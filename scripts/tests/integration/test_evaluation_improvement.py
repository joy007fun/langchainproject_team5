# scripts/test_evaluation_improvement.py
"""
평가 시스템 개선 테스트 스크립트

구체적 평가 기준 추가 후 일관성 및 정확성 검증
"""

# ------------------------- 표준 라이브러리 ------------------------- #
import sys
import os
from pathlib import Path
import time

# ------------------------- 프로젝트 루트 경로 추가 ------------------------- #
sys.path.insert(0, str(Path(__file__).parent.parent))

# ------------------------- 서드파티 라이브러리 ------------------------- #
import numpy as np
from dotenv import load_dotenv

# ------------------------- 환경 변수 로드 ------------------------- #
load_dotenv()

# ------------------------- 프로젝트 모듈 ------------------------- #
from src.evaluation.evaluator import AnswerEvaluator
from src.utils.experiment_manager import ExperimentManager


# ==================== 테스트 케이스 정의 ==================== #
TEST_CASES = [
    # 테스트 1: 우수 답변 (예상: 35-40점)
    {
        "name": "우수 답변 (완벽한 답변)",
        "question": "Transformer의 핵심 구조는?",
        "answer": "Transformer는 Self-Attention과 Feed-Forward Neural Network로 구성됩니다. "
                 "Attention Is All You Need (Vaswani et al., 2017) 논문에서 제안되었으며, "
                 "Self-Attention 메커니즘은 입력 시퀀스의 각 위치가 다른 모든 위치와의 관계를 학습합니다.",
        "reference_docs": "Transformer는 Self-Attention과 Feed-Forward Neural Network로 구성됩니다. "
                         "각 레이어는 Multi-Head Attention과 Position-wise FFN으로 이루어져 있습니다.",
        "difficulty": "easy",
        "expected_scores": {
            "accuracy": (9, 10),
            "relevance": (9, 10),
            "difficulty": (8, 10),
            "citation": (10, 10),
            "total": (36, 40)
        }
    },

    # 테스트 2: 보통 답변 (예상: 20-27점)
    {
        "name": "보통 답변 (일부 누락)",
        "question": "BERT의 학습 방법은?",
        "answer": "BERT는 Masked Language Modeling으로 사전학습합니다.",
        "reference_docs": "BERT는 Masked Language Modeling (MLM)과 Next Sentence Prediction (NSP) "
                         "두 가지 태스크로 사전학습합니다.",
        "difficulty": "easy",
        "expected_scores": {
            "accuracy": (4, 6),
            "relevance": (9, 10),
            "difficulty": (8, 10),
            "citation": (0, 0),
            "total": (21, 26)
        }
    },

    # 테스트 3: 미흡 답변 (예상: 10-19점)
    {
        "name": "미흡 답변 (관련성 부족)",
        "question": "GPT의 학습 방법은?",
        "answer": "GPT는 자연어 처리에 사용되는 모델입니다.",
        "reference_docs": "GPT는 Causal Language Modeling (CLM) 방식으로 사전학습하며, "
                         "이전 토큰들을 기반으로 다음 토큰을 예측합니다.",
        "difficulty": "easy",
        "expected_scores": {
            "accuracy": (1, 3),
            "relevance": (2, 4),
            "difficulty": (7, 9),
            "citation": (0, 0),
            "total": (10, 16)
        }
    },

    # 테스트 4: Easy 모드 부적합 (예상: 난이도 1-3점)
    {
        "name": "난이도 부적합 (Easy인데 Hard 수준)",
        "question": "Attention 메커니즘이란?",
        "answer": "Attention(Q, K, V) = softmax(QK^T / √d_k)V로 계산되는 메커니즘입니다.",
        "reference_docs": "Attention은 Query, Key, Value의 내적으로 계산되며, "
                         "중요한 부분에 집중하는 메커니즘입니다.",
        "difficulty": "easy",
        "expected_scores": {
            "accuracy": (7, 9),
            "relevance": (9, 10),
            "difficulty": (1, 3),
            "citation": (0, 0),
            "total": (17, 22)
        }
    },

    # 테스트 5: Hard 모드 적합 (예상: 난이도 9-10점)
    {
        "name": "난이도 적합 (Hard 모드)",
        "question": "Transformer의 Self-Attention 계산 방법은?",
        "answer": "Self-Attention은 Attention(Q, K, V) = softmax(QK^T / √d_k)V로 계산됩니다. "
                 "여기서 Q, K, V는 각각 Query, Key, Value 행렬이며, "
                 "d_k는 Key의 차원입니다. Attention Is All You Need (Vaswani et al., 2017)에서 제안되었습니다.",
        "reference_docs": "Self-Attention은 Query, Key, Value의 내적으로 계산되며, "
                         "스케일링 팩터 √d_k로 나누어 안정성을 높입니다.",
        "difficulty": "hard",
        "expected_scores": {
            "accuracy": (9, 10),
            "relevance": (9, 10),
            "difficulty": (9, 10),
            "citation": (10, 10),
            "total": (37, 40)
        }
    },
]


