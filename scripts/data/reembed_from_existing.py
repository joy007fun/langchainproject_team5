#!/usr/bin/env python
"""
기존 청크 텍스트로 임베딩만 재생성

Usage:
    python scripts/data/reembed_from_existing.py --paper-id 1
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

from src.database.embeddings import get_embeddings

load_dotenv()


def reembed_paper_from_existing(paper_id: int, collection_name: str = "paper_chunks"):
    """
    기존 청크 텍스트로 임베딩 재생성
    
    Args:
        paper_id: 논문 ID
        collection_name: 컬렉션명
    """
    print(f"\n{'='*80}")
    print(f"📝 paper_id={paper_id} 임베딩 재생성 (기존 텍스트 사용)")
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
        ORDER BY (cmetadata->>'chunk_index')::int;
    """, (collection_uuid, str(paper_id)))
    
    existing_chunks = cursor.fetchall()
    
    if not existing_chunks:
        print(f"❌ paper_id={paper_id}의 청크가 존재하지 않습니다!")
        cursor.close()
        conn.close()
        return False
    
    print(f"   ✅ {len(existing_chunks)}개 청크 로드 완료")
    
    # 3. 임베딩 모델 초기화
    print(f"\n🔄 임베딩 생성 중 (모델: text-embedding-3-small)...")
    embeddings = get_embeddings()
    
    # 4. 각 청크의 임베딩 재생성
    updated_count = 0
    for i, chunk_data in enumerate(existing_chunks, 1):
        chunk_id = chunk_data['id']
        text = chunk_data['document']
        metadata = chunk_data['cmetadata']
        
        # 새 임베딩 생성
        new_embedding = embeddings.embed_query(text)
        
        # DB 업데이트
        cursor.execute("""
            UPDATE langchain_pg_embedding
            SET embedding = %s
            WHERE id = %s;
        """, (str(new_embedding), chunk_id))
        
        updated_count += 1
        
        if i % 5 == 0 or i == len(existing_chunks):
            print(f"   진행: {i}/{len(existing_chunks)} ({i/len(existing_chunks)*100:.1f}%)")
    
    conn.commit()
    print(f"   ✅ {updated_count}개 임베딩 업데이트 완료")
    
    # 5. 검증
    print(f"\n🔍 재생성 검증 중...")
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM langchain_pg_embedding
        WHERE collection_id = %s
        AND cmetadata->>'paper_id' = %s;
    """, (collection_uuid, str(paper_id)))
    after_count = cursor.fetchone()['count']
    
    print(f"   저장된 청크 수: {after_count}개")
    
    if after_count == len(existing_chunks):
        print(f"   ✅ 검증 성공!")
    else:
        print(f"   ⚠️  청크 수 불일치")
    
    cursor.close()
    conn.close()
    
    # 6. 테스트 검색
    print(f"\n🔍 테스트 검색 중...")
    from src.database.vector_store import get_pgvector_store
    
    store = get_pgvector_store(collection_name)
    results = store.similarity_search_with_score("Attention is all you need", k=10)
    
    found = False
    for rank, (doc, score) in enumerate(results, 1):
        if doc.metadata.get('paper_id') == paper_id:
            found = True
            print(f"   ✅ [{rank}위] paper_id={paper_id} 발견! (L2 거리: {score:.4f})")
            break
    
    if not found:
        print(f"   ⚠️  paper_id={paper_id}가 Top-10에 없습니다.")
        print(f"   Top-3 결과:")
        for rank, (doc, score) in enumerate(results[:3], 1):
            pid = doc.metadata.get('paper_id')
            print(f"      [{rank}위] paper_id={pid}, L2={score:.4f}")
    
    print(f"\n{'='*80}")
    print(f"✅ paper_id={paper_id} 임베딩 재생성 완료!")
    print(f"{'='*80}\n")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="기존 청크로 임베딩 재생성")
    parser.add_argument("--paper-id", type=int, required=True, help="논문 ID")
    parser.add_argument("--collection", type=str, default="paper_chunks", help="컬렉션명")
    
    args = parser.parse_args()
    
    try:
        success = reembed_paper_from_existing(
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
