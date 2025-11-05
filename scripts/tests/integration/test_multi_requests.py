#!/usr/bin/env python3
"""
다중 요청 패턴 테스트 스크립트

2-Tool, 3-Tool, 4-Tool 패턴 테스트
"""

# ==================== Import ==================== #
from src.agent.graph import create_agent_graph, initialize_agent_state
from src.utils.experiment_manager import ExperimentManager

# ==================== 테스트 시나리오 ==================== #
TEST_SCENARIOS = {
    "2-Tool 패턴": [
        {
            "difficulty": "easy",
            "question": "Attention 논문 찾아서 요약해줘",
            "expected_tools": ["search_paper", "summarize"],
            "description": "2-Tool: 논문 검색 + 요약"
        },
        {
            "difficulty": "easy",
            "question": "2024년 상위 인용 논문 통계",
            "expected_tools": ["text2sql", "search_paper"],
            "description": "2-Tool: 통계 + 논문 검색"
        },
        {
            "difficulty": "easy",
            "question": "최신 AI 트렌드 정리해줘",
            "expected_tools": ["web_search", "summarize"],
            "description": "2-Tool: 웹 검색 + 요약"
        }
    ],
    "3-Tool 패턴": [
        {
            "difficulty": "easy",
            "question": "Transformer 논문 검색해서 요약하고 저장해줘",
            "expected_tools": ["search_paper", "summarize", "save_file"],
            "description": "3-Tool: 검색 + 요약 + 저장"
        },
        {
            "difficulty": "hard",
            "question": "인용 많은 AI 논문 통계 조회하고 요약해줘",
            "expected_tools": ["text2sql", "search_paper", "summarize"],
            "description": "3-Tool: 통계 + 검색 + 요약"
        },
        {
            "difficulty": "easy",
            "question": "Transformer 설명하고 관련 논문 찾아서 요약해줘",
            "expected_tools": ["glossary", "search_paper", "summarize"],
            "description": "3-Tool: 용어 + 검색 + 요약"
        }
    ],
    "4-Tool 패턴": [
        {
            "difficulty": "hard",
            "question": "Attention 개념 설명하고 관련 논문 정리해서 저장해줘",
            "expected_tools": ["glossary", "search_paper", "summarize", "save_file"],
            "description": "4-Tool: 용어 + 검색 + 요약 + 저장"
        },
        {
            "difficulty": "hard",
            "question": "2024년 상위 인용 논문 통계 보고 찾아서 요약하고 저장해줘",
            "expected_tools": ["text2sql", "search_paper", "summarize", "save_file"],
            "description": "4-Tool: 통계 + 검색 + 요약 + 저장"
        },
        {
            "difficulty": "hard",
            "question": "최신 AI 기술 찾아서 정리하고 분석해서 저장해줘",
            "expected_tools": ["web_search", "summarize", "general", "save_file"],
            "description": "4-Tool: 웹 + 요약 + 분석 + 저장"
        }
    ],
    "단일 요청": [
        {
            "difficulty": "easy",
            "question": "Transformer가 뭐야?",
            "expected_tools": ["glossary"],
            "description": "단일: 용어 검색"
        },
        {
            "difficulty": "hard",
            "question": "BERT 논문 검색해줘",
            "expected_tools": ["search_paper"],
            "description": "단일: 논문 검색"
        }
    ]
}

# ==================== 테스트 실행 함수 ==================== #
def test_scenario(category, scenario_num, scenario, exp_manager):
    """단일 시나리오 테스트"""
    print(f"\n{'='*80}")
    print(f"[{category}] 테스트 #{scenario_num}: {scenario['description']}")
    print(f"{'='*80}")
    print(f"난이도: {scenario['difficulty']}")
    print(f"질문: {scenario['question']}")
    print(f"예상 도구: {' → '.join(scenario['expected_tools'])}")
    print(f"-"*80)

    try:
        # Agent 그래프 생성
        agent = create_agent_graph(exp_manager)

        # 상태 초기화 (간단한 딕셔너리)
        state = {
            "question": scenario["question"],
            "difficulty": scenario["difficulty"],
            "messages": []  # 멀티턴 대화용 (빈 리스트)
        }

        # Agent 실행
        print("Agent 실행 중...")
        result = agent.invoke(state)

        # 결과 분석
        tool_pipeline = result.get("tool_pipeline", [])
        tool_choice = result.get("tool_choice", "unknown")
        final_answers = result.get("final_answers", {})

        print(f"\n선택된 도구 파이프라인: {tool_pipeline}")
        print(f"실제 실행된 도구: {tool_choice}")

        # 검증
        success = True
        if scenario["expected_tools"]:
            if tool_pipeline == scenario["expected_tools"]:
                print("✅ 도구 선택 정확!")
            else:
                print(f"❌ 도구 선택 오류!")
                print(f"   예상: {scenario['expected_tools']}")
                print(f"   실제: {tool_pipeline}")
                success = False

        # 답변 확인
        if final_answers:
            print(f"\n생성된 답변 수: {len(final_answers)}개")
            for difficulty_level, answer in final_answers.items():
                print(f"  - {difficulty_level}: {len(answer)} 글자")
        else:
            print("⚠️  답변이 생성되지 않음")
            success = False

        return success

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 메인 실행 ==================== #
def main():
    """전체 테스트 실행"""
    print("\n")
    print("="*80)
    print(" "*20 + "다중 요청 패턴 종합 테스트")
    print("="*80)

    # ExperimentManager 생성
    print("\n실험 매니저 초기화 중...")
    exp_manager = ExperimentManager()
    print(f"실험 폴더: {exp_manager.experiment_dir}")

    # 전체 테스트 결과
    total_tests = 0
    passed_tests = 0
    failed_tests = []

    # 각 카테고리별 테스트
    for category, scenarios in TEST_SCENARIOS.items():
        print(f"\n\n{'#'*80}")
        print(f"#{' '*30}{category} 시작{' '*30}#")
        print(f"{'#'*80}")

        for i, scenario in enumerate(scenarios, 1):
            total_tests += 1
            success = test_scenario(category, i, scenario, exp_manager)

            if success:
                passed_tests += 1
            else:
                failed_tests.append(f"{category} #{i}: {scenario['description']}")

    # 최종 결과
    print("\n\n")
    print("="*80)
    print(" "*30 + "테스트 결과")
    print("="*80)
    print(f"총 테스트: {total_tests}개")
    print(f"성공: {passed_tests}개 ({passed_tests/total_tests*100:.1f}%)")
    print(f"실패: {len(failed_tests)}개 ({len(failed_tests)/total_tests*100:.1f}%)")

    if failed_tests:
        print(f"\n실패한 테스트:")
        for test_name in failed_tests:
            print(f"  - {test_name}")

    print("\n" + "="*80)

    # 실험 종료
    exp_manager.close()
    print(f"\n실험 로그 저장 완료: {exp_manager.experiment_dir}")


if __name__ == "__main__":
    main()
