# scripts/tests/integration/test_router_fix.py
"""
Router JSON 파싱 수정 테스트

이전 세션에서 발생한 Router JSON 파싱 에러가 수정되었는지 확인하는 테스트
"""

# ==================== Import ==================== #
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.state import AgentState
from src.agent.nodes import router_node
from src.utils.experiment_manager import ExperimentManager


# ==================== 테스트 함수 ==================== #
def test_router_with_markdown_response():
    """
    Router가 마크다운 코드 펜스로 감싼 응답을 올바르게 처리하는지 테스트
    """
    print("=" * 80)
    print("Router JSON 파싱 테스트 시작")
    print("=" * 80)

    # ExperimentManager 초기화
    exp_manager = ExperimentManager()

    # 이전 세션에서 실패했던 질문들
    test_questions = [
        {
            "question": "LangGraph가 뭐야? langchain과 langgraph 차이를 알려줘",
            "difficulty": "easy",
            "expected_tool": "general"  # 비교 질문이므로 general
        },
        {
            "question": "Few-shot learning을 개선한 연구는 어떤게 있어?",
            "difficulty": "easy",
            "expected_tool": "search_paper"  # 논문 검색
        },
        {
            "question": "LLM의 효율적인 Fine-tuning 기법 논문 찾아줘",
            "difficulty": "easy",
            "expected_tool": "search_paper"  # 논문 검색
        },
        {
            "question": "Attention이 왜 필요해?",
            "difficulty": "easy",
            "expected_tool": "general"  # 개념 설명
        },
    ]

    results = []

    for i, test_case in enumerate(test_questions, 1):
        print(f"\n[테스트 {i}/{len(test_questions)}]")
        print(f"질문: {test_case['question']}")
        print(f"난이도: {test_case['difficulty']}")
        print(f"예상 도구: {test_case['expected_tool']}")

        # 상태 초기화
        state = AgentState(
            question=test_case["question"],
            difficulty=test_case["difficulty"],
            messages=[],
            tool_choice="",
            final_answer="",
        )

        try:
            # Router 노드 실행
            updated_state = router_node(state, exp_manager)

            tool_choice = updated_state.get("tool_choice", "")

            # 결과 확인
            success = tool_choice in ["general", "glossary", "search_paper", "web_search", "summarize", "text2sql", "save_file"]

            if success:
                print(f"✅ 성공: tool_choice = {tool_choice}")
                results.append({
                    "question": test_case["question"],
                    "expected": test_case["expected_tool"],
                    "actual": tool_choice,
                    "success": True,
                    "error": None
                })
            else:
                print(f"❌ 실패: 유효하지 않은 도구 = {tool_choice}")
                results.append({
                    "question": test_case["question"],
                    "expected": test_case["expected_tool"],
                    "actual": tool_choice,
                    "success": False,
                    "error": f"유효하지 않은 도구: {tool_choice}"
                })

        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            results.append({
                "question": test_case["question"],
                "expected": test_case["expected_tool"],
                "actual": None,
                "success": False,
                "error": str(e)
            })

    # 최종 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    print(f"\n성공: {success_count}/{total_count}")
    print(f"실패: {total_count - success_count}/{total_count}")

    for i, result in enumerate(results, 1):
        status = "✅" if result["success"] else "❌"
        print(f"\n{status} 테스트 {i}:")
        print(f"  질문: {result['question'][:50]}...")
        print(f"  예상: {result['expected']}")
        print(f"  실제: {result['actual']}")
        if result["error"]:
            print(f"  에러: {result['error']}")

    # 실험 종료
    exp_manager.end_session()

    print("\n" + "=" * 80)
    print(f"실험 폴더: {exp_manager.session_dir}")
    print("=" * 80)

    return success_count == total_count


# ==================== 실행 ==================== #
if __name__ == "__main__":
    success = test_router_with_markdown_response()

    if success:
        print("\n✅ 모든 테스트 통과!")
        sys.exit(0)
    else:
        print("\n❌ 일부 테스트 실패")
        sys.exit(1)
