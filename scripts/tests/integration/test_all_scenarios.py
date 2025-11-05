# scripts/tests/integration/test_all_scenarios.py
"""
전체 시나리오 테스트 스크립트

초보자/전문가 모드 각각 20+개 질문을 자동으로 실행하여
도구 선택, 실행 결과, Fallback 작동 등을 검증
"""

# ==================== Import ==================== #
import sys
from pathlib import Path
import time
from typing import Dict, List

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.graph import create_agent_graph, initialize_fallback_state
from src.agent.state import AgentState
from src.utils.experiment_manager import ExperimentManager


# ==================== 테스트 질문 정의 ==================== #
BEGINNER_QUESTIONS = [
    # 단일요청 - general (4개)
    {"q": "AI가 뭐야?", "expected_tool": "general", "type": "단일"},
    {"q": "딥러닝이랑 머신러닝은 어떻게 다른거야?", "expected_tool": "general", "type": "단일"},
    {"q": "CNN에서 필터가 하는 일이 뭐야?", "expected_tool": "general", "type": "단일"},
    {"q": "왜 AI 학습에 GPU를 쓰는거야?", "expected_tool": "general", "type": "단일"},

    # 단일요청 - glossary (3개)
    {"q": "Transformer가 뭐야?", "expected_tool": "glossary", "type": "단일"},
    {"q": "BERT 모델 설명해줘", "expected_tool": "glossary", "type": "단일"},
    {"q": "Attention Mechanism이 뭔지 알려줘", "expected_tool": "glossary", "type": "단일"},

    # 단일요청 - search_paper (3개)
    {"q": "Transformer 관련 논문 찾아줘", "expected_tool": "search_paper", "type": "단일"},
    {"q": "BERT 모델 논문 있어?", "expected_tool": "search_paper", "type": "단일"},
    {"q": "Few-shot learning 연구 논문 보여줘", "expected_tool": "search_paper", "type": "단일"},

    # 단일요청 - text2sql (2개)
    {"q": "2024년에 나온 AI 논문 몇 개야?", "expected_tool": "text2sql", "type": "단일"},
    {"q": "가장 많이 인용된 논문 5개 보여줘", "expected_tool": "text2sql", "type": "단일"},

    # 단일요청 - summarize (1개)
    {"q": "\"Attention Is All You Need\" 논문 요약해줘", "expected_tool": "summarize", "type": "단일"},

    # 단일요청 - web_search (1개)
    {"q": "최신 AI 뉴스 알려줘", "expected_tool": "web_search", "type": "단일"},

    # 다중요청 (4개)
    {"q": "GPT 논문 찾아서 요약해줘", "expected_tool": "search_paper", "type": "다중", "pipeline": ["search_paper", "summarize"]},
    {"q": "Attention 관련 논문 정리해줘", "expected_tool": "search_paper", "type": "다중", "pipeline": ["search_paper", "summarize"]},
    {"q": "RAG가 뭔지 설명하고 관련 논문도 보여줘", "expected_tool": "glossary", "type": "다중", "pipeline": ["glossary", "search_paper"]},
    {"q": "2023년 이후 인용 많은 논문 찾아줘", "expected_tool": "text2sql", "type": "다중", "pipeline": ["text2sql", "search_paper"]},

    # 멀티턴 (2개)
    {"q": "Vision Transformer가 뭐야?", "expected_tool": "glossary", "type": "멀티턴"},
    {"q": "관련 논문 찾아줘", "expected_tool": "search_paper", "type": "멀티턴"},
]

