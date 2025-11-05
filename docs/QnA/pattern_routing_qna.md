# 패턴 기반 도구 라우팅 Q&A

## 문서 정보
- **작성일**: 2025-11-05
- **작성자**: 최현화[팀장]
- **목적**: 패턴 기반 도구 라우팅 시스템 관련 자주 묻는 질문 및 답변

---

## 목차
1. [기본 개념](#1-기본-개념)
2. [패턴 파일 이해하기](#2-패턴-파일-이해하기)
3. [패턴 매칭 동작 방식](#3-패턴-매칭-동작-방식)
4. [패턴 추가/수정하기](#4-패턴-추가수정하기)
5. [우선순위와 충돌](#5-우선순위와-충돌)
6. [Exclude Keywords](#6-exclude-keywords)
7. [Multi-turn 대응](#7-multi-turn-대응)
8. [트러블슈팅](#8-트러블슈팅)
9. [실전 예제](#9-실전-예제)

---

## 1. 기본 개념

### Q1-1. 패턴 기반 라우팅이란 무엇인가요?

**A:** **사용자 질문의 키워드를 보고 어떤 도구를 실행할지 자동으로 결정하는 시스템**입니다.

**비유로 설명하면**:
- 음식점에서 메뉴를 보고 주문하는 것과 비슷합니다
- "김치찌개" 메뉴를 보면 → 주방에서 김치찌개를 만듦
- "논문 요약" 키워드를 보면 → search_paper + summarize 도구 실행

**예시**:
```
사용자 질문: "Transformer 논문 요약해줘"
         ↓
키워드 확인: "논문" + "요약" 포함?
         ↓
패턴 매칭: ✅ 성공!
         ↓
도구 선택: [search_paper, web_search, general, summarize]
```

---

### Q1-2. LLM 라우팅과 무엇이 다른가요?

**A:** **규칙 기반 vs AI 판단**의 차이입니다.

| 구분 | LLM 라우팅 | 패턴 라우팅 |
|------|-----------|-----------|
| **방식** | AI가 질문 읽고 판단 | 키워드 규칙으로 판단 |
| **속도** | 1-3초 (느림) | 0.001초 (빠름) |
| **비용** | API 호출 비용 발생 | 비용 없음 |
| **일관성** | 같은 질문도 다른 답변 가능 | 항상 같은 결과 |
| **유연성** | 새로운 질문 대응 가능 | 사전 정의된 패턴만 |

**실생활 비유**:
- **LLM 라우팅**: 사람한테 물어보기 ("이거 어디 있어요?" → 생각 후 답변)
- **패턴 라우팅**: 안내판 보고 찾기 (화살표 따라가기)

---

### Q1-3. 왜 패턴 라우팅을 사용하나요?

**A:** **빠르고, 정확하고, 비용이 들지 않기 때문**입니다.

**장점**:
1. ⚡ **초고속**: LLM 호출 없이 즉시 판단
2. 💯 **100% 일관성**: 같은 질문 → 같은 도구
3. 💰 **비용 절감**: API 호출 안 함
4. 🔄 **파이프라인 지원**: 여러 도구 순차 실행
5. 🎯 **정확도**: 명확한 패턴은 LLM보다 정확

**실제 사례**:
```
질문: "GPT 논문 요약해줘"

LLM 라우팅:
  - 시간: 2.3초
  - 비용: API 호출 1회
  - 결과: search_paper (요약 도구 누락 가능)

패턴 라우팅:
  - 시간: 0.001초
  - 비용: 0원
  - 결과: [search_paper, web_search, general, summarize] (완벽한 파이프라인)
```

---

## 2. 패턴 파일 이해하기

### Q2-1. 패턴 파일은 어디에 있나요?

**A:** `configs/multi_request_patterns.yaml` 파일입니다.

**파일 위치**:
```
프로젝트/
├── configs/
│   └── multi_request_patterns.yaml  ← 여기!
```

**내용 예시**:
```yaml
patterns:
  - keywords:
      - 논문
      - 요약
    tools:
      - search_paper
      - summarize
```

---

### Q2-2. YAML 파일이 뭔가요? 어렵나요?

**A:** YAML은 **설정 파일 형식**입니다. **들여쓰기로 구조를 표현**하는 간단한 형식입니다.

**비유**: 엑셀처럼 데이터를 정리하는 방법 중 하나

**기본 문법**:
```yaml
# 주석 (설명)
키: 값

# 리스트
과일:
  - 사과
  - 바나나
  - 포도

# 딕셔너리 (키-값 쌍)
학생:
  이름: 홍길동
  나이: 20
  전공: 컴퓨터공학
```

**주의사항**:
- ❌ 탭(Tab) 사용 금지 → ✅ 스페이스 2칸 사용
- ❌ 들여쓰기 틀리면 오류 발생

---

### Q2-3. 패턴 하나는 어떻게 생겼나요?

**A:** **5가지 필드**로 구성됩니다.

```yaml
- keywords:              # ① 필수 키워드 (모두 포함되어야 함)
    - 논문
    - 요약
  exclude_keywords:      # ② 제외 키워드 (하나라도 있으면 제외)
    - 저장
  tools:                 # ③ 실행할 도구 목록 (순서대로)
    - search_paper
    - summarize
  description: 논문 요약  # ④ 설명 (문서화용)
  priority: 120          # ⑤ 우선순위 (높을수록 먼저 확인)
  examples:              # ⑥ 예시 (문서화용)
    - Transformer 논문 요약해줘
```

**필드 설명**:

| 필드 | 필수? | 설명 | 예시 |
|------|-------|------|------|
| `keywords` | ✅ 필수 | 모두 포함되어야 매칭 | `["논문", "요약"]` |
| `exclude_keywords` | ❌ 선택 | 하나라도 있으면 제외 | `["저장"]` |
| `tools` | ✅ 필수 | 실행할 도구 (1~6개) | `[search_paper, summarize]` |
| `priority` | ❌ 선택 | 우선순위 (기본값: 0) | `120` |
| `description` | ❌ 선택 | 패턴 설명 | `"논문 요약"` |
| `examples` | ❌ 선택 | 예시 질문 | `["GPT 논문 요약"]` |

---

### Q2-4. 현재 몇 개의 패턴이 있나요?

**A:** **총 17개 패턴**이 있으며, 4가지 카테고리로 분류됩니다.

**카테고리별 분류**:

| 카테고리 | 개수 | 우선순위 | 예시 |
|---------|------|---------|------|
| **단일 도구** | 4개 | 150-200 | "뭐야?" → glossary |
| **2-도구 파이프라인** | 6개 | 100-140 | "논문 요약" → [search, summarize] |
| **5-도구 파이프라인** | 1개 | 100 | "논문 요약 저장" |
| **6-도구 파이프라인** | 6개 | 75-80 | "통계 논문 요약 저장" |

**패턴 목록 예시**:
```
1. "뭐야" → glossary (Priority 200)
2. "뭔지" → glossary (Priority 200)
3. "전체 저장" → save_file (Priority 150)
4. "논문 찾" → search_paper (Priority 140)
5. "논문 요약" → [search_paper, web_search, general, summarize] (Priority 120)
...
```

---

## 3. 패턴 매칭 동작 방식

### Q3-1. 패턴 매칭은 어떻게 작동하나요?

**A:** **3단계로 동작**합니다.

```
1단계: 패턴 파일 로드
  ↓
2단계: 질문에서 키워드 찾기
  ↓
3단계: 첫 번째 매칭 패턴 선택
```

**상세 흐름**:
```python
# 1단계: YAML 파일 로드 (우선순위 정렬됨)
patterns = load_patterns()  # 17개, Priority 내림차순

# 2단계: 패턴 순회
for pattern in patterns:  # 우선순위 높은 순서
    keywords = pattern["keywords"]
    exclude_keywords = pattern.get("exclude_keywords", [])

    # 모든 키워드 포함?
    if all(kw in question for kw in keywords):
        # 제외 키워드 있음?
        if not any(ex_kw in question for ex_kw in exclude_keywords):
            # 매칭 성공! ✅
            return pattern["tools"]

# 3단계: 매칭 실패 → LLM 라우팅
return llm_routing(question)
```

---

### Q3-2. "모든 키워드가 포함"이란 무엇인가요?

**A:** `keywords` 리스트의 **모든 단어가 질문에 있어야** 매칭됩니다.

**예시 1: 성공**
```yaml
keywords: ["논문", "요약"]
질문: "Transformer 논문 요약해줘"
     ↓
체크: "논문" 포함? ✅
      "요약" 포함? ✅
     ↓
결과: 매칭 성공!
```

**예시 2: 실패**
```yaml
keywords: ["논문", "요약"]
질문: "Transformer 논문 찾아줘"
     ↓
체크: "논문" 포함? ✅
      "요약" 포함? ❌ (없음!)
     ↓
결과: 매칭 실패
```

**코드로 보면**:
```python
keywords = ["논문", "요약"]
question = "Transformer 논문 요약해줘"

# all() 함수: 모든 조건이 True여야 True 반환
result = all(kw in question for kw in keywords)
# → ("논문" in question) and ("요약" in question)
# → True and True
# → True ✅
```

---

### Q3-3. 여러 패턴이 매칭되면 어떻게 되나요?

**A:** **우선순위가 가장 높은 첫 번째 패턴**이 선택됩니다.

**예시 상황**:
```
질문: "논문 요약해줘"

패턴 A: keywords=["논문", "요약"], priority=120
패턴 B: keywords=["논문"], priority=100
패턴 C: keywords=["요약"], priority=90

매칭 결과:
  - 패턴 A: ✅ 매칭 (priority 120)
  - 패턴 B: ✅ 매칭 (priority 100)
  - 패턴 C: ✅ 매칭 (priority 90)

선택: 패턴 A (우선순위 가장 높음)
```

**동작 순서**:
```python
# 1. 패턴을 priority 내림차순 정렬
patterns_sorted = sorted(patterns, key=lambda p: p["priority"], reverse=True)
# [패턴 A(120), 패턴 B(100), 패턴 C(90)]

# 2. 순서대로 확인하다가 첫 매칭 반환
for pattern in patterns_sorted:
    if matches(pattern, question):
        return pattern  # 첫 번째 매칭만 선택!
```

---

### Q3-4. 매칭 속도는 얼마나 빠른가요?

**A:** **0.001초 미만**입니다. (1밀리초 이하)

**비교**:
```
패턴 매칭: 0.0005초 (0.5ms)
LLM 라우팅: 2.3초 (2300ms)

→ 약 4600배 빠름! ⚡
```

**왜 빠른가요?**:
- 단순 문자열 검색만 수행
- LLM 호출 없음
- 네트워크 통신 없음

**복잡도**:
```
패턴 수: N = 17개
키워드 수: K = 평균 2개

시간 복잡도: O(N * K) = O(17 * 2) = O(34)
실제 실행 시간: < 1ms
```

---

## 4. 패턴 추가/수정하기

### Q4-1. 새로운 패턴을 추가하려면 어떻게 하나요?

**A:** **YAML 파일에 새 패턴 블록을 추가**하면 됩니다.

**단계별 가이드**:

**1단계: 요구사항 분석**
```
사용자 요청: "BERT 설명하고 관련 논문도 찾아줘"

분석:
  - 키워드: "설명", "논문", "찾"
  - 도구: glossary (설명) → search_paper (논문 검색)
  - 우선순위: 100 (2-도구 파이프라인)
```

**2단계: YAML 작성**
```yaml
- keywords:
    - 설명
    - 논문
    - 찾
  exclude_keywords:
    - 저장
    - 요약
  tools:
    - glossary
    - search_paper
  description: 용어 설명 후 관련 논문 검색
  priority: 100
  examples:
    - BERT 설명하고 관련 논문도 찾아줘
    - Transformer 설명하고 논문 검색해줘
```

**3단계: 파일에 추가**
```yaml
# multi_request_patterns.yaml

patterns:
  # ... 기존 패턴들 ...

  # ==================== 새 패턴 추가 ==================== #
  - keywords:
      - 설명
      - 논문
      - 찾
    # ... (위 내용 붙여넣기)
```

**4단계: 메타데이터 업데이트**
```yaml
metadata:
  version: '3.3'                  # 버전 증가
  total_patterns: 18              # 17 → 18
  pattern_breakdown:
    two_tool: 7                   # 6 → 7
```

---

### Q4-2. 기존 패턴을 수정하려면?

**A:** YAML 파일에서 **해당 패턴을 찾아서 수정**하면 됩니다.

**예시: 키워드 추가**

**변경 전**:
```yaml
- keywords:
    - 논문
    - 요약
  tools:
    - search_paper
    - summarize
```

**변경 후** ("정리"도 요약으로 인식):
```yaml
- keywords:
    - 논문
    - 요약
  tools:
    - search_paper
    - summarize

# 또는 새 패턴 추가
- keywords:
    - 논문
    - 정리        # "정리"도 요약 의미
  tools:
    - search_paper
    - summarize
  priority: 120
```

---

### Q4-3. 패턴을 삭제하려면?

**A:** YAML 파일에서 **해당 패턴 블록 전체를 삭제**하면 됩니다.

**삭제 대상 찾기**:
```yaml
# 삭제할 패턴
- keywords:
    - 웹
    - 검색
  tools:
    - web_search
  priority: 80

# 아래 패턴부터 유지
- keywords:
    - 최신
    - 정보
  # ...
```

**삭제 방법**:
1. 해당 패턴 전체 선택 (`- keywords:`부터 다음 `-` 전까지)
2. Delete 키 누르기
3. 저장

**주의**: 메타데이터도 업데이트!
```yaml
metadata:
  total_patterns: 16  # 17 → 16 (1개 삭제)
```

---

### Q4-4. 패턴 추가 후 테스트는 어떻게 하나요?

**A:** **Streamlit UI에서 직접 질문해보면** 됩니다.

**테스트 절차**:

1. **파일 저장 확인**
   ```bash
   # YAML 문법 검사
   python -c "import yaml; yaml.safe_load(open('configs/multi_request_patterns.yaml'))"
   ```

2. **서버 재시작**
   ```bash
   # Streamlit 재시작 (변경사항 반영)
   streamlit run ui/main.py
   ```

3. **테스트 질문 입력**
   ```
   UI에서 질문: "BERT 설명하고 관련 논문도 찾아줘"
   ```

4. **로그 확인**
   ```
   실행 과정 확인:
   - "다중 요청 감지: ['설명', '논문', '찾']" ← 패턴 매칭 성공!
   - "순차 실행 도구: glossary → search_paper"
   ```

---

## 5. 우선순위와 충돌

### Q5-1. 우선순위(priority)는 무엇인가요?

**A:** 여러 패턴이 매칭될 때 **어떤 패턴을 먼저 선택할지** 결정하는 숫자입니다.

**원칙**:
- 숫자가 **높을수록** 우선순위 **높음**
- 우선순위 높은 패턴부터 확인
- 첫 번째 매칭 패턴 선택

**우선순위 범위**:
```
200번대: 최우선 (단순 요청)
  └─ 예: "뭐야?" → glossary

100-150번대: 중간 우선순위 (복합 요청)
  └─ 예: "논문 요약" → [search_paper, summarize]

70-90번대: 낮은 우선순위 (복잡한 파이프라인)
  └─ 예: "통계 논문 요약 저장" → [text2sql, search, summarize, save]
```

---

### Q5-2. 왜 우선순위가 필요한가요?

**A:** **포함 관계 패턴의 충돌**을 해결하기 위함입니다.

**문제 상황**:
```yaml
# 패턴 A: 구체적 (3개 키워드)
keywords: ["논문", "요약", "저장"]
tools: [search_paper, summarize, save_file]

# 패턴 B: 일반적 (2개 키워드)
keywords: ["논문", "요약"]
tools: [search_paper, summarize]
```

**질문**: "논문 요약해서 저장해줘"

**충돌**:
- 패턴 A 매칭: ✅ ("논문", "요약", "저장" 모두 포함)
- 패턴 B 매칭: ✅ ("논문", "요약" 포함)

**해결**: 우선순위로 선택
```yaml
# 방법 1: 구체적 패턴에 높은 우선순위
패턴 A: priority=100  # 선택됨 ✅
패턴 B: priority=120

# 방법 2: 순서 조정 (위에 있는 것 우선)
patterns:
  - keywords: ["논문", "요약", "저장"]  # 먼저 확인
  - keywords: ["논문", "요약"]         # 나중 확인
```

---

### Q5-3. 우선순위를 어떻게 정해야 하나요?

**A:** **키워드 개수와 복잡도**를 고려합니다.

**우선순위 결정 기준**:

| 키워드 개수 | 도구 개수 | 추천 Priority | 예시 |
|-----------|---------|-------------|------|
| 1개 | 1개 | 150-200 | "뭐야?" |
| 2개 | 1-2개 | 120-150 | "논문 찾" |
| 2-3개 | 2-4개 | 100-120 | "논문 요약" |
| 3-4개 | 4-5개 | 80-100 | "논문 요약 저장" |
| 4개 이상 | 5-6개 | 70-80 | "통계 논문 요약 저장" |

**원칙**:
1. **구체적 패턴 → 높은 우선순위**
2. **단순 패턴 → 높은 우선순위**
3. **자주 사용 → 높은 우선순위**

---

### Q5-4. 우선순위 충돌 디버깅 방법은?

**A:** **로그를 확인**하면 어떤 패턴이 매칭되었는지 알 수 있습니다.

**로그 예시**:
```
질문: "논문 요약해서 저장해줘"

로그:
  - 패턴 매칭 시도: keywords=['논문', '요약', '저장']
  - 키워드 매칭: True
  - 제외 키워드 매칭: False
  - 다중 요청 감지: ['논문', '요약', '저장'] → [search_paper, summarize, save_file]
  - 패턴 설명: 논문 요약 저장
```

**확인 사항**:
- "다중 요청 감지" 메시지 확인
- 예상과 다르면 우선순위 조정

---

## 6. Exclude Keywords

### Q6-1. exclude_keywords는 왜 필요한가요?

**A:** **오매칭을 방지**하기 위함입니다.

**문제 상황**:
```yaml
# 패턴: 용어 정의
keywords: ["뭔지"]
tools: [glossary]
```

**오매칭 발생**:
```
질문: "AI가 뭔지 찾아서 저장해줘"
     ↓
매칭: ✅ "뭔지" 포함
     ↓
실행: glossary만 실행 ❌
기대: glossary → save_file
```

**해결**: exclude_keywords 추가
```yaml
keywords: ["뭔지"]
exclude_keywords: ["논문", "찾아"]  # ✅ 논문 검색 제외
tools: [glossary]
```

**결과**:
```
질문: "AI가 뭔지 찾아서 저장해줘"
     ↓
매칭: "뭔지" 포함 ✅
      "찾아" 포함 ❌ (exclude에 있음!)
     ↓
결과: 매칭 실패 → 다른 패턴 확인
```

---

### Q6-2. exclude_keywords는 어떻게 작동하나요?

**A:** **하나라도 있으면 패턴 제외**합니다.

**로직**:
```python
exclude_keywords = ["논문", "검색", "찾아"]
question = "AI가 뭔지 찾아서 저장해줘"

# any() 함수: 하나라도 True면 True 반환
exclude_match = any(ex_kw in question for ex_kw in exclude_keywords)
# → ("논문" in question) or ("검색" in question) or ("찾아" in question)
# → False or False or True
# → True ❌ (매칭 제외!)
```

**비교**:
- `keywords`: **모두** 있어야 매칭 (AND 조건)
- `exclude_keywords`: **하나라도** 있으면 제외 (OR 조건)

---

### Q6-3. exclude_keywords 설정 가이드는?

**A:** **오매칭이 발생하는 키워드**를 추가합니다.

**가이드**:

**Step 1: 오매칭 발견**
```
패턴: keywords=["뭐야"]
질문: "GPT 논문이 뭐야?"
실행: glossary만 실행 ❌
기대: 논문 검색도 필요
```

**Step 2: 원인 분석**
```
"논문"이 있으면 search_paper도 필요한데
"뭐야" 패턴에만 매칭됨
```

**Step 3: exclude 추가**
```yaml
keywords: ["뭐야"]
exclude_keywords: ["논문"]  # ✅ 논문 관련은 제외
tools: [glossary]
```

**Step 4: 별도 패턴 추가**
```yaml
# 논문 + 뭐야 패턴
keywords: ["논문", "뭐야"]
tools: [search_paper, general]
priority: 110  # "뭐야"보다 높은 우선순위
```

---

### Q6-4. exclude_keywords 실전 예시

**A:** 현재 사용 중인 **실제 패턴**들입니다.

**예시 1: 용어 정의 패턴**
```yaml
# "뭐야" 패턴
keywords: ["뭐야"]
exclude_keywords: ["논문", "검색", "찾아"]
tools: [glossary]
priority: 200

# 이유: "논문 찾아서 뭐야"같은 복합 요청 제외
```

**예시 2: 논문 요약 패턴**
```yaml
keywords: ["논문", "요약"]
exclude_keywords: ["저장"]
tools: [search_paper, web_search, general, summarize]
priority: 120

# 이유: "저장"이 있으면 save_file도 필요
```

**예시 3: 통계 패턴**
```yaml
keywords: ["통계", "논문"]
exclude_keywords: ["저장", "요약"]
tools: [text2sql, search_paper]
priority: 110

# 이유: "요약", "저장"이 있으면 더 복잡한 파이프라인 필요
```

---

## 7. Multi-turn 대응

### Q7-1. Multi-turn이란 무엇인가요?

**A:** **이전 대화를 참고하는 연속 대화**를 의미합니다.

**예시**:
```
사용자 1: "Transformer가 뭐야?"
AI 1: "Transformer는 Attention 메커니즘을 사용한 모델입니다..."

사용자 2: "관련 논문 찾아줘"  ← Multi-turn!
         ↑
"관련"이 Transformer를 가리킴 (이전 대화 참조)
```

---

### Q7-2. 패턴 매칭과 Multi-turn의 충돌은?

**A:** **맥락 참조 표현이 있으면 패턴 매칭을 건너뛰고 LLM 라우팅을 사용**합니다.

**문제 상황**:
```
사용자 2: "관련 논문 찾아줘"
         ↓
패턴 매칭: "논문", "찾" → search_paper
         ↓
문제: "관련"이 무엇인지 모름! (Transformer를 모름)
```

**해결**:
```python
# 맥락 참조 키워드
contextual_keywords = [
    "관련", "그거", "이거", "저거", "해당",
    "방금", "위", "앞서", "이전", "그"
]

# 맥락 참조 감지
if "관련" in question:
    # 패턴 매칭 건너뛰기
    # LLM 라우팅 (이전 대화 컨텍스트 포함)
```

---

### Q7-3. 명확한 다중 요청은 어떻게 처리하나요?

**A:** **맥락 참조가 있어도 "저장", "요약" 같은 명확한 키워드가 있으면 패턴 매칭을 시도**합니다.

**예시**:
```
사용자 2: "관련 논문 요약해서 저장해줘"
         ↓
분석: "관련" (맥락 참조) + "요약", "저장" (명확한 다중 요청)
     ↓
처리: 패턴 매칭 시도 ✅
     ↓
매칭: ["논문", "요약", "저장"] 패턴
     ↓
실행: [search_paper, summarize, save_file]
```

**코드**:
```python
# 명확한 다중 요청 지시어
multi_request_indicators = ["저장", "요약", "정리"]

# "관련"이 있어도 "저장"이 명확하면 패턴 시도
if "관련" in question and "저장" in question:
    # 패턴 매칭 시도 ✅
```

---

## 8. 트러블슈팅

### Q8-1. 패턴이 매칭되지 않아요!

**A:** **로그를 확인**하고 키워드를 점검합니다.

**체크리스트**:

1. **키워드 철자 확인**
   ```yaml
   # 오타 있음?
   keywords: ["놈문", "요약"]  # ❌ "논문" 아님!
   ```

2. **질문에 모든 키워드 포함되었는지 확인**
   ```
   패턴: keywords=["논문", "요약"]
   질문: "논문 찾아줘"
        ↓
   체크: "논문" ✅, "요약" ❌
        ↓
   결과: 매칭 실패
   ```

3. **exclude_keywords 확인**
   ```yaml
   keywords: ["논문"]
   exclude_keywords: ["저장"]

   질문: "논문 저장해줘"
        ↓
   결과: 매칭 제외 (exclude 때문에)
   ```

4. **우선순위 확인**
   ```
   더 높은 우선순위 패턴이 먼저 매칭되었을 수 있음
   ```

---

### Q8-2. 잘못된 도구가 실행돼요!

**A:** **exclude_keywords를 추가**하거나 **새 패턴을 만듭니다**.

**Case 1: 오매칭 발생**
```
질문: "AI가 뭔지 찾아서 저장해줘"
실행: search_paper (❌ glossary가 먼저 실행되어야 함)
```

**해결 1**: exclude_keywords 추가
```yaml
keywords: ["뭔지"]
exclude_keywords: ["찾아", "논문"]  # ✅
tools: [glossary]
```

**해결 2**: 새 패턴 추가
```yaml
keywords: ["뭔지", "저장"]
tools: [glossary, save_file]
priority: 140  # "뭔지"보다 높은 우선순위
```

---

### Q8-3. YAML 파일 수정 후 반영이 안 돼요!

**A:** **서버를 재시작**해야 합니다.

**원인**: 캐싱
```python
# config_loader.py
_multi_request_patterns_cache = None  # 캐시 변수

# 첫 로드 시 캐시 저장
if _multi_request_patterns_cache is not None:
    return _multi_request_patterns_cache  # 캐시 반환 (파일 재로드 안 함)
```

**해결 방법**:

**방법 1: 서버 재시작** (권장)
```bash
# Ctrl+C로 중지
# 다시 시작
streamlit run ui/main.py
```

**방법 2: 강제 재로드 코드** (개발용)
```python
from src.agent.config_loader import reload_config
reload_config()  # 캐시 무효화
```

---

### Q8-4. YAML 파일에 오류가 있어요!

**A:** **들여쓰기나 문법을 확인**합니다.

**흔한 오류**:

**오류 1: 탭(Tab) 사용**
```yaml
# ❌ 잘못됨
keywords:
	- 논문  # 탭 사용

# ✅ 올바름
keywords:
  - 논문  # 스페이스 2칸
```

**오류 2: 들여쓰기 불일치**
```yaml
# ❌ 잘못됨
keywords:
  - 논문
   - 요약  # 들여쓰기 1칸

# ✅ 올바름
keywords:
  - 논문
  - 요약  # 들여쓰기 2칸
```

**오류 3: 콜론(:) 뒤 공백 없음**
```yaml
# ❌ 잘못됨
keywords:["논문"]

# ✅ 올바름
keywords: ["논문"]
```

**검증 방법**:
```bash
# YAML 문법 검사
python -c "import yaml; yaml.safe_load(open('configs/multi_request_patterns.yaml'))"

# 오류 없으면 아무것도 출력 안 됨
# 오류 있으면 에러 메시지 출력
```

---

## 9. 실전 예제

### Q9-1. "GPT 논문 요약해줘" 처리 과정은?

**A:** **4단계 파이프라인**으로 처리됩니다.

**전체 흐름**:
```
입력: "GPT 논문 요약해줘"
  ↓
1. Router: 패턴 매칭
  - keywords: ["논문", "요약"] ✅
  - tools: [search_paper, web_search, general, summarize]
  ↓
2. search_paper: RAG 논문 검색
  - 결과: GPT 관련 논문 찾음
  - tool_result 저장
  ↓
3. web_search: 웹 검색 (실패 시)
  - search_paper 성공 시 건너뛸 수 있음
  ↓
4. general: LLM이 논문 내용 확인
  - tool_result 업데이트
  ↓
5. summarize: 논문 요약
  - tool_result를 요약
  - 최종 답변 생성
```

**매칭 패턴**:
```yaml
keywords: ["논문", "요약"]
exclude_keywords: ["저장"]
tools: [search_paper, web_search, general, summarize]
priority: 120
```

---

### Q9-2. "AI가 뭔지 찾아서 저장해줘" 처리는?

**A:** **2단계 파이프라인** (glossary → save_file)로 처리됩니다.

**흐름**:
```
입력: "AI가 뭔지 찾아서 저장해줘"
  ↓
1. Router: 패턴 매칭
  - keywords: ["뭔지", "저장"] ✅
  - exclude: ["논문"] (질문에 없음)
  - tools: [glossary, save_file]
  ↓
2. glossary: 용어 정의 검색
  - "AI" 용어 검색
  - tool_result: "AI는 인공지능..."
  ↓
3. save_file: 파일 저장
  - tool_result를 파일로 저장
  - 파일명: 20251105_123456_response_1.md
```

**매칭 패턴**:
```yaml
keywords: ["뭔지", "저장"]
exclude_keywords: ["전체", "논문"]
tools: [glossary, save_file]
priority: 140
```

---

### Q9-3. "Transformer가 뭐야?" 처리는?

**A:** **단일 도구** (glossary만) 실행됩니다.

**흐름**:
```
입력: "Transformer가 뭐야?"
  ↓
1. Router: 패턴 매칭
  - keywords: ["뭐야"] ✅
  - exclude: ["논문", "검색", "찾아"] (질문에 없음)
  - tools: [glossary]
  ↓
2. glossary: 용어 정의 검색
  - "Transformer" 용어 검색
  - 최종 답변: "Transformer는 Attention 메커니즘..."
```

**매칭 패턴**:
```yaml
keywords: ["뭐야"]
exclude_keywords: ["논문", "검색", "찾아"]
tools: [glossary]
priority: 200  # 최우선!
```

---

### Q9-4. "관련 논문 찾아줘" (Multi-turn) 처리는?

**A:** **LLM 라우팅**으로 처리됩니다 (패턴 매칭 건너뛰기).

**이전 대화**:
```
사용자 1: "Transformer가 뭐야?"
AI 1: "Transformer는..."
```

**현재 요청 처리**:
```
입력: "관련 논문 찾아줘"
  ↓
1. Router: 맥락 참조 감지
  - "관련" 키워드 포함 ✅
  - 이전 대화 있음 ✅
  - 패턴 매칭 건너뛰기
  ↓
2. LLM 라우팅 (이전 대화 포함)
  - 이전 대화: "Transformer가 뭐야?"
  - 현재 질문: "관련 논문 찾아줘"
  - LLM 판단: "Transformer 논문 검색"
  - tools: [search_paper]
  ↓
3. search_paper: Transformer 논문 검색
  - 최종 답변 생성
```

**왜 패턴 매칭 안 하나요?**
- "관련"이 무엇을 가리키는지 패턴으로는 알 수 없음
- LLM이 이전 대화를 보고 판단해야 함

---

## 📝 요약

### 핵심 포인트

1. **패턴 라우팅 = 키워드 기반 규칙**
   - 빠르고, 정확하고, 비용 없음

2. **YAML 파일로 관리**
   - 코드 수정 없이 패턴 추가/수정
   - 17개 패턴, 4가지 카테고리

3. **우선순위 중요**
   - 높은 숫자 = 먼저 확인
   - 구체적 패턴 = 높은 우선순위

4. **exclude_keywords로 오매칭 방지**
   - 하나라도 있으면 제외

5. **Multi-turn 자동 대응**
   - 맥락 참조 → 패턴 건너뛰기 → LLM 라우팅

### 패턴 추가 체크리스트

- [ ] keywords 2글자 이상?
- [ ] exclude_keywords 필요?
- [ ] 우선순위 적절?
- [ ] 기존 패턴 충돌 확인?
- [ ] examples 추가?
- [ ] 메타데이터 업데이트?
- [ ] 서버 재시작?

### 도움이 더 필요하면?

- 📖 상세 문서: `docs/modularization/06-2_패턴_기반_도구_라우팅.md`
- 💬 질문: 팀장(최현화)에게 문의
- 🐛 버그 발견: Issue 등록

---

**작성자**: 최현화[팀장]
**작성일**: 2025-11-05
**버전**: 1.0
