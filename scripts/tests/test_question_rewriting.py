"""
멀티턴 질문 재작성 기능 테스트 스크립트

LLM이 생성한 query 필드가 state["refined_query"]에 저장되고
도구 노드에게 전달되는지 검증
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.agent.nodes import router_node
from src.agent.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage


def test_refined_query_extraction():
    """
    LLM 응답에서 query 필드를 추출하여 state에 저장하는지 테스트
    """

    print("=" * 80)
    print("멀티턴 질문 재작성 테스트")
    print("=" * 80)

    # ========== 시나리오: "관련 논문 찾아줘" → LLM이 "Vision Transformer" 추출 ========== #
    print("\n[테스트] '관련 논문 찾아줘' → LLM query 필드 추출")
    print("-" * 80)

    state: AgentState = {
        "question": "관련 논문 찾아줘",
        "difficulty": "easy",
        "messages": [
            HumanMessage(content="Vision Transformer가 뭐야?"),
            AIMessage(content="Vision Transformer (ViT)는 이미지를 패치 단위로 분할하여 트랜스포머 아키텍처를 적용하는 컴퓨터 비전 모델입니다. CNN과 달리 Self-Attention 메커니즘을 사용하여..."),
            HumanMessage(content="관련 논문 찾아줘")
        ]
    }

    # router_node 실행
    result = router_node(state)

    print(f"\n원본 질문: {result['question']}")
    print(f"재작성된 질문: {result.get('refined_query', '없음')}")
    print(f"선택된 도구: {result.get('tool_choice')}")
    print(f"라우팅 방법: {result.get('routing_method')}")

    # refined_query 필드 존재 여부 확인
    if "refined_query" in result:
        print(f"\n✅ 테스트 통과: refined_query 필드가 state에 저장됨")
        print(f"   → LLM이 파악한 맥락: '{result['refined_query']}'")

        # "Vision Transformer" 키워드가 포함되어 있는지 확인
        if "vision transformer" in result["refined_query"].lower() or "vit" in result["refined_query"].lower():
            print(f"   → 맥락 정보 정확히 파악됨 ✅")
        else:
            print(f"   → 주의: 맥락 정보가 명확하지 않을 수 있음 ⚠️")
    else:
        print(f"\n⚠️  테스트 실패: refined_query 필드가 state에 없음")
        print(f"   → LLM 응답에 query 필드가 없거나 파싱 실패")

    # ========== 도구 노드 시뮬레이션 ========== #
    print("\n[도구 노드 시뮬레이션] search_paper_node가 받을 질문")
    print("-" * 80)

    # search_paper.py의 로직 시뮬레이션
    question_for_tool = result.get("refined_query", result["question"])

    print(f"도구가 받는 질문: {question_for_tool}")

    if question_for_tool == "관련 논문 찾아줘":
        print("❌ 도구가 원본 질문(모호)을 받음 → 검색 실패 가능성 높음")
    else:
        print("✅ 도구가 재작성된 질문(명확)을 받음 → 정확한 검색 가능")

    # ========== 테스트 2: 맥락 참조 없는 일반 질문 ========== #
    print("\n" + "=" * 80)
    print("[테스트 2] 맥락 참조 없는 일반 질문: 'Transformer 논문 찾아줘'")
    print("=" * 80)

    state2: AgentState = {
        "question": "Transformer 논문 찾아줘",
        "difficulty": "easy",
        "messages": [
            HumanMessage(content="Transformer 논문 찾아줘")
        ]
    }

    result2 = router_node(state2)

    print(f"\n원본 질문: {result2['question']}")
    print(f"재작성된 질문: {result2.get('refined_query', '없음')}")
    print(f"선택된 도구: {result2.get('tool_choice')}")
    print(f"라우팅 방법: {result2.get('routing_method')}")

    if "refined_query" not in result2:
        print(f"\n✅ 예상대로: 맥락 참조 없으면 refined_query 생성 안됨")
        print(f"   → 원본 질문이 충분히 명확하므로 재작성 불필요")
    else:
        print(f"\n⚠️  refined_query가 생성됨: {result2['refined_query']}")
        print(f"   → LLM이 질문을 재작성함 (선택적 동작)")

    # ========== 테스트 3: Multi-Query Retrieval 활성화 확인 ========== #
    print("\n" + "=" * 80)
    print("[테스트 3] Multi-Query Retrieval 활성화 확인")
    print("=" * 80)

    print("\nsearch_paper.py의 use_multi_query 설정 확인:")

    try:
        with open("/home/ieyeppo/AI_Lab/langchain-project/src/tools/search_paper.py", "r", encoding="utf-8") as f:
            content = f.read()

        if '"use_multi_query": True' in content:
            print("✅ use_multi_query: True로 설정됨")
            print("   → LLM이 자동으로 여러 검색 쿼리 생성하여 검색 강화")
        elif '"use_multi_query": False' in content:
            print("❌ use_multi_query: False로 설정됨")
            print("   → Multi-Query 기능 미사용")
        else:
            print("⚠️  use_multi_query 설정을 찾을 수 없음")
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_refined_query_extraction()
