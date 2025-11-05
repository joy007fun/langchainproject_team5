#!/usr/bin/env python
"""용어 질문 도구 선택 테스트 스크립트

용어 정의 질문에 대해 glossary 도구가 올바르게 선택되는지 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.agent.question_classifier import classify_question
from src.llm.client import LLMClient
from src.prompts import get_routing_prompt


def test_question_classifier():
    """Question Classifier 테스트"""
    print("=" * 80)
    print("Question Classifier 테스트")
    print("=" * 80)

    test_cases = [
        ("nlp 용어가 뭐야?", "term_definition"),
        ("mamba 용어 설명해줘", "term_definition"),
        ("Transformer 용어가 뭐야?", "term_definition"),
        ("BERT가 뭐야?", "term_definition"),
        ("Attention 설명해줘", "term_definition"),
        ("Transformer 논문 찾아줘", "paper_search"),
    ]

    passed = 0
    failed = 0

    for question, expected in test_cases:
        result = classify_question(question, difficulty="easy")
        status = "✅ PASS" if result == expected else f"❌ FAIL (got: {result})"
        print(f"{status}: \"{question}\" → {expected}")

        if result == expected:
            passed += 1
        else:
            failed += 1

    print()
    print(f"총 {len(test_cases)}개 테스트: {passed}개 성공, {failed}개 실패")
    print("=" * 80)

    return failed == 0


def test_routing_prompt():
    """Routing Prompt 테스트"""
    print("\n" + "=" * 80)
    print("Routing Prompt 테스트")
    print("=" * 80)

    test_cases = [
        ("nlp 용어가 뭐야?", "glossary"),
        ("mamba 용어 설명해줘", "glossary"),
        ("Transformer 용어가 뭐야?", "glossary"),
        ("BERT가 뭐야?", "glossary"),
        ("Transformer 논문 찾아줘", "search_paper"),
    ]

    # Routing prompt 로드
    routing_prompt_template = get_routing_prompt()

    # LLM 초기화
    llm_client = LLMClient.from_difficulty(difficulty="easy")

    passed = 0
    failed = 0

    for question, expected in test_cases:
        routing_prompt = routing_prompt_template.format(question=question, difficulty="easy")

        try:
            raw_response = llm_client.llm.invoke(routing_prompt).content.strip()

            # 응답에서 도구명 추출 (첫 번째 단어)
            tool_choice = raw_response.split()[0].lower()

            # 유효한 도구 목록
            valid_tools = ["general", "glossary", "search_paper", "web_search", "summarize", "text2sql", "save_file"]

            if tool_choice not in valid_tools:
                tool_choice = "unknown"

            status = "✅ PASS" if tool_choice == expected else f"❌ FAIL (got: {tool_choice})"
            print(f"{status}: \"{question}\" → {expected}")

            if tool_choice == expected:
                passed += 1
            else:
                failed += 1
                print(f"   LLM 응답: {raw_response[:100]}")

        except Exception as e:
            print(f"❌ ERROR: \"{question}\" - {e}")
            failed += 1

    print()
    print(f"총 {len(test_cases)}개 테스트: {passed}개 성공, {failed}개 실패")
    print("=" * 80)

    return failed == 0


def main():
    """메인 함수"""
    print("\n")
    print("🔍 용어 질문 도구 선택 테스트")
    print()

    # Question Classifier 테스트
    classifier_passed = test_question_classifier()

    # Routing Prompt 테스트
    routing_passed = test_routing_prompt()

    print("\n" + "=" * 80)
    print("최종 결과")
    print("=" * 80)
    print(f"Question Classifier: {'✅ 모두 통과' if classifier_passed else '❌ 일부 실패'}")
    print(f"Routing Prompt: {'✅ 모두 통과' if routing_passed else '❌ 일부 실패'}")
    print("=" * 80)

    if classifier_passed and routing_passed:
        print("\n🎉 모든 테스트가 성공했습니다!")
        return 0
    else:
        print("\n⚠️  일부 테스트가 실패했습니다. 로그를 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
