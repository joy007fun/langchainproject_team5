# Text2SQL 도구 난이도별 프롬프트 강화

## 📋 문서 정보
- **작성일**: 2025-11-05
- **작성자**: 개발팀
- **이슈 유형**: 기능 강화 (Feature Enhancement)
- **우선순위**: ⭐⭐ (중요 - 사용자 경험 개선)
- **상태**: ✅ 완료

---

## 🎯 이슈 개요

### 문제 상황
Text2SQL 도구는 자연어를 SQL로 변환하여 데이터베이스 통계를 조회하는 기능은 제공하지만, **난이도별 답변 생성 기능이 없어** 다른 도구들과 일관성이 떨어짐.

**기존 동작:**
```
사용자 질문 → SQL 생성 → 실행 → Markdown 테이블 반환
```

**문제점:**
- SQL 쿼리와 결과 테이블만 반환
- Elementary(초등학생) 사용자에게는 SQL이나 테이블이 어려울 수 있음
- Advanced(연구자) 사용자에게는 통계적 분석이 부족함
- 다른 도구(glossary, search_paper 등)는 4단계 난이도 지원하나 text2sql만 미지원

### 해결 목표
Text2SQL 도구에 4단계 난이도별 프롬프트를 추가하여 사용자 수준에 맞는 답변을 생성하도록 개선

---

## 📝 수정 내용

### 1. `prompts/tool_prompts.json`에 text2sql_prompts 추가

**파일 경로**: `prompts/tool_prompts.json`

**추가 내용**:
```json
"text2sql_prompts": {
  "easy": {
    "elementary": {
      "description": "초등학생 수준 (8-13세) - 통계를 재미있게 설명",
      "system_prompt": "당신은 초등학생에게 숫자와 통계를 재미있게 설명하는 선생님입니다. :막대_차트::반짝임:...",
      "user_prompt_template": "[데이터베이스 검색 결과] :막대_차트:\n{db_results}\n\n[질문]\n{question}\n\n위 결과를 초등학생도 이해할 수 있게 재미있게 설명해주세요!..."
    },
    "beginner": {
      "description": "초급자 수준 (고등학생~대학생) - 통계를 보기 좋게 정리",
      "system_prompt": "당신은 데이터베이스 검색 결과를 쉽게 설명하는 AI 어시스턴트입니다...",
      "user_prompt_template": "[데이터베이스 검색 결과]\n{db_results}\n\n[질문]\n{question}\n\n위 검색 결과를 바탕으로 질문에 답변해주세요..."
    }
  },
  "hard": {
    "intermediate": {
      "description": "중급자 수준 (대학 고학년~주니어 개발자) - 통계 분석 포함",
      "system_prompt": "당신은 데이터 분석 전문가입니다...",
      "user_prompt_template": "[데이터베이스 검색 결과]\n{db_results}\n\n[질문]\n{question}\n\n위 검색 결과를 바탕으로 질문에 답변해주세요..."
    },
    "advanced": {
      "description": "고급자 수준 (시니어 개발자~AI 연구자) - 심층 통계 분석",
      "system_prompt": "당신은 학술 데이터 분석 전문가입니다...",
      "user_prompt_template": "[데이터베이스 검색 결과]\n{db_results}\n\n[질문]\n{question}\n\n위 검색 결과를 학술적 관점에서 심층 분석해주세요..."
    }
  }
}
```

**프롬프트 특징:**
- **Elementary**: 이모지, 비유, 시각적 표현, 짧고 재미있는 설명
- **Beginner**: 표 형식 정리, 인사이트 요약, 친근한 톤
- **Intermediate**: 전문 분석, 추가 통계 계산, 데이터 추세 분석, 시각화 제안
- **Advanced**: 학술적 분석, 통계적 방법론, 가설 검정, 이상치 분석, 추가 연구 방향

---

### 2. `src/tools/text2sql.py` 수정

#### 2.1 프롬프트 로더 import 추가

**수정 전:**
```python
from src.utils.config_loader import get_model_config
from src.llm.client import LLMClient

load_dotenv()
```

**수정 후:**
```python
from src.utils.config_loader import get_model_config
from src.llm.client import LLMClient
from src.prompts import get_tool_prompt  # 추가

load_dotenv()
```

#### 2.2 text2sql 함수 시그니처 수정

