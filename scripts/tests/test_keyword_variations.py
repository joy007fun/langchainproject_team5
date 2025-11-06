#!/usr/bin/env python3
"""키워드 변형 패턴 매칭 테스트"""

import sys
sys.path.insert(0, '/home/ieyeppo/AI_Lab/langchain-project')

from src.agent.config_loader import get_multi_request_patterns

def test_keyword_variations():
    """키워드 변형 패턴 테스트"""

    # 패턴 로드
    patterns = get_multi_request_patterns()

    print("\n" + "="*80)
    print("🔍 키워드 변형 패턴 매칭 테스트")
    print("="*80)

    # 테스트 케이스: (질문, 예상 도구 목록, 설명)
    test_cases = [
        # 용어 정의만 (단일 도구)
        ("LLM이 뭐야?", ["glossary"], "뭐야 - 단일 용어 정의"),
        ("Transformer가 뭔데?", ["glossary"], "뭔데 - 단일 용어 정의"),
        ("RAG 뭔지 알려줘", ["glossary"], "뭔지 - 단일 용어 정의"),
        ("BERT가 무엇인지 설명해줘", ["glossary"], "무엇인지 - 단일 용어 정의"),
        ("Attention 어떤건지 알려줘", ["glossary"], "어떤건지 - 단일 용어 정의"),
        ("GPT 어떤거야?", ["glossary"], "어떤거야 - 단일 용어 정의"),

        # 용어 정의 + 논문 검색 (복합 도구)
        ("RAG가 뭐야? 관련 논문도 보여줘", ["glossary", "search_paper"], "뭐야 + 논문 - 복합"),
        ("Transformer가 뭔데? 논문도 찾아줘", ["glossary", "search_paper"], "뭔데 + 논문 - 복합"),
        ("LLM이 뭔지 설명하고 논문도 검색해줘", ["glossary", "search_paper"], "뭔지 + 논문 - 복합"),
        ("BERT가 무엇인지 알려주고 논문도 보여줘", ["glossary", "search_paper"], "무엇인지 + 논문 - 복합"),
        ("Attention 어떤건지 설명하고 논문도 찾아줘", ["glossary", "search_paper"], "어떤건지 + 논문 - 복합"),
        ("GPT 어떤거야? 논문 찾아줘", ["glossary", "search_paper"], "어떤거야 + 논문 - 복합"),

        # 용어 정의 + 저장 (복합 도구)
        ("LLM이 뭐야? 저장해줘", ["glossary", "save_file"], "뭐야 + 저장 - 복합"),
        ("Transformer가 뭔데? 저장해줘", ["glossary", "save_file"], "뭔데 + 저장 - 복합"),
        ("RAG 뭔지 알려주고 저장해줘", ["glossary", "save_file"], "뭔지 + 저장 - 복합"),
        ("BERT가 무엇인지 설명하고 저장해줘", ["glossary", "save_file"], "무엇인지 + 저장 - 복합"),
        ("Attention 어떤건지 찾아서 저장해줘", ["glossary", "save_file"], "어떤건지 + 저장 - 복합"),
        ("GPT 어떤거야? 저장해줘", ["glossary", "save_file"], "어떤거야 + 저장 - 복합"),
    ]

    passed = 0
    failed = 0

    for question, expected_tools, description in test_cases:
        # 패턴 매칭 수행
        matched_pattern = None
        matched_tools = None

        for pattern in patterns:
            keywords = pattern.get("keywords", [])
            any_of_keywords = pattern.get("any_of_keywords", [])
            exclude_keywords = pattern.get("exclude_keywords", [])
            tools = pattern.get("tools", [])

            # AND 로직: 모든 keywords가 포함되어야 함
            keywords_match = all(kw in question for kw in keywords)

            # OR 로직: any_of_keywords 중 하나라도 포함되면 됨
            any_keywords_match = any(kw in question for kw in any_of_keywords) if any_of_keywords else True

            # 제외 키워드 확인
            exclude_match = any(ex_kw in question for ex_kw in exclude_keywords) if exclude_keywords else False

            if keywords_match and any_keywords_match and not exclude_match:
                matched_pattern = pattern
                matched_tools = tools
                break

        # 결과 검증
        if matched_tools == expected_tools:
            status = "✅"
            passed += 1
        else:
            status = "❌"
            failed += 1

        print(f"\n{status} {description}")
        print(f"   질문: '{question}'")
        print(f"   예상: {expected_tools}")
        print(f"   실제: {matched_tools}")

        if matched_pattern:
            pattern_desc = matched_pattern.get('description', 'N/A')
            priority = matched_pattern.get('priority', 'N/A')
            print(f"   패턴: {pattern_desc} (우선순위: {priority})")

    print("\n" + "="*80)
    print(f"결과: {passed}/{len(test_cases)} 통과, {failed}/{len(test_cases)} 실패")
    print("="*80)

    return failed == 0

if __name__ == "__main__":
    success = test_keyword_variations()
    sys.exit(0 if success else 1)
