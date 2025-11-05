# src/agent/state.py
"""
Agent 상태 정의 모듈

LangGraph Agent의 상태(State)를 TypedDict로 정의:
- 사용자 질문 및 난이도
- 도구 선택 및 실행 결과
- 최종 답변
- 대화 히스토리
"""

# ------------------------- 표준 라이브러리 ------------------------- #
from typing import TypedDict, List, Dict, Any, Optional
# TypedDict: 타입 힌트가 포함된 딕셔너리


# ==================== Agent 상태 정의 ==================== #
class AgentState(TypedDict, total=False):
    """
    LangGraph Agent의 상태 정의

    Attributes:
        question (str): 사용자 질문
        difficulty (str): 난이도 ('easy' 또는 'hard')
        tool_choice (str): 선택된 도구 이름
        tool_result (str): 도구 실행 결과
        final_answer (str): 최종 답변
        messages (list): 대화 히스토리 (메시지 리스트)
        source_documents (list): 참고 논문 문서 리스트 (선택 사항)

        # Fallback Chain 관련 필드
        retry_count (int): 현재 재시도 횟수
        failed_tools (List[str]): 실패한 도구 리스트
        question_type (str): 질문 유형 (term_definition, paper_search 등)
        fallback_chain (List[str]): 현재 질문에 대한 도구 우선순위 리스트
        validation_failed (bool): Router 검증 실패 여부
        tool_status (str): 도구 실행 상태 (success, failed, partial, error)
        failure_reason (str): 도구 실패 사유
        tool_timeline (List[Dict[str, Any]]): 도구 실행 타임라인
        max_retries (int): 최대 재시도 횟수
        validation_enabled (bool): Router 검증 활성화 여부
        validation_retries (int): 현재 검증 재시도 횟수
        max_validation (int): 최대 검증 재시도 횟수
    """
    # 기본 필드
    question: str                               # 사용자 질문
    difficulty: str                             # 난이도 (easy/hard)
    tool_choice: str                            # 선택된 도구
    tool_result: str                            # 도구 실행 결과
    final_answer: str                           # 최종 답변 (하위 호환성)
    final_answers: Dict[str, str]               # 두 수준의 답변 {"elementary": "...", "beginner": "..."} or {"intermediate": "...", "advanced": "..."}
    messages: list                              # 대화 히스토리
    source_documents: list                      # 참고 논문 문서

    # Fallback Chain 관련 필드
    retry_count: int                            # 현재 재시도 횟수
    failed_tools: List[str]                     # 실패한 도구 리스트
    question_type: str                          # 질문 유형
    fallback_chain: List[str]                   # 도구 우선순위 리스트
    validation_failed: bool                     # Router 검증 실패 여부
    tool_status: str                            # 도구 실행 상태
    failure_reason: str                         # 도구 실패 사유
    tool_timeline: List[Dict[str, Any]]         # 도구 실행 타임라인
    max_retries: int                            # 최대 재시도 횟수
    validation_enabled: bool                    # Router 검증 활성화 여부
    validation_retries: int                     # 현재 검증 재시도 횟수
    max_validation: int                         # 최대 검증 재시도 횟수

    # 다중 요청 Pipeline 관련 필드
    tool_pipeline: List[str]                    # 순차 실행 도구 리스트
    pipeline_index: int                         # 현재 Pipeline 실행 인덱스