EXPERT_QUESTIONS = [
    # 단일요청 - general (3개)
    {"q": "Self-Attention의 시간 복잡도는?", "expected_tool": "general", "type": "단일"},
    {"q": "Transformer가 RNN보다 나은 이유를 기술적으로 설명해줘", "expected_tool": "general", "type": "단일"},
    {"q": "Gradient Vanishing 문제와 해결책을 알려줘", "expected_tool": "general", "type": "단일"},

    # 단일요청 - search_paper (4개)
    {"q": "LoRA Fine-tuning 기법 논문 찾아줘", "expected_tool": "search_paper", "type": "단일"},
    {"q": "Multimodal Learning 최신 연구 논문 검색해줘", "expected_tool": "search_paper", "type": "단일"},
    {"q": "Chain-of-Thought prompting 논문 있어?", "expected_tool": "search_paper", "type": "단일"},
    {"q": "Constitutional AI 관련 논문 찾아줘", "expected_tool": "search_paper", "type": "단일"},

    # 단일요청 - glossary (2개)
    {"q": "Zero-shot Learning의 정의를 알려줘", "expected_tool": "glossary", "type": "단일"},
    {"q": "Mixture of Experts란?", "expected_tool": "glossary", "type": "단일"},

    # 단일요청 - text2sql (3개)
    {"q": "2022년 이후 Attention 메커니즘 관련 논문을 연도별로 보여줘", "expected_tool": "text2sql", "type": "단일"},
    {"q": "카테고리별 논문 수 통계 보여줘", "expected_tool": "text2sql", "type": "단일"},
    {"q": "2024년 인용 수 상위 10개 논문 제목 알려줘", "expected_tool": "text2sql", "type": "단일"},

    # 단일요청 - summarize (1개)
    {"q": "\"BERT: Pre-training of Deep Bidirectional Transformers\" 논문 요약해줘", "expected_tool": "summarize", "type": "단일"},

    # 단일요청 - web_search (1개)
    {"q": "2025년 NeurIPS 컨퍼런스 소식 찾아줘", "expected_tool": "web_search", "type": "단일"},

    # 다중요청 (7개)
    {"q": "BERT와 GPT 논문 비교해서 분석하고 저장해줘", "expected_tool": "search_paper", "type": "다중", "pipeline": ["search_paper", "summarize", "general", "save_file"]},
    {"q": "Diffusion Model 설명하고 관련 논문 찾아서 요약해줘", "expected_tool": "glossary", "type": "다중", "pipeline": ["glossary", "search_paper", "summarize"]},
    {"q": "2024년 BERT 계열 논문 통계 보여주고 대표 논문 하나 요약해줘", "expected_tool": "text2sql", "type": "다중", "pipeline": ["text2sql", "search_paper", "summarize"]},
    {"q": "최신 LLM 트렌드 찾아서 정리하고 저장해줘", "expected_tool": "web_search", "type": "다중", "pipeline": ["web_search", "summarize", "save_file"]},
    {"q": "Supervised Learning과 Unsupervised Learning 차이를 논문 기반으로 설명해줘", "expected_tool": "search_paper", "type": "다중", "pipeline": ["search_paper", "general"]},
    {"q": "Retrieval Augmented Generation 설명하고 관련 논문도 찾아줘", "expected_tool": "glossary", "type": "다중", "pipeline": ["glossary", "search_paper"]},
    {"q": "Transformer 관련 논문 통계를 SQL로 조회하고 결과 저장해줘", "expected_tool": "text2sql", "type": "다중", "pipeline": ["text2sql", "save_file"]},
]


# ==================== 테스트 실행 함수 ==================== #
def run_test(question_data: Dict, difficulty: str, exp_manager: ExperimentManager):
    """
    단일 질문 테스트 실행

    Args:
        question_data: 질문 데이터
        difficulty: 난이도 (easy/hard)
        exp_manager: ExperimentManager

    Returns:
        Dict: 테스트 결과
    """
    question = question_data["q"]
    expected_tool = question_data.get("expected_tool")
    q_type = question_data.get("type", "단일")

    print(f"\n{'='*80}")
    print(f"질문: {question}")
    print(f"유형: {q_type}")
    print(f"예상 도구: {expected_tool}")
    print(f"{'='*80}")

    # Agent 그래프 생성
    agent_executor = create_agent_graph(exp_manager)

    # 상태 초기화
    state = AgentState(
        question=question,
        difficulty=difficulty,
        messages=[],
        tool_choice="",
        final_answer="",
    )

    # Fallback Chain 초기화
    state = initialize_fallback_state(state, exp_manager)

    # 실행 시작 시간
    start_time = time.time()

    try:
        # Agent 실행
        result = agent_executor.invoke(state)

        # 실행 시간
        elapsed = time.time() - start_time

        # 결과 분석
        tool_choice = result.get("tool_choice", "unknown")
        final_answer = result.get("final_answer", "")
        tool_status = result.get("tool_status", "unknown")
        tool_pipeline = result.get("tool_pipeline", [])

        # 성공 여부 판단
        success = tool_status == "success" and len(final_answer) > 0

        print(f"\n✅ 실행 완료")
        print(f"   선택 도구: {tool_choice}")
        print(f"   도구 상태: {tool_status}")
        if len(tool_pipeline) > 1:
            print(f"   파이프라인: {' → '.join(tool_pipeline)}")
        print(f"   답변 길이: {len(final_answer)} 글자")
        print(f"   실행 시간: {elapsed:.2f}초")

        return {
            "question": question,
            "type": q_type,
            "expected_tool": expected_tool,
            "actual_tool": tool_choice,
            "tool_status": tool_status,
            "pipeline": tool_pipeline,
            "success": success,
            "elapsed": elapsed,
            "answer_length": len(final_answer),
            "error": None
        }

    except Exception as e:
        elapsed = time.time() - start_time

        print(f"\n❌ 실행 실패")
        print(f"   에러: {str(e)}")
        print(f"   실행 시간: {elapsed:.2f}초")

        return {
            "question": question,
            "type": q_type,
            "expected_tool": expected_tool,
            "actual_tool": "error",
            "tool_status": "failed",
            "pipeline": [],
            "success": False,
            "elapsed": elapsed,
            "answer_length": 0,
            "error": str(e)
        }