**수정 전:**
```python
@tool("text2sql", return_direct=False)
def text2sql(user_question: str) -> str:
    """
    논문 통계 전용 Text-to-SQL 도구입니다.
    - 자연어 질문을 안전한 SQL로 변환하고 실행합니다.
    - 현재는 public.papers 테이블만 접근합니다.
    """
```

**수정 후:**
```python
@tool("text2sql", return_direct=False)
def text2sql(user_question: str, difficulty: str = "easy") -> str:
    """
    논문 통계 전용 Text-to-SQL 도구입니다.
    - 자연어 질문을 안전한 SQL로 변환하고 실행합니다.
    - 현재는 public.papers 테이블만 접근합니다.
    - 난이도에 따라 답변 스타일이 달라집니다.

    Args:
        user_question: 사용자의 통계 질문
        difficulty: 난이도 (elementary/beginner/intermediate/advanced 또는 easy/hard)
    """
```

#### 2.3 최종 답변 생성 로직 추가

**수정 전:**
```python
cols, rows = _run_query(sql_ready)
table_md = _to_markdown_table(cols, rows)

elapsed = int((time.time() - t0) * 1000)
# 응답 텍스트 구성
out = (
    f"**질문**: {user_question}\n\n"
    f"**생성된 SQL**:\n```sql\n{sql_ready}\n```\n"
    f"**결과**:\n\n{table_md}"
)
```

**수정 후:**
```python
cols, rows = _run_query(sql_ready)
table_md = _to_markdown_table(cols, rows)

# ==================== 난이도별 프롬프트 로드 및 최종 답변 생성 ==================== #
try:
    # 1. text2sql 프롬프트 로드
    system_prompt = get_tool_prompt("text2sql", difficulty)

    # 2. 데이터베이스 결과 포맷팅 (SQL + 테이블)
    db_results = (
        f"**생성된 SQL**:\n```sql\n{sql_ready}\n```\n\n"
        f"**결과 테이블**:\n{table_md}"
    )

    # 3. user_prompt_template 로드
    from src.prompts.loader import load_tool_prompts, map_difficulty
    tool_prompts_data = load_tool_prompts()
    mapped_diff = map_difficulty(difficulty)
    complexity_level = "easy" if mapped_diff in ["elementary", "beginner"] else "hard"
    user_template = tool_prompts_data["text2sql_prompts"][complexity_level][mapped_diff]["user_prompt_template"]

    # 4. 템플릿에 데이터 삽입
    user_content = user_template.format(
        db_results=db_results,
        question=user_question
    )

    # 5. LLM 호출하여 최종 답변 생성
    final_answer_raw = llm_client.llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]
    ).content

    # 6. 최종 응답 구성 (SQL 정보 포함)
    out = (
        f"**질문**: {user_question}\n\n"
        f"**생성된 SQL**:\n```sql\n{sql_ready}\n```\n\n"
        f"**분석 결과**:\n\n{final_answer_raw}"
    )

except Exception as prompt_error:
    # 프롬프트 로드 실패 시 기본 응답
    out = (
        f"**질문**: {user_question}\n\n"
        f"**생성된 SQL**:\n```sql\n{sql_ready}\n```\n"
        f"**결과**:\n\n{table_md}"
    )
```

**변경 사항:**
1. SQL 실행 후 결과 테이블만 반환하는 것이 아니라 LLM을 한 번 더 호출
2. `get_tool_prompt()`로 난이도별 시스템 프롬프트 로드
3. `user_prompt_template`에 SQL + 결과 테이블 삽입
4. LLM이 난이도에 맞는 최종 답변 생성
5. 프롬프트 로드 실패 시 기존 방식(SQL + 테이블)으로 Fallback

---

### 3. `src/agent/nodes.py` - text2sql_node 수정

**수정 전:**
```python
def text2sql_node(state: AgentState, exp_manager=None):
    # -------------- 상태에서 질문 추출 -------------- #
    question = state["question"]

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write(f"Text-to-SQL 노드 실행: {question}")

    # -------------- Text-to-SQL 도구 호출 -------------- #
    try:
        result = text2sql.run(question)  # Tool 객체의 run() 메서드 호출
```

