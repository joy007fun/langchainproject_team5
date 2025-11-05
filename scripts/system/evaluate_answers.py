# scripts/evaluate_answers.py
"""
답변 평가 스크립트

LLM-as-a-Judge 방식으로 챗봇 답변의 품질을 평가하고,
평가 결과를 PostgreSQL에 저장합니다.
"""

# ------------------------- 표준 라이브러리 ------------------------- #
import json

# ------------------------- 프로젝트 모듈 ------------------------- #
from src.evaluation.evaluator import AnswerEvaluator
from src.evaluation.storage import save_evaluation_results, get_evaluation_statistics
from src.utils.experiment_manager import ExperimentManager


# ==================== 메인 실행부 ==================== #
if __name__ == "__main__":
    # ExperimentManager 초기화
    with ExperimentManager() as exp:
        exp.logger.write("=" * 60)
        exp.logger.write("답변 평가 스크립트 실행")
        exp.logger.write("=" * 60)

        # AnswerEvaluator 초기화
        evaluator = AnswerEvaluator(exp_manager=exp)

        # -------------- 테스트 케이스 정의 -------------- #
        # 테스트 케이스 정의
        test_cases = [
            {
                "question": "Transformer 논문 설명해줘",
                "answer": "Transformer는 2017년 Google에서 발표한 딥러닝 모델입니다. Self-Attention 메커니즘을 사용하여 시퀀스 데이터를 처리하며, Encoder-Decoder 구조를 가지고 있습니다. 저자는 Vaswani et al.입니다.",
                "reference_docs": "Attention Is All You Need (Vaswani et al., 2017)",
                "difficulty": "easy"
            },
            {
                "question": "BERT의 pre-training 방법은?",
                "answer": "BERT는 Masked Language Model (MLM)과 Next Sentence Prediction (NSP) 두 가지 방법으로 pre-training을 진행합니다. MLM은 입력 문장의 일부 단어를 마스킹하고 예측하며, NSP는 두 문장의 연속성을 판단합니다. BERT: Pre-training of Deep Bidirectional Transformers (Devlin et al., 2018) 논문에서 제안되었습니다.",
                "reference_docs": "BERT: Pre-training of Deep Bidirectional Transformers (Devlin et al., 2018)",
                "difficulty": "hard"
            }
        ]

        # -------------- 배치 평가 수행 -------------- #
        # 배치 평가 수행
        exp.logger.write(f"테스트 케이스 {len(test_cases)}개 평가 시작")
        results = evaluator.evaluate_batch(test_cases)

        # -------------- 평가 결과 저장 -------------- #
        # 평가 결과 저장
        exp.logger.write("평가 결과 PostgreSQL에 저장")
        save_evaluation_results(results)

        # -------------- 평가 통계 조회 -------------- #
        # 평가 통계 조회
        stats = get_evaluation_statistics()
        exp.logger.write(f"평가 통계: {json.dumps(stats, indent=2, ensure_ascii=False)}")

        # -------------- 평가 결과 출력 -------------- #
        # 평가 결과 출력
        exp.logger.write("=" * 60)
        exp.logger.write("평가 완료")
        for i, result in enumerate(results, 1):
            exp.logger.write(f"\n[테스트 {i}]")
            exp.logger.write(f"질문: {result['question']}")
            exp.logger.write(f"총점: {result['total_score']}/40")
            exp.logger.write(f"- 정확도: {result['accuracy_score']}/10")
            exp.logger.write(f"- 관련성: {result['relevance_score']}/10")
            exp.logger.write(f"- 난이도 적합성: {result['difficulty_score']}/10")
            exp.logger.write(f"- 출처 명시: {result['citation_score']}/10")
            exp.logger.write(f"코멘트: {result['comment']}")

        exp.logger.write("=" * 60)