# ==================== 일관성 테스트 함수 ==================== #
def test_consistency(evaluator: AnswerEvaluator, test_case: dict, num_runs: int = 5):
    """
    동일 답변 반복 평가 → 일관성 검증

    Args:
        evaluator: AnswerEvaluator 인스턴스
        test_case: 테스트 케이스
        num_runs: 반복 횟수

    Returns:
        dict: 일관성 통계
    """
    print(f"\n[일관성 테스트] {test_case['name']}")
    print(f"{'='*60}")
    print(f"질문: {test_case['question']}")
    print(f"답변: {test_case['answer'][:80]}...")
    print()

    results = []

    for i in range(num_runs):
        print(f"평가 {i+1}/{num_runs}...", end=" ")

        result = evaluator.evaluate(
            question=test_case["question"],
            answer=test_case["answer"],
            reference_docs=test_case["reference_docs"],
            difficulty=test_case["difficulty"]
        )

        results.append(result)
        print(f"총점: {result['total_score']}/40")
        time.sleep(0.5)  # API Rate Limit 방지

    # 통계 계산
    accuracy_scores = [r['accuracy_score'] for r in results]
    relevance_scores = [r['relevance_score'] for r in results]
    difficulty_scores = [r['difficulty_score'] for r in results]
    citation_scores = [r['citation_score'] for r in results]
    total_scores = [r['total_score'] for r in results]

    stats = {
        "accuracy": {
            "mean": np.mean(accuracy_scores),
            "std": np.std(accuracy_scores),
            "min": np.min(accuracy_scores),
            "max": np.max(accuracy_scores)
        },
        "relevance": {
            "mean": np.mean(relevance_scores),
            "std": np.std(relevance_scores),
            "min": np.min(relevance_scores),
            "max": np.max(relevance_scores)
        },
        "difficulty": {
            "mean": np.mean(difficulty_scores),
            "std": np.std(difficulty_scores),
            "min": np.min(difficulty_scores),
            "max": np.max(difficulty_scores)
        },
        "citation": {
            "mean": np.mean(citation_scores),
            "std": np.std(citation_scores),
            "min": np.min(citation_scores),
            "max": np.max(citation_scores)
        },
        "total": {
            "mean": np.mean(total_scores),
            "std": np.std(total_scores),
            "min": np.min(total_scores),
            "max": np.max(total_scores)
        }
    }

    # 결과 출력
    print(f"\n[통계 결과]")
    print(f"{'항목':<15} {'평균':<8} {'표준편차':<10} {'범위':<15}")
    print(f"{'-'*60}")
    print(f"{'정확도':<15} {stats['accuracy']['mean']:.2f}   {stats['accuracy']['std']:.2f}       "
          f"{stats['accuracy']['min']:.0f} ~ {stats['accuracy']['max']:.0f}")
    print(f"{'관련성':<15} {stats['relevance']['mean']:.2f}   {stats['relevance']['std']:.2f}       "
          f"{stats['relevance']['min']:.0f} ~ {stats['relevance']['max']:.0f}")
    print(f"{'난이도 적합성':<15} {stats['difficulty']['mean']:.2f}   {stats['difficulty']['std']:.2f}       "
          f"{stats['difficulty']['min']:.0f} ~ {stats['difficulty']['max']:.0f}")
    print(f"{'출처 명시':<15} {stats['citation']['mean']:.2f}   {stats['citation']['std']:.2f}       "
          f"{stats['citation']['min']:.0f} ~ {stats['citation']['max']:.0f}")
    print(f"{'-'*60}")
    print(f"{'총점':<15} {stats['total']['mean']:.2f}   {stats['total']['std']:.2f}       "
          f"{stats['total']['min']:.0f} ~ {stats['total']['max']:.0f}")

    # 목표 달성 여부
    print(f"\n[목표 달성 여부]")
    all_std_ok = all(
        stats[key]['std'] <= 1.0
        for key in ['accuracy', 'relevance', 'difficulty', 'citation']
    )

    if all_std_ok:
        print(f"✅ 모든 항목의 표준편차가 1.0 이하입니다 (우수)")
    elif stats['total']['std'] <= 1.5:
        print(f"✅ 총점 표준편차가 1.5 이하입니다 (양호)")
    else:
        print(f"⚠️  일관성 개선이 필요합니다 (표준편차 > 1.5)")

    return stats