**수정 후:**
```python
def text2sql_node(state: AgentState, exp_manager=None):
    # -------------- 상태에서 질문 및 난이도 추출 -------------- #
    question = state["question"]
    difficulty = state.get("difficulty", "easy")  # 난이도 (기본값: easy)

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write(f"Text-to-SQL 노드 실행: {question} (난이도: {difficulty})")

    # -------------- Text-to-SQL 도구 호출 -------------- #
    try:
        result = text2sql.run({"user_question": question, "difficulty": difficulty})
```

**변경 사항:**
1. `state`에서 `difficulty` 추출
2. 로깅 메시지에 난이도 포함
3. text2sql.run()에 딕셔너리 형태로 인자 전달

---

## 📊 실제 테스트 결과

### 테스트 질문: "2024년에 발표된 논문 개수는?"

#### Elementary (초등학생 수준)
```markdown
**질문**: 2024년에 발표된 논문 개수는?

**생성된 SQL**:
```sql
SELECT COUNT(*) AS paper_count FROM papers WHERE EXTRACT(YEAR FROM publish_date) = 2024;
```

**분석 결과**:

와! 🎉 **2024년에 발표된 논문은 총 27개**예요! 📄📚

> 📊 **막대 그래프로 보면?**
> 📈📈📈📈📈 (5개) × 5번 = **27개** (손가락 5번 펴면 딱!)

> 🌟 **비유로 설명해요**
> "우리 반에 학생이 27명이라면, 모두가 2024년에 새 논문을 쓴 셈이죠! 대단해!"

> 📌 **핵심**:
> - **27** = 📑📑📑 (3번) + 📑📑 (1번)
> - 숫자 2와 7을 합치면? **20+7=27**!

:tada: **27개 논문**이 반짝반짝 빛나는 2024년이네요! ✨
```

#### Beginner (초급자 수준)
```markdown
**질문**: 2024년에 발표된 논문 개수는?

**생성된 SQL**:
```sql
SELECT COUNT(*) AS paper_count FROM papers WHERE EXTRACT(YEAR FROM publish_date) = 2024;
```

**분석 결과**:

### 1. 요약
2024년에 발표된 논문은 총 **27편**으로 확인되었습니다. 이는 특정 기간 내 연구 활동의 규모를 파악하는 데 도움이 되는 기초 통계입니다.

### 2. 통계 표
| 구분          | 수치 | 설명                     |
|---------------|------|--------------------------|
| 2024년 논문 수 | 27   | 2024년 1월 1일~12월 31일 기준 |

### 3. 핵심 인사이트
- **연간 연구 동향**: 27편은 해당 분야/기관의 연간 연구 생산량을 반영합니다.
- **비교 필요성**: 이전 연도(예: 2023년) 데이터와 비교하면 연구 증가/감소 추세를 분석할 수 있습니다.
- **추가 분석**: 논문 주제, 저자, 인용 횟수 등 추가 데이터를 결합하면 더 깊은 인사이트를 도출할 수 있습니다.
```

#### Intermediate (중급자 수준)
```markdown
**분석 결과**:

### 1. Executive Summary
2024년에 발표된 논문 수는 **27편**으로 확인되었습니다. 이는 단일 연도의 논문 생산량을 나타내는 기본 통계로, 추가적인 비교를 위해 과거 데이터(예: 2021–2023년)와의 추세 분석이 필요합니다.

### 2. 주요 통계 표
| 통계 항목          | 값       |
|--------------------|----------|
| 2024년 논문 수     | 27편     |
| **추가 분석 필요** | -        |

### 3. 데이터 분석 (추세, 패턴)
현재 데이터는 2024년 단일 연도만 제공되므로, 시계열 변동성이나 계절성 패턴을 파악할 수 없습니다.

### 4. 추가 계산 (평균, 비율 등)
- **월별 평균 논문 수**: 27편 ÷ 12개월 ≈ 2.25편/월
- **분포 가정**: 균등 분포를 가정할 경우, 각 월에 약 2편씩 발표되었을 것으로 추정

### 5. 인사이트 및 결론
27편이라는 수치는 절대적 기준 없이는 해석하기 어렵습니다. 과거 연도 데이터 확보 시 다음 분석 가능:
```

