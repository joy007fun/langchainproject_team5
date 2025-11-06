#!/usr/bin/env python3
"""Failure Detector 패턴 테스트"""

import sys
sys.path.insert(0, '/home/ieyeppo/AI_Lab/langchain-project')

from src.agent.failure_detector import is_tool_failed

def test_failure_detection():
    """Failure Detection 패턴 테스트"""

    test_cases = [
        # (text, should_fail, description)
        ("사실적 오류 감소와 정확한 근거 있는 답변", False, "긍정적 맥락의 '오류' - 실패 아님"),
        ("오류 방지 기능 추가", False, "긍정적 맥락의 '오류' - 실패 아님"),
        ("실패를 극복하는 방법", False, "긍정적 맥락의 '실패' - 실패 아님"),
        ("오류가 발생했습니다", True, "부정적 맥락 - 실패"),
        ("오류 발생", True, "부정적 맥락 - 실패"),
        ("실행 중 오류", True, "부정적 맥락 - 실패"),
        ("생성에 실패했습니다", True, "부정적 맥락 - 실패"),
        ("관련 논문을 찾을 수 없습니다", True, "검색 실패 - 실패"),
        ("검색 결과가 없습니다", True, "결과 없음 - 실패"),
        ("정상적인 답변입니다", False, "정상 답변 - 실패 아님"),
    ]

    print("\n" + "="*80)
    print("🔍 Failure Detection 패턴 테스트")
    print("="*80)

    passed = 0
    failed = 0

    for text, should_fail, description in test_cases:
        is_failed, reason = is_tool_failed(text)

        status = "✅" if is_failed == should_fail else "❌"
        result = "실패 감지" if is_failed else "성공 감지"

        if is_failed == should_fail:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} {description}")
        print(f"   텍스트: '{text}'")
        print(f"   예상: {'실패' if should_fail else '성공'}, 실제: {result}")
        if is_failed:
            print(f"   사유: {reason}")

    print("\n" + "="*80)
    print(f"결과: {passed}/{len(test_cases)} 통과, {failed}/{len(test_cases)} 실패")
    print("="*80)

if __name__ == "__main__":
    test_failure_detection()
