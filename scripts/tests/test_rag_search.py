#!/usr/bin/env python3
"""RAG 논문 검색 테스트"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_pg_conn_str():
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "papers")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

def test_rag_papers():
    """RAG 관련 논문이 DB에 있는지 확인"""
    conn = psycopg2.connect(get_pg_conn_str())

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. RAG 키워드로 검색
            cur.execute("""
                SELECT paper_id, title, authors, publish_date
                FROM papers
                WHERE
                    title ILIKE %s
                    OR title ILIKE %s
                    OR title ILIKE %s
                    OR abstract ILIKE %s
                LIMIT 10
            """, ('%RAG%', '%Retrieval-Augmented%', '%Retrieval Augmented%', '%Retrieval-Augmented Generation%'))

            results = cur.fetchall()

            print(f"\n🔍 RAG 키워드 검색 결과: {len(results)}개")
            print("=" * 80)

            if results:
                for i, row in enumerate(results, 1):
                    print(f"\n{i}. [{row['paper_id']}] {row['title']}")
                    print(f"   저자: {row['authors']}")
                    print(f"   발행일: {row['publish_date']}")
            else:
                print("\n❌ RAG 관련 논문이 데이터베이스에 없습니다.")

            # 2. 전체 논문 수 확인
            cur.execute("SELECT COUNT(*) as total FROM papers")
            total = cur.fetchone()['total']
            print(f"\n📊 전체 논문 수: {total}개")

            # 3. 샘플 논문 확인
            cur.execute("SELECT paper_id, title FROM papers LIMIT 5")
            samples = cur.fetchall()
            print(f"\n📄 샘플 논문 5개:")
            for row in samples:
                print(f"  - [{row['paper_id']}] {row['title']}")

    finally:
        conn.close()

if __name__ == "__main__":
    test_rag_papers()