def run_all_tests(questions: List[Dict], difficulty: str, mode_name: str):
    """
    모든 질문 테스트 실행

    Args:
        questions: 질문 목록
        difficulty: 난이도
        mode_name: 모드 이름
    """
    print(f"\n{'#'*80}")
    print(f"# {mode_name} 테스트 시작")
    print(f"# 난이도: {difficulty}")
    print(f"# 총 질문 수: {len(questions)}개")
    print(f"{'#'*80}\n")

    # ExperimentManager 초기화
    exp_manager = ExperimentManager()

    results = []

    for i, q_data in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}]")
        result = run_test(q_data, difficulty, exp_manager)
        results.append(result)

        # 각 질문 사이 대기 (rate limit 방지)
        if i < len(questions):
            time.sleep(2)

    # 결과 요약
    print(f"\n\n{'='*80}")
    print(f"테스트 결과 요약 - {mode_name}")
    print(f"{'='*80}\n")

    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count

    print(f"성공: {success_count}/{len(results)}")
    print(f"실패: {failed_count}/{len(results)}")
    print(f"성공률: {success_count/len(results)*100:.1f}%")

    # 유형별 통계
    print(f"\n유형별 성공률:")
    for q_type in ["단일", "다중", "멀티턴"]:
        type_results = [r for r in results if r["type"] == q_type]
        if type_results:
            type_success = sum(1 for r in type_results if r["success"])
            print(f"  {q_type}: {type_success}/{len(type_results)} ({type_success/len(type_results)*100:.1f}%)")

    # 도구별 통계
    print(f"\n도구별 선택 횟수:")
    tool_counts = {}
    for r in results:
        tool = r["actual_tool"]
        tool_counts[tool] = tool_counts.get(tool, 0) + 1

    for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {tool}: {count}회")

    # 실패한 질문 상세
    if failed_count > 0:
        print(f"\n실패한 질문 상세:")
        for i, r in enumerate(results, 1):
            if not r["success"]:
                print(f"\n  [{i}] {r['question']}")
                print(f"      예상: {r['expected_tool']}")
                print(f"      실제: {r['actual_tool']}")
                print(f"      상태: {r['tool_status']}")
                if r["error"]:
                    print(f"      에러: {r['error'][:100]}")

    # 실험 종료
    exp_manager.close()

    print(f"\n실험 폴더: {exp_manager.experiment_dir}")

    return results


# ==================== 메인 실행 ==================== #
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="시나리오 테스트 실행")
    parser.add_argument("--mode", choices=["beginner", "expert", "both"], default="both",
                       help="테스트 모드 선택")
    args = parser.parse_args()

    if args.mode in ["beginner", "both"]:
        beginner_results = run_all_tests(BEGINNER_QUESTIONS, "easy", "초보자 모드")

    if args.mode in ["expert", "both"]:
        expert_results = run_all_tests(EXPERT_QUESTIONS, "hard", "전문가 모드")

    print(f"\n\n{'#'*80}")
    print("# 전체 테스트 완료")
    print(f"{'#'*80}")
