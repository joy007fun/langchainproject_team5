#!/usr/bin/env python3
"""하이브리드 검색 테스트"""

import sys
sys.path.insert(0, '/home/ieyeppo/AI_Lab/langchain-project')

from src.tools.search_paper import search_paper_database

def test_hybrid_search():
    """RAG 키워드로 하이브리드 검색 테스트"""

    print("\n" + "="*80)
    print("🔍 하이브리드 검색 테스트: 'RAG' 키워드")
    print("="*80)

    # 1. 하이브리드 검색 활성화 (기본)
    print("\n1️⃣ 하이브리드 검색 (벡터 + 키워드)")
    result = search_paper_database.invoke({
        "query": "RAG",
        "top_k": 5,
        "with_scores": True,
        "use_hybrid": True,
        "tool_name": "search_paper",
    })

    print(f"\n검색 결과 길이: {len(result)} 글자")
    if "관련 논문을 찾을 수 없습니다" in result:
        print("❌ 검색 실패: 관련 논문을 찾을 수 없습니다.")
    else:
        print("✅ 검색 성공!")
        print(f"\n{result[:500]}...\n")

    # 2. 키워드 검색만
    print("\n" + "="*80)
    print("2️⃣ 벡터 검색만 (하이브리드 비활성화)")
    result2 = search_paper_database.invoke({
        "query": "RAG",
        "top_k": 5,
        "with_scores": True,
        "use_hybrid": False,
        "tool_name": "search_paper",
    })

    print(f"\n검색 결과 길이: {len(result2)} 글자")
    if "관련 논문을 찾을 수 없습니다" in result2:
        print("❌ 검색 실패: 관련 논문을 찾을 수 없습니다.")
    else:
        print("✅ 검색 성공!")
        print(f"\n{result2[:500]}...\n")

    # 3. 더 긴 쿼리로 테스트
    print("\n" + "="*80)
    print("3️⃣ 긴 쿼리 테스트: 'Retrieval-Augmented Generation'")
    result3 = search_paper_database.invoke({
        "query": "Retrieval-Augmented Generation",
        "top_k": 5,
        "with_scores": True,
        "use_hybrid": True,
        "tool_name": "search_paper",
    })

    print(f"\n검색 결과 길이: {len(result3)} 글자")
    if "관련 논문을 찾을 수 없습니다" in result3:
        print("❌ 검색 실패: 관련 논문을 찾을 수 없습니다.")
    else:
        print("✅ 검색 성공!")
        print(f"\n{result3[:500]}...\n")

if __name__ == "__main__":
    test_hybrid_search()
