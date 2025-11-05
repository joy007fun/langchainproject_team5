"""
멀티턴 라우팅 기능 테스트 스크립트

이전 대화 맥락을 고려한 도구 선택이 정상 동작하는지 검증
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.agent.nodes import router_node
from src.agent.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage


def test_multiturn_routing():
    """
    멀티턴 대화 시나리오 테스트

    시나리오:
    1. "Vision Transformer가 뭐야?" → glossary 도구 선택 (패턴 매칭)
    2. "관련 논문 찾아줘" → Multi-turn 맥락 참조 감지 → LLM 라우팅
    """

    print("=" * 80)
    print("멀티턴 라우팅 테스트")
    print("=" * 80)

    # ========== 테스트 1: 첫 번째 질문 (패턴 매칭) ========== #
    print("\n[테스트 1] 첫 번째 질문: 'Vision Transformer가 뭐야?'")
    print("-" * 80)

    state1: AgentState = {
        "question": "Vision Transformer가 뭐야?",
        "difficulty": "easy",
        "messages": [
            HumanMessage(content="Vision Transformer가 뭐야?")
        ]
    }

    result1 = router_node(state1)

    print(f"선택된 도구: {result1.get('tool_choice')}")
    print(f"라우팅 방법: {result1.get('routing_method')}")
    print(f"라우팅 이유: {result1.get('routing_reason')}")
    print(f"파이프라인: {result1.get('tool_pipeline', [])}")

    expected_tool1 = "glossary"
    if result1.get("tool_choice") == expected_tool1:
        print(f"✅ 테스트 1 통과: '{expected_tool1}' 도구가 선택됨")
    else:
        print(f"❌ 테스트 1 실패: 예상 '{expected_tool1}', 실제 '{result1.get('tool_choice')}'")

    # ========== 테스트 2: 두 번째 질문 (멀티턴 맥락 참조) ========== #
    print("\n[테스트 2] 두 번째 질문: '관련 논문 찾아줘' (멀티턴)")
    print("-" * 80)

    state2: AgentState = {
        "question": "관련 논문 찾아줘",
        "difficulty": "easy",
        "messages": [
            HumanMessage(content="Vision Transformer가 뭐야?"),
            AIMessage(content="Vision Transformer (ViT)는 이미지를 패치 단위로 분할하여..."),
            HumanMessage(content="관련 논문 찾아줘")
        ]
    }

    result2 = router_node(state2)

    print(f"선택된 도구: {result2.get('tool_choice')}")
    print(f"라우팅 방법: {result2.get('routing_method')}")
    print(f"라우팅 이유: {result2.get('routing_reason')}")
    print(f"파이프라인: {result2.get('tool_pipeline', [])}")

    # Multi-turn 맥락 참조 감지 확인
    routing_method2 = result2.get("routing_method")

    # 패턴 매칭이 아닌 다른 방법(LLM 라우팅 등)을 사용했는지 확인
    if routing_method2 != "pattern_based":
        print(f"✅ 테스트 2 통과: Multi-turn 맥락 참조가 감지되어 패턴 매칭을 건너뜀")
        print(f"   → LLM 라우팅이 이전 대화 컨텍스트를 고려하여 도구 선택")
    else:
        print(f"⚠️  테스트 2 주의: 패턴 매칭이 사용됨 (Multi-turn 맥락 참조 미감지)")
        print(f"   → '관련' 키워드가 있으면 LLM 라우팅을 사용해야 함")

    # ========== 테스트 3: 맥락 참조 없는 일반 질문 ========== #
    print("\n[테스트 3] 맥락 참조 없는 질문: 'Transformer 논문 찾아줘'")
    print("-" * 80)

    state3: AgentState = {
        "question": "Transformer 논문 찾아줘",
        "difficulty": "easy",
        "messages": [
            HumanMessage(content="Vision Transformer가 뭐야?"),
            AIMessage(content="Vision Transformer (ViT)는..."),
            HumanMessage(content="Transformer 논문 찾아줘")
        ]
    }

    result3 = router_node(state3)

    print(f"선택된 도구: {result3.get('tool_choice')}")
    print(f"라우팅 방법: {result3.get('routing_method')}")
    print(f"라우팅 이유: {result3.get('routing_reason')}")

    expected_tool3 = "search_paper"
    if result3.get("tool_choice") == expected_tool3:
        print(f"✅ 테스트 3 통과: 맥락 참조 없는 질문은 패턴 매칭 사용")
    else:
        print(f"❌ 테스트 3 실패: 예상 '{expected_tool3}', 실제 '{result3.get('tool_choice')}'")

    # ========== 테스트 4: 다양한 맥락 참조 키워드 테스트 ========== #
    print("\n[테스트 4] 다양한 맥락 참조 키워드 테스트")
    print("-" * 80)

    contextual_questions = [
        "그거 논문 찾아줘",
        "이거 관련 논문 검색해줘",
        "방금 말한 거 논문 찾아줘",
        "위에서 설명한 거 논문 보여줘",
        "해당 논문 찾아줘"
    ]

    for q in contextual_questions:
        state_test: AgentState = {
            "question": q,
            "difficulty": "easy",
            "messages": [
                HumanMessage(content="Vision Transformer가 뭐야?"),
                AIMessage(content="Vision Transformer는..."),
                HumanMessage(content=q)
            ]
        }

        result_test = router_node(state_test)
        routing_method = result_test.get("routing_method")

        if routing_method != "pattern_based":
            print(f"✅ '{q}' → Multi-turn 감지됨 (LLM 라우팅 사용)")
        else:
            print(f"⚠️  '{q}' → Multi-turn 미감지 (패턴 매칭 사용)")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_multiturn_routing()
