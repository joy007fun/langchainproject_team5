# 용어집 시스템 Q&A

## 문서 정보
- **작성일**: 2025-11-04
- **작성자**: 최현화[팀장]
- **목적**: 용어집 시스템 관련 자주 묻는 질문 및 답변

---

## 목차
1. [기본 개념](#1-기본-개념)
2. [용어 추출 및 저장](#2-용어-추출-및-저장)
3. [용어집 검색](#3-용어집-검색)
4. [데이터베이스](#4-데이터베이스)
5. [도구별 동작](#5-도구별-동작)
6. [트러블슈팅](#6-트러블슈팅)
7. [최적화 및 성능](#7-최적화-및-성능)

---

## 1. 기본 개념

### Q1-1. 용어집 시스템이 뭔가요?

**A:** 용어집 시스템은 **AI/ML 관련 전문 용어를 자동으로 추출하여 저장하고, 사용자가 질문할 때 용어 정의를 제공하는 시스템**입니다.

**두 가지 핵심 기능:**
1. **용어 자동 추출**: 다른 도구의 LLM 답변에서 AI/ML 용어를 추출하여 glossary 테이블에 저장
2. **용어 검색**: 사용자가 "Attention이 뭐야?" 같은 질문을 하면 glossary 테이블에서 검색하여 답변

---

### Q1-2. 용어집 검색 도구와 용어 자동 추출은 다른 건가요?

**A:** 네, 완전히 다른 기능입니다.

| 구분 | 용어집 검색 도구 | 용어 자동 추출 |
|------|----------------|---------------|
| **목적** | 사용자 질문에 용어 정의 답변 | 답변에서 용어를 자동으로 DB에 저장 |
| **실행 시점** | 사용자가 용어 질문할 때 | 다른 도구가 답변 생성한 후 |
| **파일** | `src/tools/glossary.py` | `src/utils/glossary_extractor.py` |
| **호출 위치** | Agent 라우팅 | Streamlit UI (`chat_interface.py`) |
| **DB 연동** | glossary 테이블 읽기 | glossary 테이블 쓰기 |

**예시:**
- **용어집 검색 도구**: "Attention이 뭐야?" → glossary 테이블 검색 → 정의 반환
- **용어 자동 추출**: "GAN 설명해줘" → 일반 답변 도구가 설명 생성 → 답변에서 "GAN", "Generator", "Discriminator" 추출 → glossary 저장

---

### Q1-3. 왜 용어를 자동으로 저장하나요?

**A:** 다음과 같은 이점이 있습니다:

1. **용어집 DB 자동 확장**: 사용자 질문에 답변하면서 자연스럽게 용어집이 확장됨
2. **향후 활용**: 저장된 용어는 나중에 다른 사용자가 질문할 때 바로 답변 가능
3. **일관성**: 동일한 용어에 대해 일관된 정의 제공
4. **시간 절약**: 매번 LLM에게 용어 정의를 물어볼 필요 없음

---

### Q1-4. 용어 자동 추출도 도구인가요?

**A:** **아니오, 용어 자동 추출은 도구가 아닙니다.**

**도구 vs 유틸리티:**

| 구분 | 도구 (Tools) | 용어 자동 추출 |
|------|------------|---------------|
| **위치** | `src/tools/` | `src/utils/glossary_extractor.py` |
| **역할** | Agent가 선택하여 실행 | 도구 실행 후 자동 실행 |
| **실행 주체** | Agent (Router 선택) | Streamlit UI |
| **사용자 인지** | 사용자가 의도적으로 요청 | 백그라운드에서 자동 실행 |
| **LangGraph 통합** | ✅ Agent 노드로 등록됨 | ❌ 통합 안 됨 |

**7가지 도구:**
1. `general_answer` - 일반 답변
2. `search_paper` - RAG 검색
3. `web_search` - 웹 검색
4. `glossary` - 용어집 검색 ← **이것이 도구**
5. `summarize` - 논문 요약
6. `text2sql` - Text-to-SQL
7. `save_file` - 파일 저장

**용어 자동 추출은:**
- **유틸리티 함수**: 도구가 아닌 보조 기능
- **자동 실행**: 사용자가 요청하지 않아도 백그라운드에서 실행
- **UI 레벨 처리**: `ui/components/chat_interface.py`에서 호출

**예시:**
```
사용자: "GAN 설명해줘"
    ↓
Agent: general_answer 도구 선택 (7가지 도구 중 선택)
    ↓
general_answer 도구 실행: "GAN은 Generator와 Discriminator..."
    ↓
UI: 답변 표시
    ↓
UI: 용어 자동 추출 실행 (자동, 백그라운드) ← 도구가 아님
    ↓
glossary_extractor.py: "GAN", "Generator", "Discriminator" 추출
    ↓
DB 저장
```

**핵심:**
- **glossary 도구**: 사용자가 "Attention이 뭐야?"라고 질문 → Agent가 선택
- **용어 자동 추출**: 어떤 도구든 답변 생성 후 → UI가 자동 실행

---

## 2. 용어 추출 및 저장

### Q2-1. 어떤 도구에서 용어가 추출되나요?

**A:** **5개 도구**에서만 용어가 추출됩니다 (화이트리스트 방식):

| 도구 | 추출 여부 | 이유 |
|------|----------|------|
| `general_answer` | ✅ | AI/ML 개념 설명 가능성 높음 |
| `search_paper` | ✅ | 논문 설명에 전문 용어 다수 포함 |
| `web_search` | ✅ | 최신 AI/ML 용어 포함 가능 |
| `glossary` | ✅ | 용어 정의 답변 자체가 용어 |
| `summarize` | ✅ | 논문 요약에 전문 용어 포함 |
| **`text2sql`** | ❌ | SQL 쿼리와 통계 결과만 (용어 없음) |
| **`save_file`** | ❌ | 파일 저장 완료 메시지만 (용어 없음) |

---

### Q2-2. text2sql과 save_file에서는 왜 용어 추출을 안 하나요?

**A:** **답변에 AI/ML 용어가 전혀 없기 때문**입니다.

**text2sql 답변 예시:**
```markdown
**질문**: 2024년에 발표된 논문 개수는?

**생성된 SQL**:
```sql
SELECT COUNT(*) AS paper_count FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
```

**결과**:

paper_count
---
42
---

→ AI/ML 용어가 하나도 없음 (SQL 구문과 숫자만)

**save_file 답변 예시:**
---
파일 저장이 완료되었습니다.
경로: experiments/20251104/20251104_103015_session_001/outputs/response.txt
---

→ 역시 AI/ML 용어 없음

**불필요한 LLM 호출 방지:**
- 용어 추출을 위해 LLM을 호출하면 비용 발생
- text2sql, save_file은 용어가 없으므로 호출해도 빈 리스트만 반환
- 따라서 아예 호출하지 않아 비용 절감

---

### Q2-3. 용어는 몇 개까지 추출되나요?

**A:** **사용자가 설정한 범위만큼** 추출됩니다.

**기본값:**
- 최소 1개 ~ 최대 5개 (기본 설정)
- Streamlit UI 사이드바에서 사용자가 직접 조정 가능

**설정 방법:**
1. **사이드바 → "📖 용어 추출 설정" 섹션**
2. **슬라이더**: 드래그앤드롭으로 1~100 범위 선택
3. **텍스트 입력**: 최소/최대 개수 수동 입력
4. **양방향 동기화**: 슬라이더 ↔ 텍스트 입력 자동 업데이트

**중요 조건:**
1. **IT 용어만 저장**: AI/ML/NLP/CV/RL 등 IT 관련 용어만 추출
2. **품질 우선**: 정확성/유사도 높은 순으로 우선순위 정렬
3. **무작위 단어 금지**: 최소 개수 미달 시 실제 추출된 개수만 저장
   - 예: 설정 5-15개, 실제 IT 용어 3개 → 3개만 저장

**예시:**

**시나리오 1: 기본 설정 (1-5개)**
- 답변: "GAN은 Generator와 Discriminator로 구성됩니다."
- 추출: 3개 (GAN, Generator, Discriminator)
- 결과: 1 ≤ 3 ≤ 5 → **3개 저장**

**시나리오 2: 많은 용어 설정 (10-30개)**
- 답변: "Transformer는 Self-Attention, Multi-Head Attention, FFN, Layer Norm, Residual Connection, Positional Encoding, Encoder, Decoder 등으로 구성됩니다."
- 추출: 20개 IT 용어
- 결과: 10 ≤ 20 ≤ 30 → **20개 저장**

**시나리오 3: 용어 부족 (5-15개 설정, 3개만 추출)**
- 답변: "BERT는 양방향 학습을 수행합니다."
- 추출: 3개 (BERT, 양방향 학습, Transformer)
- IT 필터링: 2개 (BERT, Transformer만 IT 용어)
- 결과: 2 < 5(min) → **2개만 저장** (무작위 단어 추가 안 함)

---

### Q2-4. 용어 추출은 누가 하나요?

**A:** **답변 생성에 사용된 것과 동일한 난이도별 LLM**이 자동으로 추출합니다.

**사용 모델 설정:**
- 용어 추출 LLM은 `LLMClient.from_difficulty()`를 통해 **답변 생성과 동일한 모델** 사용
- Easy 모드: Solar Pro2
- Hard 모드: GPT-5
- 이유: 답변 생성에 사용된 모델이 해당 난이도에 맞는 용어 정의를 생성하는 데 더 적합

**왜 동일한 LLM을 사용하나요?**

| 항목 | 답변 생성 LLM | 용어 추출 LLM |
|------|-------------|--------------|
| **모델** | GPT-5 또는 Solar Pro2 (난이도별) | **동일 모델 사용** |
| **역할** | 사용자 질문에 답변 | 답변에서 AI/ML 용어 추출 |
| **설명 수준** | Easy/Hard 모드에 적합 | 동일한 난이도로 용어 설명 생성 |
| **일관성** | - | 답변과 용어 설명의 톤&스타일 일치 |

**왜 동일한 모델을 사용하나요?**

1. **일관된 난이도**: 답변이 Easy 모드면 용어 설명도 초보자용으로 생성
2. **스타일 통일**: 답변과 용어 설명이 같은 수준의 언어로 작성됨
3. **정확도 향상**: 답변 컨텍스트를 이해하는 동일 모델이 더 적절한 용어 추출

**전체 프로세스 (초보자 설명):**

```
[1단계] 사용자 질문
"GAN이 뭐야?"
    ↓
[2단계] 답변 생성 LLM (GPT-5 또는 Solar Pro2)
답변: "GAN은 Generator와 Discriminator로 구성된...
       적대적 학습(Adversarial Learning)을 통해..."
    ↓
[3단계] 답변 표시 (사용자에게)
사용자는 즉시 답변을 볼 수 있음
    ↓
[4단계] 용어 추출 LLM (GPT-4o Mini) - 백그라운드 실행
프롬프트:
  "다음 답변에서 AI/ML 관련 전문 용어를 1-5개 추출하고,
   각 용어에 대한 정의와 난이도별 설명을 생성하세요.

   답변: GAN은 Generator와 Discriminator로 구성된...
         적대적 학습(Adversarial Learning)을 통해..."

LLM 응답 (JSON):
{
  "terms": [
    {
      "term": "GAN",
      "definition": "Generative Adversarial Network의 약자로...",
      "easy_explanation": "두 개의 신경망이 서로 경쟁하면서...",
      "hard_explanation": "Generator G(z)와 Discriminator D(x)의...",
      "category": "Deep Learning",
      "difficulty_level": "advanced",
      "related_terms": ["Generator", "Discriminator"],
      "examples": "이미지 생성, 스타일 변환"
    },
    {
      "term": "Generator",
      "definition": "GAN에서 가짜 데이터를 생성하는 모델...",
      ...
    },
    {
      "term": "Discriminator",
      "definition": "GAN에서 진짜/가짜를 구분하는 모델...",
      ...
    }
  ]
}
    ↓
[5단계] JSON 파싱 및 DB 저장
- 3개 용어 파싱 완료
- glossary 테이블에 INSERT
- 중복 용어는 자동 스킵 (ON CONFLICT DO NOTHING)
    ↓
[6단계] 토스트 메시지 표시
"✅ 3개 용어가 용어집에 추가되었습니다!"
```

**실제 구현 코드:**

```python
# src/utils/glossary_extractor.py

def extract_and_save_terms(answer, difficulty, min_terms, max_terms, logger):
    """
    LLM을 사용하여 답변에서 AI/ML 용어 추출 및 저장
    """
    # 1. LLM 초기화
    # 난이도별 LLM 클라이언트 생성 (답변 생성과 동일한 모델 사용)
    llm_client = LLMClient.from_difficulty(difficulty=difficulty, logger=logger)

    # 2. 프롬프트 구성
    prompt = f"""다음 답변에서 사용된 AI/ML/NLP/CV/RL 관련 전문 용어를 추출하고,
각 용어에 대한 정의와 난이도별 설명을 생성하세요.

**중요 조건:**
1. **IT 용어만 추출**: AI/ML/NLP/CV/RL 등 IT 관련 용어만
2. **품질 우선**: 정확성/유사도 높은 순으로 우선순위 정렬
3. **무작위 단어 금지**: 최소 개수 미달 시 실제 추출된 개수만 반환
4. **추출 개수**: {min_terms}개 이상 {max_terms}개 이하

답변:
{answer}

JSON 형식으로만 반환:
{{
  "terms": [
    {{
      "term": "용어명",
      "definition": "간단한 정의",
      "easy_explanation": "초보자용 쉬운 설명",
      "hard_explanation": "전문가용 상세 설명",
      "category": "카테고리 (예: NLP, CV, RL)",
      "difficulty_level": "beginner/intermediate/advanced",
      "related_terms": ["관련 용어1", "관련 용어2"],
      "examples": "사용 예시"
    }}
  ]
}}"""

    # 3. LLM 호출
    response = llm_client.llm.invoke(prompt)

    # 4. JSON 파싱
    import json
    data = json.loads(response.content)
    terms = data.get("terms", [])

    # 5. DB 저장
    saved_count = 0
    for term_data in terms:
        try:
            conn = psycopg2.connect(...)
            cursor.execute("""
                INSERT INTO glossary (
                    term, definition, easy_explanation, hard_explanation,
                    category, difficulty_level, related_terms, examples
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (term) DO NOTHING  -- 중복 스킵
            """, (...))
            conn.commit()
            saved_count += 1
        except Exception as e:
            logger.write(f"용어 저장 실패: {e}")

    return saved_count
```

**비용 및 시간:**

| 항목 | 값 |
|------|-----|
| **LLM 모델** | GPT-4o Mini (기본값) |
| **토큰 수** | 약 500-1000 토큰 (답변 + 프롬프트) |
| **비용** | 약 $0.0001-0.0003 (답변당) |
| **응답 시간** | 1-3초 (백그라운드) |

---

### Q2-5. 용어 추출 실패하면 어떻게 되나요?

**A:** **사용자 경험에 영향 없이 조용히 실패 처리**됩니다.

**실패 처리 원칙: "Silent Failure"**

용어 추출은 **보조 기능**이므로, 실패해도 메인 기능(답변 생성)에 영향을 주면 안 됩니다.

**에러 처리 흐름:**

```
[메인 기능] 답변 생성
    ↓
답변 표시 (성공) ← 사용자는 여기까지만 봄
    ↓
[보조 기능] 용어 추출 시작
    ↓
┌─────────────────────────────────┐
│ try:                            │
│   extract_and_save_terms(...)   │
│ except Exception as e:          │
│   logger.write("실패")          │
│   # 에러 무시                    │
└─────────────────────────────────┘
    ↓
실패 → 로그에만 기록
성공 → 토스트 메시지 표시
```

**코드 구현:**

```python
# ui/components/chat_interface.py

# 답변 생성 완료 (메인 기능)
st.markdown(answer)

# 용어 추출 (보조 기능)
if tool_choice in GLOSSARY_ENABLED_TOOLS:
    try:
        saved_count = extract_and_save_terms(
            answer=answer,
            difficulty=difficulty,
            min_terms=st.session_state.get("glossary_min_terms", 1),
            max_terms=st.session_state.get("glossary_max_terms", 5),
            logger=exp_manager.logger
        )

        if saved_count > 0:
            st.toast(f"✅ {saved_count}개 용어가 용어집에 추가되었습니다!", icon="📚")
        else:
            # 추출된 용어 없음 (에러 아님, 정상 케이스)
            pass

    except Exception as e:
        # 에러 발생 - 조용히 실패
        if exp_manager:
            exp_manager.logger.write(
                f"용어 자동 저장 실패: {e}",
                print_error=True
            )
        # 사용자에게는 아무것도 표시 안 함
```

**실패 가능한 케이스:**

| 실패 원인 | 로그 기록 | 사용자 표시 | 메인 기능 영향 |
|---------|---------|-----------|-------------|
| **LLM API 오류** (키 없음, 할당량 초과) | ✅ | ❌ | ❌ 영향 없음 |
| **JSON 파싱 오류** (LLM이 잘못된 형식 반환) | ✅ | ❌ | ❌ 영향 없음 |
| **DB 연결 오류** (PostgreSQL 중단) | ✅ | ❌ | ❌ 영향 없음 |
| **용어 없음** (IT 용어 0개 추출) | ❌ | ❌ | ❌ 영향 없음 (정상 케이스) |

**로그 예시:**

```
# experiments/20251104/20251104_103015_session_001/chatbot.log

[2025-11-04 10:30:45] 답변 생성 완료: 500 글자
[2025-11-04 10:30:46] 용어 자동 추출 시작
[2025-11-04 10:30:48] 용어 자동 저장 실패: OpenAI API rate limit exceeded
[2025-11-04 10:30:48] 에러 스택 트레이스:
Traceback (most recent call last):
  File "src/utils/glossary_extractor.py", line 45, in extract_and_save_terms
    response = llm.invoke(prompt)
openai.error.RateLimitError: Rate limit exceeded
```

**사용자 화면:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 RAG 논문 검색

[답변 내용...]

📋 복사   💾 저장

📊 답변 품질 평가 결과 (34/40점)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

← 용어 추출 실패했지만 사용자는 모름
```

**왜 조용히 실패해야 하나요?**

1. **사용자 경험 최우선**: 답변 보기가 목적, 용어 추출은 부가 기능
2. **에러 피로도 방지**: 매번 "용어 추출 실패" 메시지 뜨면 짜증남
3. **신뢰도 유지**: 메인 기능은 정상 작동함을 보여줌
4. **디버깅 가능**: 로그에는 상세히 기록되어 있어 문제 해결 가능

**향후 개선 방안:**

```python
# 옵션 1: 재시도 로직 (현재 미구현)
# configs/model_config.yaml의 embeddings.max_retries 설정값 사용 (기본값: 3)
max_retries = config.get("embeddings.max_retries", 3)

for retry in range(max_retries):
    try:
        return extract_and_save_terms(...)
    except Exception as e:
        if retry == max_retries - 1:  # 마지막 시도
            logger.write(f"{max_retries}번 시도 모두 실패")
        else:
            time.sleep(1)  # 1초 대기 후 재시도

# 옵션 2: 대체 모델 사용
# configs/model_config.yaml에서 사용자가 정의한 모델을 최우선시
try:
    llm = ChatOpenAI(model="gpt-4o-mini")  # 기본값
    ...
except:
    # GPT 실패 시 Solar로 대체
    llm = ChatOpenAI(model="solar-pro2")
    ...
```

**이유:**
- 용어 추출은 부가 기능
- 실패해도 사용자 답변에는 문제없음
- 로그에만 기록

---

### Q2-6. 중복 용어는 어떻게 처리하나요?

**A:** **PostgreSQL의 `ON CONFLICT` 절로 자동 처리**됩니다.

**SQL 쿼리:**
```sql
INSERT INTO glossary (term, definition, easy_explanation, hard_explanation, category, created_at)
VALUES (%s, %s, %s, %s, %s, NOW())
ON CONFLICT (term) DO NOTHING
RETURNING term_id;
```

**동작:**
- `term`이 PRIMARY KEY이므로 중복 불가
- 이미 존재하는 용어면 `DO NOTHING` (무시)
- 새로운 용어만 INSERT

**예시:**
- "GAN"이 이미 glossary에 있으면 → 무시
- "Diffusion Model"이 없으면 → 새로 저장

---

## 3. 용어집 검색

### Q3-1. 용어집 검색 도구는 언제 사용되나요?

**A:** 사용자가 **용어 정의를 직접 질문**할 때 Router가 자동으로 선택합니다.

**라우팅 패턴:**
| 질문 | 선택되는 도구 |
|------|-------------|
| "Attention이 뭐야?" | `glossary` |
| "BLEU Score 설명해줘" | `glossary` |
| "Fine-tuning이란?" | `glossary` |
| "Transformer 논문 설명해줘" | `search_paper` (용어가 아닌 논문 질문) |

---

### Q3-2. 용어집에 없는 용어를 질문하면?

**A:** **두 가지 시나리오**로 처리됩니다.

---

#### 🎯 시나리오 1: Router가 glossary 도구를 선택한 경우

**실행 흐름:**
```
사용자 질문: "ml이 뭐야?"
    ↓
Step 1. Router 노드 (src/agent/nodes.py:27-71)
    - LLM이 질문 분석하여 도구 선택
    - 선택: "glossary" (용어 정의 질문으로 판단)
    ↓
Step 2. Glossary 도구 실행 (src/tools/glossary.py:428-510)
    - VectorDB (glossary_embeddings) + SQL (glossary 테이블) 하이브리드 검색
    - search_glossary() 함수 호출 (mode="hybrid", top_k=3)
    ↓
Step 3. 검색 결과 처리
    [Case A] 검색 결과 있음:
        - 용어 정의, 난이도별 설명, 관련 용어 반환
        - LLM이 이를 바탕으로 사용자 친화적 답변 생성
        - END

    [Case B] 검색 결과 없음: ⚠️ 현재 시스템의 Fallback
        - _format_glossary_md() 함수가 "관련 용어를 찾을 수 없습니다." 반환
        - 이 메시지를 glossary 도구의 LLM에게 전달
        - LLM이 자체 지식(GPT-5 또는 Solar Pro2 학습 데이터)으로 답변 생성
        - 예: "ML은 Machine Learning의 약자로..."
        - END
```

**코드 위치:**
```python
# src/tools/glossary.py:266-278
def _format_glossary_md(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "관련 용어를 찾을 수 없습니다."  # ← Fallback 메시지
    # ...

# src/tools/glossary.py:475-481
user_content = f"""[용어집 검색 결과]
{raw_results}  # ← "관련 용어를 찾을 수 없습니다."가 여기 전달됨

[질문]
{question}

위 검색 결과를 바탕으로 질문에 답변해주세요."""
# LLM이 이 메시지를 보고 자체 지식으로 답변 생성

# src/agent/graph.py:112-113
for node in ["glossary", ...]:
    workflow.add_edge(node, END)  # ← glossary 실행 후 바로 종료
```

**중요:**
- ❌ **다른 도구(search_paper, web_search, general)로 자동 전환되지 않음**
- ❌ **재라우팅 메커니즘 없음** (LangGraph 구조상 한 번 선택된 도구만 실행)
- ✅ **glossary 도구 내부에서만 LLM 자체 지식으로 Fallback**

---

#### 🎯 시나리오 2: Router가 general 도구를 선택한 경우

**실행 흐름:**
```
사용자 질문: "ml이 뭐야?"
    ↓
Step 1. Router 노드
    - LLM이 질문 분석
    - 선택: "general" (간단한 질문으로 판단)
    ↓
Step 2. General 도구 실행 (src/tools/general_answer.py)
    - LLM에게 바로 질문 전달
    - LLM 자체 지식으로 답변 생성
    - END
```

---

#### ⚠️ 현재 시스템의 한계

**1. 도구 간 자동 전환 없음**
```
문제 시나리오:
사용자: "최신 Diffusion Model 논문 찾아줘"
    ↓
Router: search_paper 선택
    ↓
search_paper: DB에 관련 논문 없음 → "관련 논문을 찾을 수 없습니다."
    ↓
END (종료) ❌
    ↓
❌ web_search로 자동 전환 안 됨
❌ general로 Fallback 안 됨
```

**2. 도구 선택 실패 시 재시도 없음**
```
문제 시나리오:
사용자: "Attention 메커니즘 설명해줘"
    ↓
Router: 실수로 save_file 선택 (잘못된 판단)
    ↓
save_file: 파일 경로 없음 → 오류
    ↓
END (종료) ❌
    ↓
❌ 도구 재선택 안 됨
❌ glossary나 general로 자동 전환 안 됨
```

**3. Fallback Chain 없음**
```
이상적인 Fallback Chain:
glossary 검색 → 실패
    ↓
search_paper 검색 → 실패
    ↓
web_search 검색 → 실패
    ↓
general 답변 (최종 Fallback)

현재 구현:
선택된 도구 1개만 실행 → END
```

---

#### 💡 향후 개선 방향

**제안 1: 도구 우선순위 기반 자동전환**
```yaml
# configs/model_config.yaml (신규)
fallback_chain:
  enabled: true
  max_retries: 3  # 도구 실행 실패 시 최대 재시도 횟수

  # 질문 유형별 도구 우선순위
  term_definition:
    priority: [glossary, general]

  paper_search:
    priority: [search_paper, web_search, general]

  latest_research:
    priority: [web_search, search_paper, general]
```

**제안 2: 조건부 재라우팅 노드 추가**
```python
# src/agent/graph.py (개선안)
def should_fallback(state: AgentState):
    """도구 실행 결과가 실패인지 확인"""
    result = state.get("final_answer", "")

    # 실패 패턴 감지
    fail_patterns = [
        "관련 용어를 찾을 수 없습니다",
        "관련 논문을 찾을 수 없습니다",
        "검색 결과가 없습니다"
    ]

    if any(pattern in result for pattern in fail_patterns):
        return "retry"  # 재라우팅
    return "end"

# Fallback 라우팅 노드 추가
workflow.add_conditional_edges(
    "glossary",
    should_fallback,
    {
        "retry": "fallback_router",  # 다음 우선순위 도구 선택
        "end": END
    }
)
```

**제안 3: Router 선택 검증 노드**
```python
def validate_tool_choice(state: AgentState):
    """Router가 올바른 도구를 선택했는지 검증"""
    question = state["question"]
    tool_choice = state["tool_choice"]

    # LLM에게 재확인 (configs에서 설정한 횟수만큼)
    validation_prompt = f"""
    질문: {question}
    선택된 도구: {tool_choice}

    이 도구 선택이 적절한가요? (yes/no)
    """

    is_valid = llm.invoke(validation_prompt)

    if is_valid == "no":
        return "re_route"  # 재라우팅
    return "proceed"  # 선택된 도구 실행
```

---

#### 📚 관련 이슈

- [01-3_도구_자동전환_및_Fallback_메커니즘.md](../issues/01-3_도구_자동전환_및_Fallback_메커니즘.md) - 도구 간 자동전환 기능 구현 제안

---

### Q3-3. 난이도별로 다른 설명을 제공하나요?

**A:** 네, **Easy/Hard 모드에 따라 다른 설명 필드를 반환**합니다.

| 난이도 | 사용 필드 | 설명 |
|--------|----------|------|
| Easy | `easy_explanation` | 쉬운 용어, 비유/예시 포함 |
| Hard | `hard_explanation` | 전문 용어, 수식/기술 세부사항 |
| Fallback | `definition` | 간단한 정의 (1-2문장) |

**코드:**
```python
def _pick_explanation(row: Dict, difficulty_mode: str) -> str:
    if difficulty_mode == "easy":
        return row.get("easy_explanation") or row.get("definition") or ""
    if difficulty_mode == "hard":
        return row.get("hard_explanation") or row.get("definition") or ""
    # Auto 모드는 difficulty_level 기준 자동 선택
    ...
```

---

### Q3-4. 용어집 검색은 SQL만 사용하나요, Vector 검색도 하나요?

**A:** **하이브리드 검색**을 지원합니다 (SQL + Vector).

**검색 모드 3가지:**
1. **SQL 검색**: PostgreSQL ILIKE 검색 (정확 매칭)
2. **Vector 검색**: PGVector 유사도 검색 (의미적 유사성)
3. **Hybrid 검색**: SQL + Vector 결과 병합 후 중복 제거

**기본 설정:**
- `src/tools/glossary.py`: Hybrid 모드
- `mode` 파라미터로 변경 가능

---

## 4. 데이터베이스

### Q4-1. glossary 테이블 스키마는?

**A:**
```sql
CREATE TABLE glossary (
    term_id SERIAL PRIMARY KEY,
    term VARCHAR(255) UNIQUE NOT NULL,
    definition TEXT,
    easy_explanation TEXT,
    hard_explanation TEXT,
    category VARCHAR(100),
    difficulty_level VARCHAR(50),
    related_terms TEXT[],
    examples TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**주요 필드:**
- `term`: 용어명 (PRIMARY KEY, UNIQUE)
- `definition`: 간단한 정의
- `easy_explanation`: Easy 모드 설명
- `hard_explanation`: Hard 모드 설명
- `category`: 카테고리 (Deep Learning, NLP 등)

---

### Q4-2. Vector DB도 사용하나요?

**A:** 네, **glossary_embeddings 컬렉션**을 사용합니다.

**설정:**
- 컬렉션명: `glossary_embeddings` (환경변수 `PGV_COLLECTION_GLOSSARY`)
- 임베딩 모델: `text-embedding-3-small`
- 용도: 의미적 유사성 검색

**언제 사용?**
- 용어 검색 시 Vector 모드 또는 Hybrid 모드
- "Attention 메커니즘"과 "Self-Attention"을 유사하다고 판단 가능

---

### Q4-3. glossary 테이블이 비어있으면?

**A:** 초기에는 비어있고, **사용하면서 자동으로 채워집니다**.

**채워지는 방법:**
1. 사용자 질문 → 도구 답변 생성 → 용어 자동 추출 → glossary 저장
2. 반복하면 용어집이 점점 확장

**수동 초기 데이터:**
- 필요하면 SQL INSERT로 수동 추가 가능
- 예시 스크립트는 `database/` 폴더 참조

---

## 5. 도구별 동작

### Q5-1. 일반 답변 도구에서도 용어가 저장되나요?

**A:** 네, **저장됩니다**.

**예시:**
- 질문: "GAN 설명해줘"
- 도구: `general_answer`
- 답변: "GAN은 Generator와 Discriminator가 경쟁하며 학습하는 모델입니다..."
- 용어 추출: ["GAN", "Generator", "Discriminator"]
- glossary 저장: ✅

---

### Q5-2. RAG 검색 후에도 용어가 저장되나요?

**A:** 네, **논문 검색 결과를 바탕으로 생성된 답변에서 용어 추출**됩니다.

**예시:**
- 질문: "Transformer 논문 설명해줘"
- 도구: `search_paper`
- 답변: "Transformer는 Self-Attention 메커니즘을 사용하며..."
- 용어 추출: ["Transformer", "Self-Attention", "Multi-Head Attention"]
- glossary 저장: ✅

---

### Q5-3. 웹 검색에서도 용어가 저장되나요?

**A:** 네, **저장됩니다**.

**예시:**
- 질문: "2025년 최신 LLM 논문은?"
- 도구: `web_search`
- 답변: "GPT-5는 Mixture of Experts 구조를 사용합니다..."
- 용어 추출: ["GPT-5", "Mixture of Experts"]
- glossary 저장: ✅

---

### Q5-4. text2sql 도구 사용 시 용어가 저장되지 않는 이유는?

**A:** **답변에 AI/ML 용어가 전혀 없기 때문**입니다.

**text2sql 답변 구조:**
```
**질문**: ...
**생성된 SQL**: SELECT ...
**결과**: (테이블)
```

→ SQL 구문과 통계 결과만 있고, "GAN", "Transformer" 같은 AI/ML 용어가 없음

**불필요한 LLM 호출 방지:**
- 용어 추출을 위해 LLM 호출 → 비용 발생
- 어차피 빈 리스트만 반환 → 낭비
- 따라서 아예 호출하지 않음

---

## 6. 트러블슈팅

### Q6-1. 용어가 저장되지 않아요

**체크리스트:**
1. **도구가 화이트리스트에 있는지 확인**
   - text2sql, save_file은 제외됨
2. **PostgreSQL 연결 확인**
   - `DATABASE_URL` 환경변수 설정됐는지
3. **LLM API 키 확인**
   - `OPENAI_API_KEY` 또는 `SOLAR_API_KEY` 설정됐는지
4. **로그 확인**
   - `experiments/{날짜}/{세션}/logs/main.log`에서 "용어 추출" 검색
5. **glossary 테이블 존재 확인**
   ```sql
   SELECT * FROM glossary LIMIT 5;
   ```

---

### Q6-2. 용어 추출이 너무 느려요

**원인:** LLM 호출이 1번 더 발생하기 때문입니다.

**개선 방법:**
1. **Solar Pro2 사용** (빠르고 저렴)
   - `configs/model_config.yaml`에서 provider 변경
2. **비동기 처리** (향후 개선)
   - 사용자 답변은 바로 표시
   - 용어 추출은 백그라운드에서 실행
3. **캐싱** (향후 개선)
   - 동일한 답변은 이전 추출 결과 재사용

---

### Q6-3. 중복 용어가 계속 저장되려고 해요

**A:** 정상 동작입니다. PostgreSQL이 자동으로 무시합니다.

**SQL 동작:**
```sql
ON CONFLICT (term) DO NOTHING
```
→ 이미 있는 용어는 무시 (INSERT 안 됨)

**로그 메시지:**
```
용어 이미 존재 (건너뜀): GAN
```

---

### Q6-4. 용어 추출 실패 로그가 보여요

**확인 사항:**
1. **LLM API 키 유효성**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```
2. **JSON 파싱 오류**
   - LLM이 잘못된 JSON 반환
   - 로그에서 LLM 응답 확인
3. **네트워크 오류**
   - API 호출 타임아웃
   - tenacity 재시도 로직 확인

---

## 7. 최적화 및 성능

### Q7-1. 용어 추출 비용은 얼마나 드나요?

**A:** 도구별 LLM 호출 횟수에 따라 다릅니다.

**비용 예시 (OpenAI GPT-5 기준):**
| 도구 | 기본 답변 비용 | 용어 추출 비용 | 총 비용 |
|------|--------------|--------------|---------|
| general_answer | $0.003 | $0.002 | $0.005 |
| search_paper | $0.015 | $0.002 | $0.017 |
| web_search | $0.005 | $0.002 | $0.007 |
| glossary | $0.005 | $0.002 | $0.007 |
| summarize | $0.08 | $0.002 | $0.082 |

**절감 방법:**
- text2sql, save_file 제외로 불필요한 호출 방지 ✅ 구현됨
- Solar Pro2 사용 (GPT-5 대비 1/10 비용)

---

### Q7-2. 용어 추출을 비활성화할 수 있나요?

**A:** 코드 수정으로 가능합니다.

**방법 1: 화이트리스트 비우기**
```python
# ui/components/chat_interface.py
GLOSSARY_ENABLED_TOOLS = set()  # 빈 set → 모든 도구 제외
```

**방법 2: 조건 추가**
```python
# 환경변수로 제어
import os
ENABLE_GLOSSARY_EXTRACTION = os.getenv("ENABLE_GLOSSARY", "true").lower() == "true"

if tool_choice in GLOSSARY_ENABLED_TOOLS and ENABLE_GLOSSARY_EXTRACTION:
    extract_and_save_terms(...)
```

**방법 3: 함수 자체를 no-op으로**
```python
# src/utils/glossary_extractor.py
def extract_and_save_terms(...):
    return 0  # 즉시 반환
```

---

### Q7-3. 용어 추출 속도를 개선하려면?

**개선 방법:**

1. **비동기 처리** (향후 구현)
   ```python
   import asyncio

   async def extract_terms_async(...):
       # 백그라운드에서 실행
       pass
   ```

2. **배치 처리** (향후 구현)
   - 여러 답변 모아서 한 번에 LLM 호출
   - 비용 절감 + 속도 향상

3. **캐싱** (향후 구현)
   - 동일 답변은 이전 결과 재사용
   - Redis 캐시 활용

4. **Solar Pro2 사용** (현재 가능)
   - GPT-5 대비 빠르고 저렴
   - `configs/model_config.yaml` 수정

---

### Q7-4. 용어집이 너무 커지면 성능 문제는?

**A:** PostgreSQL 인덱스로 해결됩니다.

**현재 인덱스:**
```sql
CREATE UNIQUE INDEX idx_glossary_term ON glossary(term);
```

**추가 최적화 (필요시):**
1. **Full-text search 인덱스**
   ```sql
   CREATE INDEX idx_glossary_definition_fts
   ON glossary USING gin(to_tsvector('english', definition));
   ```

2. **PGVector 인덱스** (Vector 검색)
   ```sql
   CREATE INDEX ON glossary_embeddings USING ivfflat (embedding vector_cosine_ops);
   ```

3. **Materialized View** (통계 쿼리 최적화)
   ```sql
   CREATE MATERIALIZED VIEW glossary_stats AS
   SELECT category, COUNT(*) FROM glossary GROUP BY category;
   ```

---

## 8. 고급 활용

### Q8-1. 용어를 수동으로 추가할 수 있나요?

**A:** 네, **SQL INSERT**로 가능합니다.

**예시:**
```sql
INSERT INTO glossary (term, definition, easy_explanation, hard_explanation, category)
VALUES (
    'Attention',
    'Attention is a mechanism that allows models to focus on relevant parts of input.',
    'Attention은 중요한 부분에 집중하는 메커니즘입니다. 마치 책을 읽을 때 중요한 문장에 형광펜을 칠하는 것과 같습니다.',
    'Attention mechanism computes weighted sum of values based on query-key similarity: Attention(Q,K,V) = softmax(QK^T/√d_k)V',
    'Deep Learning'
);
```

---

### Q8-2. 용어를 수정하려면?

**A:** **UPDATE 쿼리**로 가능합니다.

**예시:**
```sql
UPDATE glossary
SET easy_explanation = '새로운 쉬운 설명',
    hard_explanation = '새로운 어려운 설명',
    updated_at = NOW()
WHERE term = 'Attention';
```

---

### Q8-3. 용어를 삭제하려면?

**A:** **DELETE 쿼리**로 가능합니다.

```sql
DELETE FROM glossary WHERE term = 'Attention';
```

**주의:**
- 자동 추출 시 다시 생성될 수 있음
- 완전히 방지하려면 용어 블랙리스트 구현 필요

---

### Q8-4. 카테고리별 통계를 보려면?

**A:** **집계 쿼리**로 확인 가능합니다.

```sql
SELECT category, COUNT(*) AS term_count
FROM glossary
GROUP BY category
ORDER BY term_count DESC;
```

**예시 결과:**
```
category        | term_count
----------------|------------
Deep Learning   | 42
NLP             | 28
Computer Vision | 15
Reinforcement   | 8
```

---

## 9. 참고 자료

### 관련 문서
- [09_도구_시스템.md](../modularization/09_도구_시스템.md) - 용어집 도구 및 자동 추출 설명
- [05_데이터베이스_시스템.md](../modularization/05_데이터베이스_시스템.md) - glossary 테이블 스키마

### 구현 파일
- `src/tools/glossary.py` - 용어집 검색 도구
- `src/utils/glossary_extractor.py` - 용어 자동 추출 함수
- `ui/components/chat_interface.py` - 도구별 선택적 호출 로직

### DB 스키마
- `database/schema.sql` - glossary 테이블 정의

---

## 작성자
- **최현화[팀장]** (용어집 시스템 구현 및 문서화)
