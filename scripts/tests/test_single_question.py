#!/usr/bin/env python
"""단일 질문 테스트 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.agent.nodes import router_node
from src.agent.state import AgentState


def test_single_question(question: str):
    """단일 질문 테스트"""
    print("=" * 80)
    print(f"질문: {question}")
    print("=" * 80)

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

        print(f"\n선택된 도구: {tool_choice}")
        print("=" * 80)

        return tool_choice

    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("=" * 80)
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "llm이 뭐야?"

    test_single_question(question)
