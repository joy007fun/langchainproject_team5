#!/usr/bin/env python
"""
특정 논문의 임베딩을 재생성하는 스크립트

Usage:
    python scripts/data/reembed_paper.py --paper-id 1
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import psycopg2
from dotenv import load_dotenv
from langchain_core.documents import Document

from src.database.embeddings import get_embeddings
from src.database.vector_store import get_pgvector_store

load_dotenv()


def delete_paper_embeddings(paper_id: int, collection_name: str = "paper_chunks"):
    """
    특정 논문의 임베딩 삭제
    
    Args:
        paper_id: 논문 ID
        collection_name: 컬렉션명
    """
    print(f"\n🗑️  paper_id={paper_id}의 기존 임베딩 삭제 중...")
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    # 컬렉션 UUID 가져오기
    cursor.execute("""
        SELECT uuid FROM langchain_pg_collection WHERE name = %s;
    """, (collection_name,))
    collection_uuid = cursor.fetchone()[0]
    
    # 삭제 전 개수 확인
    cursor.execute("""
        SELECT COUNT(*)
        FROM langchain_pg_embedding
        WHERE collection_id = %s
        AND cmetadata->>'paper_id' = %s;
    """, (collection_uuid, str(paper_id)))
    before_count = cursor.fetchone()[0]
    
    print(f"   삭제 대상: {before_count}개 청크")
    
    # 삭제 실행
    cursor.execute("""
        DELETE FROM langchain_pg_embedding
        WHERE collection_id = %s
        AND cmetadata->>'paper_id' = %s;
    """, (collection_uuid, str(paper_id)))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"   ✅ {before_count}개 청크 삭제 완료")


def get_paper_chunks(paper_id: int):
    """
    papers 테이블에서 논문 정보와 PDF 텍스트 가져오기
    
    Args:
        paper_id: 논문 ID
        
    Returns:
        논문 정보 딕셔너리
    """
    print(f"\n📄 paper_id={paper_id}의 원본 데이터 로드 중...")
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT paper_id, title, authors, publish_date, url, category, 
               citation_count, full_text
        FROM papers
        WHERE paper_id = %s;
    """, (paper_id,))
    
    row = cursor.fetchone()
    
    if not row:
        cursor.close()
        conn.close()
        raise ValueError(f"paper_id={paper_id}가 존재하지 않습니다.")
    
    paper_info = {
        "paper_id": row[0],
        "title": row[1],
        "authors": row[2],
        "publish_date": row[3],
        "url": row[4],
        "category": row[5],
        "citation_count": row[6],
        "full_text": row[7]
    }
    
    cursor.close()
    conn.close()
    
    print(f"   제목: {paper_info['title']}")
    print(f"   저자: {paper_info['authors'][:100]}...")
    print(f"   텍스트 길이: {len(paper_info['full_text']) if paper_info['full_text'] else 0} 글자")
    
    return paper_info


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    """
    텍스트를 청크로 분할
    
    Args:
        text: 원본 텍스트
        chunk_size: 청크 크기
        chunk_overlap: 청크 겹침
        
    Returns:
        청크 리스트
    """
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    chunks = text_splitter.split_text(text)
    return chunks


def reembed_paper(paper_id: int, collection_name: str = "paper_chunks", 
                  chunk_size: int = 1000, chunk_overlap: int = 200):
    """
    논문 임베딩 재생성
    
    Args:
        paper_id: 논문 ID
        collection_name: 컬렉션명
        chunk_size: 청크 크기
        chunk_overlap: 청크 겹침
    """
    print(f"\n{'='*80}")
    print(f"📝 paper_id={paper_id} 임베딩 재생성 시작")
    print(f"{'='*80}")
    
    # 1. 기존 임베딩 삭제
    delete_paper_embeddings(paper_id, collection_name)
    
    # 2. 원본 데이터 로드
    paper_info = get_paper_chunks(paper_id)
    
    if not paper_info['full_text']:
        print(f"\n❌ paper_id={paper_id}에 full_text가 없습니다!")
        return False
    
    # 3. 텍스트 청킹
    print(f"\n✂️  텍스트 청킹 중 (크기: {chunk_size}, 겹침: {chunk_overlap})...")
    chunks = chunk_text(paper_info['full_text'], chunk_size, chunk_overlap)
    print(f"   ✅ {len(chunks)}개 청크 생성")
    
    # 4. Document 객체 생성
    print(f"\n📦 Document 객체 생성 중...")
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "paper_id": paper_info['paper_id'],
                "title": paper_info['title'],
                "authors": paper_info['authors'],
                "publish_date": str(paper_info['publish_date']) if paper_info['publish_date'] else None,
                "url": paper_info['url'],
                "category": paper_info['category'],
                "citation_count": paper_info['citation_count'],
                "chunk_index": i,
                "source": f"paper_{paper_id}"
            }
        )
        documents.append(doc)
    
    print(f"   ✅ {len(documents)}개 Document 생성")
    
    # 5. 임베딩 생성 및 저장
    print(f"\n🔄 임베딩 생성 및 저장 중 (모델: text-embedding-3-small)...")
    print(f"   예상 시간: 약 {len(documents) * 0.5:.0f}초")
    
    vector_store = get_pgvector_store(collection_name)
    vector_store.add_documents(documents)
    
    print(f"   ✅ {len(documents)}개 임베딩 저장 완료")
    
    # 6. 검증
    print(f"\n🔍 재생성 검증 중...")
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT uuid FROM langchain_pg_collection WHERE name = %s;
    """, (collection_name,))
    collection_uuid = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM langchain_pg_embedding
        WHERE collection_id = %s
        AND cmetadata->>'paper_id' = %s;
    """, (collection_uuid, str(paper_id)))
    after_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    print(f"   저장된 청크 수: {after_count}개")
    
    if after_count == len(documents):
        print(f"   ✅ 검증 성공!")
    else:
        print(f"   ⚠️  청크 수 불일치: 생성={len(documents)}, 저장={after_count}")
    
    # 7. 테스트 검색
    print(f"\n🔍 테스트 검색 중...")
    results = vector_store.similarity_search_with_score(
        f"{paper_info['title']}", 
        k=5
    )
    
    found = False
    for i, (doc, score) in enumerate(results, 1):
        if doc.metadata.get('paper_id') == paper_id:
            found = True
            print(f"   ✅ [{i}위] paper_id={paper_id} 발견! (L2 거리: {score:.4f})")
            break
    
    if not found:
        print(f"   ⚠️  paper_id={paper_id}가 Top-5에 없습니다. 추가 확인 필요.")
    
    print(f"\n{'='*80}")
    print(f"✅ paper_id={paper_id} 임베딩 재생성 완료!")
    print(f"{'='*80}\n")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="논문 임베딩 재생성")
    parser.add_argument("--paper-id", type=int, required=True, help="논문 ID")
    parser.add_argument("--collection", type=str, default="paper_chunks", help="컬렉션명")
    parser.add_argument("--chunk-size", type=int, default=1000, help="청크 크기")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="청크 겹침")
    
    args = parser.parse_args()
    
    try:
        success = reembed_paper(
            paper_id=args.paper_id,
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )
        
        if success:
            print("🎉 성공!")
            sys.exit(0)
        else:
            print("❌ 실패!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
