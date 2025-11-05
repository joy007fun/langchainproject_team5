#!/usr/bin/env python
"""Router Node 통합 테스트 스크립트

실제 router_node 함수를 호출하여 도구 선택 로직을 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.agent.nodes import router_node
from src.agent.state import AgentState


def test_router_node():
    """Router Node 통합 테스트"""
    print("=" * 80)
    print("Router Node 통합 테스트 (실제 Agent 시스템 로직)")
    print("=" * 80)

    test_cases = [
        ("nlp 용어가 뭐야?", "glossary"),
        ("mamba 용어 설명해줘", "glossary"),
        ("Transformer 용어가 뭐야?", "glossary"),
        ("BERT가 뭐야?", "glossary"),
        ("Attention 설명해줘", "glossary"),
        ("Transformer 논문 찾아줘", "search_paper"),
        ("최신 AI 뉴스", "web_search"),
    ]

    passed = 0
    failed = 0

    for question, expected in test_cases:
        # AgentState 생성
        state = AgentState(
            question=question,
            difficulty="easy",
            tool_choice=None,
            final_answer="",
            final_answers={}
        )

        try:
            # router_node 함수 호출 (exp_manager 없이)
            result_state = router_node(state, exp_manager=None)
            tool_choice = result_state.get("tool_choice", "unknown")

            status = "✅ PASS" if tool_choice == expected else f"❌ FAIL (got: {tool_choice})"
            print(f"{status}: \"{question}\" → {expected}")

            if tool_choice == expected:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            print(f"❌ ERROR: \"{question}\" - {e}")
            failed += 1

    print()
    print(f"총 {len(test_cases)}개 테스트: {passed}개 성공, {failed}개 실패")
    print("=" * 80)

    return failed == 0


def main():
    """메인 함수"""
    print("\n")
    print("🔍 Router Node 통합 테스트")
    print("   (키워드 폴백 로직 포함)")
    print()

    # Router Node 테스트
    all_passed = test_router_node()

    print("\n" + "=" * 80)
    print("최종 결과")
    print("=" * 80)
    print(f"Router Node: {'✅ 모두 통과' if all_passed else '❌ 일부 실패'}")
    print("=" * 80)

    if all_passed:
        print("\n🎉 모든 테스트가 성공했습니다!")
        return 0
    else:
        print("\n⚠️  일부 테스트가 실패했습니다. 로그를 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
