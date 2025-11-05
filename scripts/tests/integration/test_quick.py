# scripts/tests/integration/test_quick.py
"""
빠른 테스트 스크립트 - 각 도구별 1-2개씩만 테스트
"""

# ==================== Import ==================== #
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# test_all_scenarios 모듈의 함수 재사용
from test_all_scenarios import run_test, BEGINNER_QUESTIONS, EXPERT_QUESTIONS
from src.utils.experiment_manager import ExperimentManager


# ==================== 빠른 테스트용 질문 선택 ==================== #
QUICK_TEST_BEGINNER = [
    {"q": "Transformer가 뭐야?", "expected_tool": "glossary", "type": "단일"},
    {"q": "Transformer 관련 논문 찾아줘", "expected_tool": "search_paper", "type": "단일"},
    {"q": "2024년에 나온 AI 논문 몇 개야?", "expected_tool": "text2sql", "type": "단일"},
    {"q": "최신 AI 뉴스 알려줘", "expected_tool": "web_search", "type": "단일"},
    {"q": "\"Attention Is All You Need\" 논문 요약해줘", "expected_tool": "summarize", "type": "단일"},
]

QUICK_TEST_EXPERT = [
    {"q": "Self-Attention의 시간 복잡도는?", "expected_tool": "general", "type": "단일"},
    {"q": "LoRA Fine-tuning 기법 논문 찾아줘", "expected_tool": "search_paper", "type": "단일"},
    {"q": "2022년 이후 Attention 메커니즘 관련 논문을 연도별로 보여줘", "expected_tool": "text2sql", "type": "단일"},
]


def run_quick_test(questions, difficulty, mode_name):
    """빠른 테스트 실행"""
    print(f"\n{'#'*80}")
    print(f"# {mode_name} 빠른 테스트")
    print(f"# 총 {len(questions)}개 질문")
    print(f"{'#'*80}\n")

    exp_manager = ExperimentManager()
    results = []

    for i, q_data in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}]")
        result = run_test(q_data, difficulty, exp_manager)
        results.append(result)

    # 결과 요약
    print(f"\n\n{'='*80}")
    print(f"{mode_name} 결과")
    print(f"{'='*80}\n")

    for i, r in enumerate(results, 1):
        status = "✅" if r["success"] else "❌"
        tool_match = "✓" if r["actual_tool"] == r["expected_tool"] else "✗"

        print(f"{status} [{i}] {r['question'][:40]}...")
        print(f"    예상: {r['expected_tool']} | 실제: {r['actual_tool']} {tool_match}")
        if not r["success"] and r.get("error"):
            print(f"    에러: {r['error'][:60]}")

    exp_manager.close()
    print(f"\n실험 폴더: {exp_manager.experiment_dir}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="빠른 테스트")
    parser.add_argument("--mode", choices=["beginner", "expert", "both"], default="beginner")
    args = parser.parse_args()

    if args.mode in ["beginner", "both"]:
        run_quick_test(QUICK_TEST_BEGINNER, "easy", "초보자 모드")

    if args.mode in ["expert", "both"]:
        run_quick_test(QUICK_TEST_EXPERT, "hard", "전문가 모드")
