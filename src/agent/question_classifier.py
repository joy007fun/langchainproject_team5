# src/agent/question_classifier.py
"""
질문 유형 분류 모듈

사용자 질문을 분석하여 7가지 유형 중 하나로 분류하고,
적절한 도구 우선순위를 결정합니다.
"""

# ------------------------- 표준 라이브러리 ------------------------- #
from typing import Dict

# ------------------------- 프로젝트 모듈 ------------------------- #
from src.llm.client import LLMClient


# ==================== QuestionClassifier 클래스 ==================== #
class QuestionClassifier:
    """
    질문 유형 분류 클래스

    LLM을 사용하여 사용자 질문을 7가지 유형으로 분류합니다.
    """

    # 질문 유형 설명
    QUESTION_TYPES = {
        "term_definition": "AI/ML 용어의 정의를 묻는 질문",
        "paper_search": "특정 논문을 검색하거나 찾는 질문",
        "latest_research": "최신 연구 동향이나 최근 논문을 묻는 질문",
        "paper_summary": "논문의 요약을 요청하는 질문",
        "statistics": "논문 개수, 저자, 연도 등 통계 정보를 묻는 질문",
        "file_save": "답변을 파일로 저장해달라는 요청",
        "general_question": "위 카테고리에 속하지 않는 일반적인 질문"
    }

    # 분류 프롬프트 템플릿
    CLASSIFICATION_PROMPT = """다음 질문을 7가지 유형 중 하나로 분류하세요.

질문 유형:
1. term_definition - AI/ML 용어의 정의를 묻는 질문
   예시: "Attention이 뭐야?", "BLEU Score 설명해줘", "Transformer란?", "nlp 용어가 뭐야?", "Transformer 용어 설명해줘"

2. paper_search - 특정 논문을 검색하거나 찾는 질문
   예시: "Transformer 논문 찾아줘", "GAN 관련 논문 검색해줘"

3. latest_research - 최신 연구 동향이나 최근 논문을 묻는 질문
   예시: "2024년 최신 LLM 논문은?", "최근 Diffusion Model 연구는?"

4. paper_summary - 논문의 요약을 요청하는 질문
   예시: "Attention is All You Need 논문 요약해줘"

5. statistics - 논문 개수, 저자, 연도 등 통계 정보를 묻는 질문
   예시: "2023년에 발표된 논문 개수는?", "가장 많이 인용된 논문은?"

6. file_save - 답변을 파일로 저장해달라는 요청
   예시: "답변을 파일로 저장해줘", "이거 파일로 저장"

7. general_question - 위 카테고리에 속하지 않는 일반적인 질문
   예시: "GAN에 대해 설명해줘", "딥러닝의 역사는?"

질문: {question}

위 질문의 유형을 하나만 선택하여 답변하세요.
답변은 반드시 다음 중 하나여야 합니다:
term_definition, paper_search, latest_research, paper_summary, statistics, file_save, general_question

답변:"""

    def __init__(self, logger=None):
        """
        QuestionClassifier 초기화

        Args:
            logger: 로거 인스턴스 (선택 사항)
        """
        self.logger = logger
        self.cache: Dict[str, str] = {}  # 질문 → 유형 캐시

    def classify(self, question: str, difficulty: str = "easy") -> str:
        """
        질문 유형 분류

        Args:
            question: 사용자 질문
            difficulty: 난이도 (easy/hard)

        Returns:
            str: 질문 유형 (term_definition, paper_search 등)
        """
        # 캐시 확인
        if question in self.cache:
            if self.logger:
                self.logger.write(f"질문 유형 캐시 적중: {self.cache[question]}")
            return self.cache[question]

        # LLM 초기화 (분류는 temperature=0.0으로 결정론적)
        llm_client = LLMClient.from_difficulty(
            difficulty=difficulty,
            logger=self.logger
        )

        # 프롬프트 생성
        prompt = self.CLASSIFICATION_PROMPT.format(question=question)

        # LLM 호출
        try:
            response = llm_client.llm.invoke(prompt).content.strip()

            # 응답 파싱 (첫 번째 단어만 추출)
            question_type = response.split()[0].lower()

            # 유효성 검증
            if question_type not in self.QUESTION_TYPES:
                if self.logger:
                    self.logger.write(f"경고: 유효하지 않은 질문 유형: {question_type}")
                    self.logger.write("기본값 'general_question' 사용")
                question_type = "general_question"

            # 캐시 저장
            self.cache[question] = question_type

            if self.logger:
                self.logger.write(f"질문 유형 분류 완료: {question_type}")

            return question_type

        except Exception as e:
            if self.logger:
                self.logger.write(f"질문 유형 분류 실패: {e}", print_error=True)
                self.logger.write("기본값 'general_question' 사용")

            # 실패 시 기본값
            return "general_question"

    def clear_cache(self):
        """
        분류 캐시 초기화
        """
        self.cache.clear()

    def get_cache_size(self) -> int:
        """
        캐시 크기 반환

        Returns:
            int: 캐시된 질문 개수
        """
        return len(self.cache)


# ==================== 전역 인스턴스 ==================== #
_global_classifier = QuestionClassifier()


def classify_question(question: str, difficulty: str = "easy", logger=None) -> str:
    """
    질문 유형 분류 (전역 함수)

    Args:
        question: 사용자 질문
        difficulty: 난이도 (easy/hard)
        logger: 로거 인스턴스

    Returns:
        str: 질문 유형
    """
    if logger:
        _global_classifier.logger = logger

    return _global_classifier.classify(question, difficulty)


def clear_classification_cache():
    """
    전역 분류 캐시 초기화
    """
    _global_classifier.clear_cache()
