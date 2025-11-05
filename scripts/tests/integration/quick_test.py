#!/usr/bin/env python3
"""
빠른 다중 요청 패턴 테스트
"""

from src.agent.graph import create_agent_graph
from src.utils.experiment_manager import ExperimentManager

# ExperimentManager 생성
print("\n실험 매니저 초기화...")
exp_manager = ExperimentManager()
print(f"실험 폴더: {exp_manager.experiment_dir}")

# Agent 생성
print("Agent 그래프 생성...")
agent = create_agent_graph(exp_manager)

# 테스트 시나리오들
tests = [
    {
        "name": "2-Tool: 논문 검색 + 요약",
        "question": "Attention 논문 찾아서 요약해줘",
        "difficulty": "easy",
        "expected": ["search_paper", "summarize"]
    },
    {
        "name": "3-Tool: 검색 + 요약 + 저장",
        "question": "Transformer 논문 검색해서 요약하고 저장해줘",
        "difficulty": "easy",
        "expected": ["search_paper", "summarize", "save_file"]
    },
    {
        "name": "4-Tool: 용어 + 검색 + 요약 + 저장",
        "question": "Attention 개념 설명하고 관련 논문 정리해서 저장해줘",
        "difficulty": "hard",
        "expected": ["glossary", "search_paper", "summarize", "save_file"]
    }
]

print(f"\n총 {len(tests)}개 테스트 실행\n")

for i, test in enumerate(tests, 1):
    print(f"{'='*80}")
    print(f"테스트 #{i}: {test['name']}")
    print(f"{'='*80}")
    print(f"질문: {test['question']}")
    print(f"난이도: {test['difficulty']}")
    print(f"예상 도구: {' → '.join(test['expected'])}")
    print(f"-"*80)

    try:
        # Agent 실행
        state = {
            "question": test["question"],
            "difficulty": test["difficulty"],
            "messages": []
        }

        print("Agent 실행 중...")
        result = agent.invoke(state)

        # 결과 확인
        tool_pipeline = result.get("tool_pipeline", [])
        print(f"\n실제 도구: {' → '.join(tool_pipeline) if tool_pipeline else 'N/A'}")

        # 검증
        if tool_pipeline == test['expected']:
            print("✅ 성공!")
        else:
            print(f"❌ 실패! (예상: {test['expected']})")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

    print()

print("테스트 완료")
exp_manager.close()
