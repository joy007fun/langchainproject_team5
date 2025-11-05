#!/usr/bin/env python
"""
올바른 방식으로 임베딩 재생성 (langchain PGVector 사용)
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from langchain_core.documents import Document

from src.database.vector_store import get_pgvector_store

load_dotenv()


def reembed_paper_proper(paper_id: int, collection_name: str = "paper_chunks"):
    """
    langchain PGVector를 사용한 올바른 임베딩 재생성
    
    Args:
        paper_id: 논문 ID
        collection_name: 컬렉션명
    """
    print(f"\n{'='*80}")
    print(f"📝 paper_id={paper_id} 임베딩 재생성 (PGVector 방식)")
    print(f"{'='*80}")
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. 컬렉션 UUID 가져오기
    cursor.execute("""
        SELECT uuid FROM langchain_pg_collection WHERE name = %s;
    """, (collection_name,))
    collection_result = cursor.fetchone()
    
    if not collection_result:
        print(f"❌ 컬렉션 '{collection_name}'이 존재하지 않습니다!")
        cursor.close()
        conn.close()
        return False
    
    collection_uuid = collection_result['uuid']
    
    # 2. 기존 청크 데이터 가져오기
    print(f"\n📦 기존 청크 데이터 로드 중...")
    cursor.execute("""
        SELECT id, document, cmetadata
        FROM langchain_pg_embedding
        WHERE collection_id = %s
        AND cmetadata->>'paper_id' = %s
        ORDER BY (cmetadata->>'chunk_index')::int NULLS LAST;
    """, (collection_uuid, str(paper_id)))
    
    existing_chunks = cursor.fetchall()
    
    if not existing_chunks:
        print(f"❌ paper_id={paper_id}의 청크가 존재하지 않습니다!")
        cursor.close()
        conn.close()
        return False
    
    print(f"   ✅ {len(existing_chunks)}개 청크 로드 완료")
    
    cursor.close()
    conn.close()
    
    # 3. Document 객체 재구성
    print(f"\n📦 Document 객체 재구성 중...")
    documents = []
    chunk_ids = []
    
    for chunk_data in existing_chunks:
        chunk_ids.append(chunk_data['id'])
        doc = Document(
            page_content=chunk_data['document'],
            metadata=chunk_data['cmetadata']
        )
        documents.append(doc)
    
    print(f"   ✅ {len(documents)}개 Document 생성")
    
    # 4. 기존 청크 삭제
    print(f"\n🗑️  기존 청크 삭제 중...")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM langchain_pg_embedding
        WHERE collection_id = %s
        AND cmetadata->>'paper_id' = %s;
    """, (collection_uuid, str(paper_id)))
    
    deleted_count = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"   ✅ {deleted_count}개 청크 삭제 완료")
    
    # 5. PGVector로 재등록 (임베딩 자동 생성)
    print(f"\n🔄 PGVector로 재등록 중 (임베딩 자동 생성)...")
    print(f"   예상 시간: 약 {len(documents)}초")
    
    store = get_pgvector_store(collection_name)
    store.add_documents(documents)
    
    print(f"   ✅ {len(documents)}개 청크 재등록 완료")
    
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
    
    # 7. 테스트 검색
    print(f"\n🔍 테스트 검색 중...")
    
    results = store.similarity_search_with_score("Attention is all you need", k=10)
    
    found = False
    for rank, (doc, score) in enumerate(results, 1):
        if doc.metadata.get('paper_id') == paper_id:
            found = True
            print(f"   ✅ [{rank}위] paper_id={paper_id} 발견! (L2 거리: {score:.4f})")
            print(f"   청크 내용: {doc.page_content[:100]}...")
            break
    
    if not found:
        print(f"   ⚠️  paper_id={paper_id}가 Top-10에 없습니다.")
        print(f"\n   Top-5 결과:")
        for rank, (doc, score) in enumerate(results[:5], 1):
            pid = doc.metadata.get('paper_id')
            print(f"      [{rank}위] paper_id={pid}, L2={score:.4f}")
            print(f"             {doc.page_content[:80]}...")
    
    print(f"\n{'='*80}")
    print(f"✅ paper_id={paper_id} 임베딩 재생성 완료!")
    print(f"{'='*80}\n")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PGVector 방식으로 임베딩 재생성")
    parser.add_argument("--paper-id", type=int, required=True, help="논문 ID")
    parser.add_argument("--collection", type=str, default="paper_chunks", help="컬렉션명")
    
    args = parser.parse_args()
    
    try:
        success = reembed_paper_proper(
            paper_id=args.paper_id,
            collection_name=args.collection
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