# ==================== 점수 분포 검증 함수 ==================== #
def test_score_distribution(evaluator: AnswerEvaluator):
    """
    다양한 품질의 답변 평가 → 점수 분포 검증

    Args:
        evaluator: AnswerEvaluator 인스턴스
    """
    print(f"\n\n{'='*80}")
    print(f"[점수 분포 검증]")
    print(f"{'='*80}\n")

    results = []

    for test_case in TEST_CASES:
        print(f"\n테스트: {test_case['name']}")
        print(f"{'-'*60}")

        result = evaluator.evaluate(
            question=test_case["question"],
            answer=test_case["answer"],
            reference_docs=test_case["reference_docs"],
            difficulty=test_case["difficulty"]
        )

        results.append({
            "name": test_case["name"],
            "expected": test_case["expected_scores"],
            "actual": result
        })

        # 결과 출력
        print(f"정확도: {result['accuracy_score']}/10 "
              f"(예상: {test_case['expected_scores']['accuracy'][0]}-{test_case['expected_scores']['accuracy'][1]})")
        print(f"관련성: {result['relevance_score']}/10 "
              f"(예상: {test_case['expected_scores']['relevance'][0]}-{test_case['expected_scores']['relevance'][1]})")
        print(f"난이도: {result['difficulty_score']}/10 "
              f"(예상: {test_case['expected_scores']['difficulty'][0]}-{test_case['expected_scores']['difficulty'][1]})")
        print(f"출처:  {result['citation_score']}/10 "
              f"(예상: {test_case['expected_scores']['citation'][0]}-{test_case['expected_scores']['citation'][1]})")
        print(f"총점:  {result['total_score']}/40 "
              f"(예상: {test_case['expected_scores']['total'][0]}-{test_case['expected_scores']['total'][1]})")

        # 예상 범위 내 포함 여부
        in_range = (
            test_case['expected_scores']['total'][0] <= result['total_score'] <= test_case['expected_scores']['total'][1]
        )

        if in_range:
            print(f"✅ 예상 범위 내 포함")
        else:
            print(f"⚠️  예상 범위 벗어남")

        print(f"코멘트: {result['comment']}")

        time.sleep(0.5)  # API Rate Limit 방지

    # 전체 요약
    print(f"\n\n{'='*80}")
    print(f"[전체 요약]")
    print(f"{'='*80}\n")

    in_range_count = sum(
        1 for r in results
        if r['expected']['total'][0] <= r['actual']['total_score'] <= r['expected']['total'][1]
    )

    print(f"테스트 케이스: {len(TEST_CASES)}개")
    print(f"예상 범위 내: {in_range_count}개 ({in_range_count/len(TEST_CASES)*100:.1f}%)")
    print(f"예상 범위 밖: {len(TEST_CASES) - in_range_count}개")

    if in_range_count >= len(TEST_CASES) * 0.8:
        print(f"\n✅ 점수 분포 검증 통과 (80% 이상)")
    else:
        print(f"\n⚠️  점수 분포 개선 필요 (80% 미만)")


# ==================== 메인 함수 ==================== #
def main():
    """메인 함수"""
    print(f"\n{'='*80}")
    print(f"평가 시스템 개선 테스트")
    print(f"{'='*80}\n")

    # ExperimentManager 생성
    with ExperimentManager() as exp_manager:
        exp_manager.logger.write("평가 시스템 개선 테스트 시작")

        # AnswerEvaluator 초기화
        evaluator = AnswerEvaluator(exp_manager=exp_manager)

        # 1. 일관성 테스트 (첫 번째 테스트 케이스만)
        consistency_stats = test_consistency(
            evaluator=evaluator,
            test_case=TEST_CASES[0],
            num_runs=5
        )

        # 2. 점수 분포 검증
        test_score_distribution(evaluator=evaluator)

        exp_manager.logger.write("평가 시스템 개선 테스트 완료")

        print(f"\n\n{'='*80}")
        print(f"테스트 완료!")
        print(f"{'='*80}\n")


# ==================== 실행 ==================== #
if __name__ == "__main__":
    main()