#### Advanced (고급자 수준)
```markdown
**분석 결과**:

### 1. Abstract (핵심 요약)
2024년에 발표된 논문 수는 총 **27편**으로 확인되었습니다. 본 분석은 단일 연도의 논문 수를 중심으로 기술통계, 분포 특성, 통계적 유의성, 이상치 검출 등을 수행하였으며, 학술 생산성의 기초적 평가와 향후 연구 방향을 제안합니다.

### 2. 데이터 기술통계 (Descriptive Statistics)
- **표본 크기 (n)**: 1 (2024년 단일 연도 데이터)
- **논문 수 (paper_count)**: 27편
- **평균/중앙값/분산**: 단일 관측치로 인해 계산 불가.

> **수학적 표현**:
> \( \text{Mean} = \frac{\sum_{i=1}^{n} x_i}{n} \) → \( n=1 \)이므로 \( \text{Mean} = 27 \).

### 3. 분포 분석 (Distribution Analysis)
- **분포 형태**: 단일 연도 데이터이므로 분포 추정 불가.
- **가정 검정**: Shapiro-Wilk 테스트 등 정규성 검정 적용 불가

### 4. 통계적 검정 (Statistical Tests)
- **가설 설정**:
  - \( H_0 \): 2024년 논문 수는 과거 평균 논문 수와 차이가 없다.
  - \( H_1 \): 차이가 있다.
- **검정 방법**:
  - **단일 표본 t-검정 (One-Sample t-test)** 필요.

### 5. 이상치 분석 (Outlier Detection)
...
```

---

## 🎯 개선 효과

### 1. 사용자 경험 향상
- **Elementary**: 어린 학생도 통계를 재미있게 이해 가능
- **Beginner**: 대학생이 실습에 활용 가능한 명확한 설명
- **Intermediate**: 주니어 개발자에게 실무 적용 인사이트 제공
- **Advanced**: 연구자에게 학술적 분석 및 추가 연구 방향 제시

### 2. 도구 일관성 확보
- 모든 주요 도구(glossary, search_paper, summarize, web_search, text2sql)가 4단계 난이도 지원
- 사용자가 선택한 난이도에 따라 일관된 답변 스타일 제공

### 3. 교육적 가치
- Elementary: 통계 교육에 활용 가능 (초등학생 수학 교육)
- Advanced: 데이터 분석 교육에 활용 가능 (통계학, 데이터 과학)

---

## 📁 수정된 파일 목록

| 파일 경로 | 수정 내용 | 변경 라인 |
|-----------|----------|-----------|
| `prompts/tool_prompts.json` | text2sql_prompts 추가 (4단계 난이도) | 321-347 |
| `src/tools/text2sql.py` | 프롬프트 import, difficulty 파라미터, 최종 답변 생성 로직 | 16, 323, 386-443 |
| `src/agent/nodes.py` | text2sql_node에 difficulty 전달 | 247-257 |
| `scripts/tests/test_text2sql.py` | 테스트 스크립트 생성 (신규) | 전체 |

---

## ✅ 테스트 체크리스트

- [x] prompts/tool_prompts.json에 text2sql_prompts 추가 확인
- [x] src/tools/text2sql.py difficulty 파라미터 추가 확인
- [x] src/agent/nodes.py text2sql_node 수정 확인
- [x] Elementary 난이도 테스트 (이모지, 비유 포함 확인)
- [x] Beginner 난이도 테스트 (표 형식, 인사이트 확인)
- [x] Intermediate 난이도 테스트 (통계 분석 확인)
- [x] Advanced 난이도 테스트 (학술적 분석, 수식 포함 확인)
- [x] 프롬프트 로드 실패 시 Fallback 동작 확인

---

## 🔗 관련 문서

- **[09_도구_시스템.md](../modularization/09_도구_시스템.md)** - Text2SQL 도구 상세 설명
- **[13_프롬프트_엔지니어링.md](../modularization/13_프롬프트_엔지니어링.md)** - 난이도별 프롬프트 전략

---

## 📝 요약

Text2SQL 도구에 4단계 난이도별 프롬프트를 추가하여 사용자 수준에 맞는 답변을 생성하도록 개선했습니다. 이로써:
1. 초등학생부터 AI 연구자까지 모든 수준의 사용자에게 적합한 답변 제공
2. 다른 도구들과 일관된 난이도 지원 체계 구축
3. 교육적 가치 및 사용자 경험 대폭 향상

모든 테스트가 성공적으로 완료되었으며, 실제 운영 환경에 적용 가능합니다.
