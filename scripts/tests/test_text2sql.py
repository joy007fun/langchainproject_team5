#!/usr/bin/env python3
"""
Text2SQL 도구 테스트 스크립트

난이도별로 text2sql 도구를 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.text2sql import text2sql


def test_text2sql_tool():
    """
    Text2SQL 도구 테스트
    """
    # 테스트 질문들
    test_questions = [
        "2024년에 발표된 논문 개수는?",
        "카테고리별 논문 수를 보여줘",
        "AI 관련 논문 중 가장 인용이 많은 건?"
    ]

    # 난이도 리스트
    difficulties = ["elementary", "beginner", "intermediate", "advanced"]

    for question in test_questions:
        print("\n" + "=" * 80)
        print(f"📊 질문: {question}")
        print("=" * 80)

        for difficulty in difficulties:
            print(f"\n🎯 난이도: {difficulty}")
            print("-" * 80)

            try:
                result = text2sql.run({
                    "user_question": question,
                    "difficulty": difficulty
                })

                print(result)

            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()

            # 구분선
            print("\n" + "─" * 80)


if __name__ == "__main__":
    print("Text2SQL 도구 테스트 시작...\n")
    test_text2sql_tool()
    print("\n✅ 테스트 완료")
