#!/usr/bin/env python3
"""실제 세션에서 사용된 정확한 쿼리로 테스트"""

import sys
sys.path.insert(0, '/home/ieyeppo/AI_Lab/langchain-project')

from src.tools.search_paper import search_paper_database

def test_exact_query():
    """Session_003에서 사용된 정확한 쿼리로 테스트"""

    query = "RAG (Retrieval-Augmented Generation) 정의 및 핵심 논문"

    print("\n" + "="*80)
    print(f"🔍 실제 쿼리 테스트")
    print(f"쿼리: {query}")
    print("="*80)

    # 하이브리드 검색
    print("\n1️⃣ 하이브리드 검색 (벡터 + 키워드)")
    result = search_paper_database.invoke({
        "query": query,
        "top_k": 5,
        "with_scores": True,
        "use_multi_query": True,  # MultiQuery 활성화
        "search_mode": "similarity",
        "use_hybrid": True,
        "tool_name": "search_paper",
    })

    print(f"\n검색 결과 길이: {len(result)} 글자")
    if "관련 논문을 찾을 수 없습니다" in result:
        print("❌ 검색 실패: 관련 논문을 찾을 수 없습니다.")
    else:
        print("✅ 검색 성공!")
        print(f"\n{result[:800]}...\n")

    # 벡터 검색만
    print("\n" + "="*80)
    print("2️⃣ 벡터 검색만 (하이브리드 비활성화)")
    result2 = search_paper_database.invoke({
        "query": query,
        "top_k": 5,
        "with_scores": True,
        "use_multi_query": True,
        "search_mode": "similarity",
        "use_hybrid": False,
        "tool_name": "search_paper",
    })

    print(f"\n검색 결과 길이: {len(result2)} 글자")
    if "관련 논문을 찾을 수 없습니다" in result2:
        print("❌ 검색 실패: 관련 논문을 찾을 수 없습니다.")
    else:
        print("✅ 검색 성공!")

if __name__ == "__main__":
    test_exact_query()
