# src/agent/failure_detector.py
"""
도구 실행 실패 감지 모듈

도구 실행 결과를 분석하여 실패 여부를 감지하고,
Fallback Chain 메커니즘을 트리거합니다.
"""

# ------------------------- 표준 라이브러리 ------------------------- #
import re
from typing import List, Tuple


# ==================== FailureDetector 클래스 ==================== #
class FailureDetector:
    """
    도구 실행 실패 감지 클래스

    도구가 반환한 결과를 분석하여 실패 패턴을 감지합니다.
    """

    # 실패 패턴 리스트 (정확한 문자열 매칭)
    FAILURE_PATTERNS = [
        "관련 용어를 찾을 수 없습니다",
        "관련 논문을 찾을 수 없습니다",
        "검색 결과가 없습니다",
        "파일 경로를 지정해주세요",
        "SQL 쿼리 생성에 실패했습니다",
        "오류가 발생했습니다",
        "검색된 논문이 없습니다",
        "결과를 찾을 수 없습니다",
        "찾을 수 없습니다",
        "데이터베이스에서 찾지 못했습니다",
        "검색에 실패했습니다",
    ]

    # 정규식 패턴 리스트 (유연한 매칭)
    REGEX_PATTERNS = [
        r".*찾을\s*수\s*없.*",           # "찾을 수 없" 패턴
        r".*결과가?\s*없.*",            # "결과가 없" 패턴
        r".*오류.*",                    # "오류" 패턴
        r".*실패.*",                    # "실패" 패턴
        r".*에러.*",                    # "에러" 패턴
        r"ERROR.*",                     # "ERROR" 패턴
        r".*exception.*",               # "exception" 패턴 (소문자)
    ]

    def __init__(self, custom_patterns: List[str] = None):
        """
        FailureDetector 초기화

        Args:
            custom_patterns: 사용자 정의 실패 패턴 리스트
        """
        self.failure_patterns = self.FAILURE_PATTERNS.copy()

        # 사용자 정의 패턴 추가
        if custom_patterns:
            self.failure_patterns.extend(custom_patterns)

        # 정규식 패턴 컴파일
        self.compiled_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.REGEX_PATTERNS
        ]

    def is_failed(self, result: str) -> Tuple[bool, str]:
        """
        도구 실행 결과가 실패인지 확인

        Args:
            result: 도구 실행 결과 문자열

        Returns:
            Tuple[bool, str]: (실패 여부, 실패 사유)
        """
        if not result:
            return True, "빈 결과"

        result_lower = result.lower()

        # 1. 정확한 문자열 매칭
        for pattern in self.failure_patterns:
            if pattern in result:
                return True, f"패턴 감지: {pattern}"

        # 2. 정규식 매칭
        for regex in self.compiled_regex:
            if regex.search(result):
                return True, f"정규식 패턴 매치: {regex.pattern}"

        # 실패 패턴이 감지되지 않음
        return False, ""

    def add_custom_pattern(self, pattern: str):
        """
        사용자 정의 실패 패턴 추가

        Args:
            pattern: 추가할 실패 패턴
        """
        if pattern not in self.failure_patterns:
            self.failure_patterns.append(pattern)

    def remove_pattern(self, pattern: str):
        """
        실패 패턴 제거

        Args:
            pattern: 제거할 실패 패턴
        """
        if pattern in self.failure_patterns:
            self.failure_patterns.remove(pattern)

    def get_patterns(self) -> List[str]:
        """
        현재 등록된 실패 패턴 리스트 반환

        Returns:
            List[str]: 실패 패턴 리스트
        """
        return self.failure_patterns.copy()


# ==================== 전역 인스턴스 ==================== #
# 싱글톤 패턴으로 전역에서 사용
_global_detector = FailureDetector()


def is_tool_failed(result: str) -> Tuple[bool, str]:
    """
    도구 실행 실패 여부 확인 (전역 함수)

    Args:
        result: 도구 실행 결과

    Returns:
        Tuple[bool, str]: (실패 여부, 실패 사유)
    """
    return _global_detector.is_failed(result)


def add_failure_pattern(pattern: str):
    """
    전역 실패 패턴 추가

    Args:
        pattern: 추가할 실패 패턴
    """
    _global_detector.add_custom_pattern(pattern)


def get_failure_patterns() -> List[str]:
    """
    전역 실패 패턴 리스트 반환

    Returns:
        List[str]: 실패 패턴 리스트
    """
    return _global_detector.get_patterns()
