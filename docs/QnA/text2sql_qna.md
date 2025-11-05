# Text-to-SQL 시스템 Q&A

## 문서 정보
- **작성일**: 2025-11-04
- **작성자**: 최현화[팀장]
- **목적**: Text-to-SQL 시스템 관련 자주 묻는 질문 및 답변

---

## 목차
1. [기본 개념](#1-기본-개념)
2. [보안 시스템](#2-보안-시스템)
3. [SQL 생성 과정](#3-sql-생성-과정)
4. [사용 예시](#4-사용-예시)
5. [에러 처리](#5-에러-처리)
6. [로깅 시스템](#6-로깅-시스템)
7. [트러블슈팅](#7-트러블슈팅)
8. [고급 활용](#8-고급-활용)

---

## 1. 기본 개념

### Q1-1. Text-to-SQL이란?

**A:** **자연어 질문을 SQL 쿼리로 자동 변환하여 실행하는 시스템**입니다.

**동작 흐름:**
```
사용자: "2024년에 발표된 논문 개수는?"
    ↓
LLM (Solar Pro2): SQL 생성
    ↓
SELECT COUNT(*) AS paper_count
FROM papers
WHERE EXTRACT(YEAR FROM publish_date) = 2024;
    ↓
PostgreSQL 실행
    ↓
결과: paper_count | 42
```

**장점:**
- 비개발자도 DB 조회 가능
- SQL 몰라도 통계 분석 가능
- 자연어로 복잡한 집계 쿼리 생성

**단점:**
- 복잡한 JOIN은 정확도 떨어짐
- LLM이 잘못된 SQL 생성 가능 → 검증 시스템 필요

---

### Q1-2. 왜 Solar Pro2를 사용하나요?

**A:** **비용 효율성과 빠른 응답 속도** 때문입니다.

| 모델 | 비용 (1K 토큰) | 속도 | SQL 생성 정확도 |
|------|---------------|------|----------------|
| **Solar Pro2** | $0.0005 | ⚡⚡⚡ 매우 빠름 | ⭐⭐⭐ 높음 |
| GPT-5 | $0.03 | ⚡⚡ 중간 | ⭐⭐⭐ 매우 높음 |
| GPT-3.5 | $0.002 | ⚡⚡⚡ 빠름 | ⭐⭐ 중간 |

**Solar Pro2 선택 이유:**
- Text-to-SQL은 단순 변환 작업 (창의성 불필요)
- Few-shot 프롬프트로 정확도 충분히 확보
- 통계 조회는 자주 사용 → 비용 절감 중요

**설정 (configs/model_config.yaml):**
```yaml
text2sql:
  provider: solar              # Solar 사용 (비용 효율)
  model: solar-pro2            # Solar Pro2 모델 (사용자 설정 최우선)
  temperature: 0.0             # 결정론적 SQL 생성
  max_retries: 2               # SQL 생성 실패 시 최대 재시도 횟수 (기본값: 2)
```

**참고:**
- `configs/model_config.yaml`에서 사용자가 정의한 모델을 최우선시
- `text2sql.max_retries` 설정으로 재시도 횟수 조절 가능

---

### Q1-3. 어떤 테이블에 접근할 수 있나요?

**A:** 현재는 **`papers` 테이블만** 접근 가능합니다.

**허용 테이블:**
- `papers` (논문 메타데이터)

**허용 컬럼 (데이터 타입 포함):**
```python
{
    "paper_id": "SERIAL PRIMARY KEY",           # 논문 고유 ID (자동 증가)
    "title": "VARCHAR(500) NOT NULL",           # 논문 제목 (최대 500자, 필수)
    "authors": "TEXT",                          # 저자 목록
    "publish_date": "DATE",                     # 발행일 (YYYY-MM-DD 형식)
    "source": "VARCHAR(100)",                   # 출처 (arXiv, IEEE, ACL 등)
    "url": "TEXT UNIQUE",                       # 논문 URL (중복 방지)
    "category": "VARCHAR(100)",                 # 카테고리 (cs.AI, cs.CL 등)
    "citation_count": "INT DEFAULT 0",          # 인용 횟수 (기본값 0)
    "abstract": "TEXT",                         # 논문 초록
    "created_at": "TIMESTAMP DEFAULT NOW()",    # DB 생성일 (자동)
    "updated_at": "TIMESTAMP DEFAULT NOW()"     # DB 수정일 (자동)
}
```

**제한 이유:**
- 보안: 다른 테이블 무단 접근 방지
- 안정성: papers 테이블만 검증됨
- 간결성: 통계 조회에 충분

**향후 확장:**
- `glossary` 테이블 추가 (용어 통계)
- `query_logs` 테이블 추가 (로그 분석)

---

### Q1-4. Text-to-SQL과 RAG의 차이는?

**A:**

| 구분 | Text-to-SQL | RAG (search_paper) |
|------|------------|-------------------|
| **목적** | 논문 통계/집계 조회 | 논문 내용 검색 및 설명 |
| **DB 접근** | papers 테이블 (메타데이터) | paper_chunks 테이블 (본문) |
| **출력** | SQL + Markdown 표 | 논문 청크 + LLM 답변 |
| **사용 예** | "2024년 논문 개수는?" | "Transformer 논문 설명해줘" |
| **LLM 호출** | 1회 (SQL 생성) | 2회 (검색 + 답변) |
| **비용** | 매우 저렴 ($0.001) | 중간 ($0.015) |

**예시:**
```python
# Text-to-SQL 질문
"2024년에 발표된 논문 개수는?"
→ SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
→ 결과: 42편

# RAG 질문
"Transformer 논문 설명해줘"
→ paper_chunks에서 유사 청크 검색
→ LLM이 청크 기반으로 설명 생성
→ 결과: "Transformer는 2017년 Google에서 발표한..."
```

---

## 2. 보안 시스템

### Q2-1. SQL Injection 방어는 어떻게 하나요?

**A:** **3단계 검증 시스템**으로 방어합니다.

**1단계: 화이트리스트 검증**
```python
ALLOWED_TABLES = {"papers"}  # papers만 허용
ALLOWED_COLUMNS = {
    "paper_id", "title", "authors", ...
}

# papers 외 테이블 참조 시 차단
if tname not in ALLOWED_TABLES:
    raise ValueError(f"허용되지 않은 테이블: {tname}")
```

**2단계: 금지 패턴 필터링**
```python
_FORBIDDEN_PATTERNS = [
    r"\bdrop\b",      # DROP 명령 금지
    r"\balter\b",     # ALTER 명령 금지
    r"\binsert\b",    # INSERT 명령 금지
    r"\bupdate\b",    # UPDATE 명령 금지
    r"\bdelete\b",    # DELETE 명령 금지
    r"\bgrant\b",     # GRANT 명령 금지
    r";\s*--",        # SQL 주석 공격 금지
    r"/\*", r"\*/"    # 주석 블록 금지
]

for pat in _FORBIDDEN_PATTERNS:
    if re.search(pat, sql_lower):
        raise ValueError("금지된 SQL 패턴 감지")
```

**3단계: 읽기 전용 검증**
```python
_READONLY_START = {"select", "with"}

first_word = sql.split()[0].lower()
if first_word not in _READONLY_START:
    raise ValueError("SELECT/WITH 쿼리만 허용")
```

**공격 예시 (차단됨):**
```sql
-- 시도: DROP TABLE 공격
사용자: "2024년 논문 개수; DROP TABLE papers;"
→ 검증: 금지 패턴 "\bdrop\b" 감지
→ 결과: ValueError 발생, 실행 차단

-- 시도: 다른 테이블 접근
사용자: "users 테이블 조회해줘"
→ 검증: "users" not in ALLOWED_TABLES
→ 결과: ValueError 발생, 실행 차단

-- 시도: UPDATE 공격
사용자: "논문 제목 수정해줘"
→ LLM 생성: UPDATE papers SET title=...
→ 검증: 금지 패턴 "\bupdate\b" 감지
→ 결과: ValueError 발생, 실행 차단
```

---

### Q2-2. 왜 SELECT만 허용하나요?

**A:** **데이터 무결성 보호**를 위해서입니다.

**허용:**
- `SELECT`: 데이터 조회 (안전)
- `WITH`: CTE (Common Table Expression, 읽기 전용)

**금지:**
- `INSERT`: 데이터 추가 (의도치 않은 데이터 생성)
- `UPDATE`: 데이터 수정 (원본 데이터 훼손)
- `DELETE`: 데이터 삭제 (복구 불가능)
- `DROP`, `ALTER`: 스키마 변경 (시스템 파괴)
- `GRANT`, `REVOKE`: 권한 변경 (보안 위험)

**예시:**
```sql
-- ✅ 허용
SELECT COUNT(*) FROM papers WHERE category='cs.CL';

-- ✅ 허용 (CTE 사용)
WITH recent_papers AS (
    SELECT * FROM papers WHERE publish_date >= '2023-01-01'
)
SELECT category, COUNT(*) FROM recent_papers GROUP BY category;

-- ❌ 금지
UPDATE papers SET citation_count = 999;

-- ❌ 금지
DELETE FROM papers WHERE paper_id = 123;

-- ❌ 금지
DROP TABLE papers;
```

---

### Q2-3. LIMIT 100은 왜 자동으로 붙나요?

**A:** **대용량 결과로 인한 성능 저하 방지**입니다.

**자동 LIMIT 로직:**
```python
def _ensure_limit(sql: str) -> str:
    # 집계 함수가 있으면 LIMIT 불필요
    if any(k in sql.lower() for k in ["count(", "avg(", "sum(", "max(", "min("]):
        return sql

    # 이미 LIMIT 있으면 그대로
    if " limit " in sql.lower():
        return sql

    # 그 외 모든 경우 LIMIT 100 추가
    return sql.rstrip(";") + " LIMIT 100;"
```

**예시:**
```sql
-- 집계 쿼리: LIMIT 없음
SELECT COUNT(*) FROM papers;
→ 변경 없음 (결과 1행)

-- 일반 SELECT: LIMIT 100 자동 추가
SELECT title, authors FROM papers;
→ SELECT title, authors FROM papers LIMIT 100;

-- 이미 LIMIT 있음: 변경 없음
SELECT title FROM papers LIMIT 10;
→ 변경 없음

-- ORDER BY도 LIMIT 100 추가
SELECT title, citation_count FROM papers ORDER BY citation_count DESC;
→ SELECT title, citation_count FROM papers ORDER BY citation_count DESC LIMIT 100;
```

**LIMIT 100 이유:**
- 10만 행 이상 반환 방지
- Streamlit UI 성능 보호
- 사용자가 원하면 명시적으로 LIMIT 지정 가능

---

## 3. SQL 생성 과정

### Q3-1. Few-shot 학습이란?

**A:** **LLM에게 예시를 제공하여 올바른 SQL 생성을 유도하는 기법**입니다.

**Few-shot 예시 (5개):**

| 질문 | 생성 SQL |
|------|---------|
| "2024년에 발표된 논문 개수는?" | `SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;` |
| "카테고리별 논문 수를 보여줘" | `SELECT category, COUNT(*) FROM papers GROUP BY category ORDER BY COUNT(*) DESC LIMIT 100;` |
| "2021년 이후 논문의 평균 인용수는?" | `SELECT AVG(citation_count) FROM papers WHERE publish_date >= DATE '2021-01-01';` |
| "AI 관련 논문 중 가장 인용이 많은 건?" | `SELECT title, citation_count FROM papers WHERE category ILIKE '%AI%' ORDER BY citation_count DESC LIMIT 1;` |
| "저자가 3명 이상인 논문은 몇 편?" | `SELECT COUNT(*) FROM papers WHERE array_length(string_to_array(authors, ','), 1) >= 3;` |

**Few-shot 효과:**
- PostgreSQL 문법 학습 (`EXTRACT`, `ILIKE`, `array_length`)
- 테이블/컬럼명 학습 (`papers`, `publish_date`)
- 집계 함수 사용법 학습 (`COUNT`, `AVG`)
- LIMIT 사용 패턴 학습

**프롬프트 구조:**
```python
system_prompt = "You are a careful Text-to-SQL generator..."

few_shot = """
-- Q: 2024년에 발표된 논문 개수는?
SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;

-- Q: 카테고리별 논문 수를 보여줘
SELECT category, COUNT(*) FROM papers GROUP BY category...
"""

user_prompt = "-- Q: 저자가 5명 이상인 논문은?"

# LLM 호출
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=few_shot + "\n\n" + user_prompt)
]
```

---

### Q3-2. SQL 검증 과정은?

**A:** **생성된 SQL을 4단계로 검증**합니다.

**1단계: SQL 추출**
```python
def _extract_sql(text: str) -> str:
    # LLM이 코드펜스로 감싼 경우
    # 입력: "```sql\nSELECT * FROM papers;\n```"
    # 출력: "SELECT * FROM papers;"

    # ```sql ... ``` 패턴 추출
    # ``` ... ``` 패턴 추출
    # 주석 제거
```

**2단계: 금지 패턴 검증**
```python
def _sanitize(sql: str) -> str:
    # DROP, ALTER, INSERT, UPDATE, DELETE 차단
    # papers 외 테이블 차단
    # SELECT/WITH만 허용
```

**3단계: LIMIT 자동 추가**
```python
def _ensure_limit(sql: str) -> str:
    # 집계가 아닌 경우 LIMIT 100 추가
```

**4단계: EXPLAIN 안전성 검사 (선택)**
```python
def _explain_safe(sql: str) -> bool:
    # PostgreSQL EXPLAIN으로 실행 계획 확인
    # 너무 큰 Seq Scan 등 경고 가능
    # 현재는 무조건 통과 (향후 강화 예정)
```

**전체 흐름:**
```python
raw_sql = llm.invoke(messages).content
    ↓
sql_generated = _extract_sql(raw_sql)
    ↓
sql_sanitized = _sanitize(sql_generated)  # 보안 검증
    ↓
sql_ready = _ensure_limit(sql_sanitized)  # LIMIT 추가
    ↓
if _explain_safe(sql_ready):              # 안전성 검사
    execute(sql_ready)
```

---

### Q3-3. 스키마 정보는 어떻게 제공하나요?

**A:** **information_schema에서 실시간으로 스키마를 가져옵니다.**

**스키마 스냅샷 생성:**
```python
def _fetch_schema_snapshot() -> str:
    sql = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema='public'
      AND table_name = ANY(%s)
    ORDER BY table_name, ordinal_position;
    """
    # ALLOWED_TABLES만 조회
    execute(sql, (list(ALLOWED_TABLES),))
```

**결과:**
```
- papers.paper_id :: integer
- papers.title :: text
- papers.authors :: text
- papers.publish_date :: date
- papers.source :: character varying
- papers.url :: text
- papers.category :: character varying
- papers.citation_count :: integer
- papers.abstract :: text
- papers.created_at :: timestamp without time zone
- papers.updated_at :: timestamp without time zone
```

**프롬프트 포함:**
```python
system_prompt = f"""You are a careful Text-to-SQL generator.

Whitelisted schema (public):
{schema}

Only these columns are guaranteed to exist:
papers(paper_id, title, authors, publish_date, ...)
"""
```

**장점:**
- DB 스키마 변경 시 자동 반영
- 정확한 컬럼명/타입 정보 제공
- LLM이 존재하지 않는 컬럼 참조 방지

---

## 4. 사용 예시

### Q4-1. 기본 통계 조회 예시

**예시 1: 연도별 논문 개수**
```python
질문: "2024년에 발표된 논문 개수는?"

생성 SQL:
SELECT COUNT(*) AS paper_count
FROM papers
WHERE EXTRACT(YEAR FROM publish_date) = 2024;

결과:
paper_count
-----------
42
```

**예시 2: 카테고리별 통계**
```python
질문: "카테고리별 논문 수를 보여줘"

생성 SQL:
SELECT category, COUNT(*) AS paper_count
FROM papers
GROUP BY category
ORDER BY paper_count DESC
LIMIT 100;

결과:
category | paper_count
---------|------------
cs.CL    | 25
cs.AI    | 18
cs.CV    | 15
...
```

**예시 3: 평균 인용수**
```python
질문: "2021년 이후 발표된 논문들의 평균 인용수는?"

생성 SQL:
SELECT AVG(citation_count) AS avg_citations
FROM papers
WHERE publish_date >= DATE '2021-01-01';

결과:
avg_citations
-------------
15.3
```

---

### Q4-2. 필터링 조회 예시

**예시 1: ILIKE 패턴 검색**
```python
질문: "AI 관련 논문 중 가장 인용이 많은 건?"

생성 SQL:
SELECT title, citation_count
FROM papers
WHERE category ILIKE '%AI%'
ORDER BY citation_count DESC
LIMIT 1;

결과:
title                                    | citation_count
-----------------------------------------|---------------
Attention is All You Need                | 50000
```

**예시 2: 날짜 범위 필터**
```python
질문: "2023년 1월부터 6월까지 발표된 논문은 몇 편?"

생성 SQL:
SELECT COUNT(*) AS paper_count
FROM papers
WHERE publish_date BETWEEN DATE '2023-01-01' AND DATE '2023-06-30';

결과:
paper_count
-----------
28
```

**예시 3: 복합 조건**
```python
질문: "2023년에 발표된 cs.CL 카테고리 논문 중 인용수 100 이상인 건?"

생성 SQL:
SELECT title, citation_count, publish_date
FROM papers
WHERE EXTRACT(YEAR FROM publish_date) = 2023
  AND category = 'cs.CL'
  AND citation_count >= 100
ORDER BY citation_count DESC
LIMIT 100;
```

---

### Q4-3. 고급 집계 예시

**예시 1: 배열 함수 (저자 수)**
```python
질문: "저자가 3명 이상인 논문은 몇 편이야?"

생성 SQL:
SELECT COUNT(*) AS paper_count
FROM papers
WHERE array_length(string_to_array(authors, ','), 1) >= 3;

결과:
paper_count
-----------
35
```

**예시 2: WITH (CTE) 사용**
```python
질문: "2023년 이후 논문 중 카테고리별 평균 인용수"

생성 SQL:
WITH recent_papers AS (
    SELECT *
    FROM papers
    WHERE publish_date >= DATE '2023-01-01'
)
SELECT category, AVG(citation_count) AS avg_cites
FROM recent_papers
GROUP BY category
ORDER BY avg_cites DESC;
```

**예시 3: EXTRACT 함수 활용**
```python
질문: "월별 논문 발표 추세"

생성 SQL:
SELECT
    EXTRACT(YEAR FROM publish_date) AS year,
    EXTRACT(MONTH FROM publish_date) AS month,
    COUNT(*) AS paper_count
FROM papers
GROUP BY year, month
ORDER BY year, month;
```

---

## 5. 에러 처리

### Q5-1. SQL 생성 실패 시 어떻게 되나요?

**A:** **에러 메시지와 함께 생성된 SQL을 표시**합니다.

**에러 응답 형식:**
```markdown
**질문**: 2024년 논문 개수

**생성된 SQL(검증 전)**:
```sql
SELECT COUNT(*) FROM users;  -- 잘못된 테이블
```

요청을 처리하는 중 오류가 발생했습니다:
```
ValueError: 허용되지 않은 테이블 참조: users
```
```

**로그 저장:**
```python
_log_query(
    user_query="2024년 논문 개수",
    generated_sql="SELECT COUNT(*) FROM users;",
    response_text=error_message,
    success=False,
    response_time_ms=500,
    error_message="ValueError: 허용되지 않은 테이블..."
)
```

---

### Q5-2. 일반적인 에러 종류는?

**A:**

**1. 허용되지 않은 테이블 참조**
```
질문: "users 테이블 조회"
에러: ValueError: 허용되지 않은 테이블 참조: users
원인: ALLOWED_TABLES에 'users' 없음
```

**2. 금지된 SQL 패턴**
```
질문: "논문 데이터 삭제해줘"
생성 SQL: DELETE FROM papers WHERE...
에러: ValueError: 금지된 SQL 패턴이 감지되었습니다.
원인: DELETE 명령 차단
```

**3. 읽기 전용 위반**
```
질문: "논문 제목 수정해줘"
생성 SQL: UPDATE papers SET title=...
에러: ValueError: SELECT/WITH 쿼리만 허용됩니다.
원인: UPDATE는 _READONLY_START에 없음
```

**4. 존재하지 않는 컬럼**
```
질문: "논문의 저자 나이 조회"
생성 SQL: SELECT author_age FROM papers;
실행 에러: column "author_age" does not exist
원인: papers 테이블에 author_age 컬럼 없음
```

**5. 잘못된 SQL 문법**
```
질문: "논문 개수"
생성 SQL: SELECT COUNT FROM papers;  -- (*) 누락
실행 에러: syntax error at or near "FROM"
원인: LLM이 잘못된 SQL 생성
```

---

### Q5-3. 에러를 줄이는 방법은?

**A:**

**1. 명확한 질문**
```
❌ "논문 조회"  → 모호함
✅ "2024년 논문 개수는?"  → 명확함

❌ "저자 정보"  → 무엇을 원하는지 불명확
✅ "저자가 3명 이상인 논문은 몇 편?"  → 명확함
```

**2. 테이블/컬럼명 힌트 제공**
```
❌ "최근 논문"  → "최근"이 모호
✅ "2023년 이후 발표된 논문"  → publish_date 사용 유도

❌ "인기 있는 논문"  → "인기"가 모호
✅ "인용수가 많은 논문"  → citation_count 사용 유도
```

**3. 집계 함수 명시**
```
❌ "논문 정보"  → SELECT * (LIMIT 100 붙음)
✅ "논문 개수는?"  → COUNT(*) (LIMIT 불필요)
```

---

## 6. 로깅 시스템

### Q6-1. query_logs 테이블이란?

**A:** **모든 Text-to-SQL 요청을 기록하는 로그 테이블**입니다.

**스키마:**
```sql
CREATE TABLE query_logs (
    log_id SERIAL PRIMARY KEY,
    user_query TEXT NOT NULL,       -- 사용자 질문 (필수)
    difficulty_mode VARCHAR(20),    -- 난이도 (현재 미사용, NULL 저장)
    tool_used VARCHAR(50),          -- 도구명 (text2sql)
    response TEXT,                  -- 응답 내용 (코드에서 첫 2000자만 저장)
    response_time_ms INTEGER,       -- 응답 시간 (밀리초)
    success BOOLEAN,                -- 성공 여부
    error_message TEXT,             -- 에러 메시지 (실패 시)
    created_at TIMESTAMP DEFAULT NOW()  -- 생성 시간
);
```

**로그 저장 예시:**
```sql
INSERT INTO query_logs VALUES (
    DEFAULT,
    '2024년 논문 개수는?',
    NULL,
    'text2sql',
    '**질문**: 2024년 논문 개수는?\n**생성된 SQL**:\n...',
    350,  -- 350ms
    TRUE,
    NULL,
    DEFAULT
);
```

---

### Q6-2. 로그는 언제 저장되나요?

**A:** **SQL 실행 성공/실패 여부와 무관하게 항상 저장**됩니다.

**성공 시:**
```python
_log_query(
    user_query=user_question,
    generated_sql=sql_ready,
    response_text=out[:2000],  # 첫 2000자만
    success=True,
    response_time_ms=elapsed,
    error_message=None
)
```

**실패 시:**
```python
_log_query(
    user_query=user_question,
    generated_sql=sql_generated,  # 검증 전 SQL
    response_text=error_message,
    success=False,
    response_time_ms=elapsed,
    error_message=str(e)
)
```

**로그 저장 실패:**
- 로그 저장 실패는 무시됨 (서비스 흐름 방해 안 함)
- `try-except`로 감싸서 에러 발생해도 계속 진행

---

### Q6-3. 로그 분석 쿼리 예시

**1. 성공률 조회**
```sql
SELECT
    COUNT(*) AS total_queries,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS success_count,
    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate
FROM query_logs
WHERE tool_used = 'text2sql';
```

**2. 평균 응답 시간**
```sql
SELECT
    AVG(response_time_ms) AS avg_ms,
    MIN(response_time_ms) AS min_ms,
    MAX(response_time_ms) AS max_ms
FROM query_logs
WHERE tool_used = 'text2sql' AND success = TRUE;
```

**3. 자주 실패하는 질문**
```sql
SELECT
    user_query,
    COUNT(*) AS failure_count,
    MAX(error_message) AS last_error
FROM query_logs
WHERE tool_used = 'text2sql' AND success = FALSE
GROUP BY user_query
ORDER BY failure_count DESC
LIMIT 10;
```

**4. 최근 24시간 사용량**
```sql
SELECT
    DATE_TRUNC('hour', created_at) AS hour,
    COUNT(*) AS query_count
FROM query_logs
WHERE tool_used = 'text2sql'
  AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;
```

**5. 느린 쿼리 찾기**
```sql
SELECT
    user_query,
    response_time_ms,
    created_at
FROM query_logs
WHERE tool_used = 'text2sql'
  AND response_time_ms > 3000  -- 3초 이상
ORDER BY response_time_ms DESC
LIMIT 10;
```

---

## 7. 트러블슈팅

### Q7-1. "relation papers does not exist" 에러

**원인:** papers 테이블이 없습니다.

**해결:**
```bash
# PostgreSQL 연결 확인
psql $DATABASE_URL -c "\dt"

# papers 테이블 생성 (스크립트 실행)
python scripts/setup_database.py
```

**테이블 생성 SQL:**
```sql
CREATE TABLE papers (
    paper_id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,        -- 논문 제목 (최대 500자, 필수)
    authors TEXT,                       -- 저자 목록
    publish_date DATE,                  -- 발행일
    source VARCHAR(100),                -- 출처 (최대 100자)
    url TEXT UNIQUE,                    -- 논문 URL (중복 불가)
    category VARCHAR(100),              -- 카테고리 (최대 100자)
    citation_count INT DEFAULT 0,       -- 인용 횟수 (기본값 0)
    abstract TEXT,                      -- 논문 초록
    created_at TIMESTAMP DEFAULT NOW(), -- DB 생성일 (자동)
    updated_at TIMESTAMP DEFAULT NOW()  -- DB 수정일 (자동)
);
```

---

### Q7-2. "Solar API key not found" 에러

**원인:** Solar API 키가 설정되지 않았습니다.

**해결:**
```bash
# .env 파일에 추가
echo "SOLAR_API_KEY=your-solar-api-key" >> .env

# 환경변수 확인
source .env
echo $SOLAR_API_KEY
```

**대안 (GPT 사용):**
```yaml
# configs/model_config.yaml
text2sql:
  provider: openai
  model: gpt-5               # GPT-5 사용 (더 높은 정확도)
  temperature: 0.0
  max_retries: 2             # 재시도 횟수
```

---

### Q7-3. SQL 생성은 되는데 결과가 이상함

**원인:** LLM이 잘못된 SQL을 생성했지만 검증을 통과함.

**디버깅:**

**1. 생성된 SQL 확인**
```python
# text2sql 응답에서 SQL 부분 확인
**생성된 SQL**:
```sql
SELECT COUNT(*) FROM papers WHERE year=2024;  -- 잘못됨
```
```

**2. 수동으로 SQL 실행**
```sql
-- PostgreSQL에서 직접 실행
psql $DATABASE_URL

SELECT COUNT(*) FROM papers WHERE year=2024;
-- ERROR: column "year" does not exist

-- 올바른 SQL
SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
```

**3. Few-shot 예시 추가**
```python
# src/tools/text2sql.py
_FEW_SHOTS.append((
    "2024년 논문 개수는?",
    "SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;"
))
```

---

### Q7-4. "금지된 SQL 패턴 감지" 에러가 잘못 발생

**원인:** False Positive - 정상 SQL인데 금지 패턴으로 오인.

**예시:**
```python
질문: "논문 제목에 'drop'이 포함된 논문"
생성 SQL: SELECT * FROM papers WHERE title ILIKE '%drop%';
에러: "금지된 SQL 패턴 감지" (title에 'drop' 있음)
```

**해결:**

**1. 패턴 수정 (단어 경계 추가)**
```python
# 기존
r"\bdrop\b"  # 단어 경계 있음 (OK)

# 문제 케이스
r"drop"  # 단어 경계 없으면 '%drop%'도 걸림
```

**2. 컨텍스트 검증 강화**
```python
# WHERE 절 내부의 문자열 리터럴은 제외
def _sanitize(sql):
    # 문자열 리터럴 제거 후 검증
    sql_without_strings = re.sub(r"'[^']*'", '', sql)
    for pat in _FORBIDDEN_PATTERNS:
        if re.search(pat, sql_without_strings):
            raise ValueError(...)
```

---

### Q7-5. 응답 시간이 너무 느림 (5초 이상)

**원인:**
1. Solar API 응답 느림
2. PostgreSQL 쿼리 느림
3. 복잡한 SQL (대용량 집계)

**해결:**

**1. Solar API 타임아웃 설정**
```python
# src/llm/client.py
llm_client = LLMClient(
    provider="solar",
    model="solar-pro2",
    temperature=0.0,
    timeout=5  # 5초 타임아웃
)
```

**2. PostgreSQL 인덱스 추가**
```sql
-- publish_date 인덱스
CREATE INDEX idx_papers_publish_date ON papers(publish_date);

-- category 인덱스
CREATE INDEX idx_papers_category ON papers(category);

-- citation_count 인덱스 (정렬용)
CREATE INDEX idx_papers_citation_count ON papers(citation_count DESC);
```

**3. EXPLAIN으로 쿼리 분석**
```sql
EXPLAIN ANALYZE
SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;

-- Seq Scan이 나오면 인덱스 추가 필요
-- Index Scan이 나오면 최적화됨
```

---

## 8. 고급 활용

### Q8-1. query_logs를 Text-to-SQL로 조회할 수 있나요?

**A:** 현재는 불가능하지만, **향후 확장 예정**입니다.

**현재:**
```python
ALLOWED_TABLES = {"papers"}  # papers만 허용
```

**향후 (query_logs 추가):**
```python
ALLOWED_TABLES = {"papers", "query_logs"}
```

**확장 후 가능한 질문:**
```
"오늘 Text-to-SQL 사용 횟수는?"
→ SELECT COUNT(*) FROM query_logs
  WHERE tool_used='text2sql'
    AND DATE(created_at) = CURRENT_DATE;

"가장 많이 실패한 질문은?"
→ SELECT user_query, COUNT(*) as fail_count
  FROM query_logs
  WHERE success=FALSE
  GROUP BY user_query
  ORDER BY fail_count DESC
  LIMIT 10;
```

---

### Q8-2. 복잡한 JOIN 쿼리도 생성할 수 있나요?

**A:** **단순 JOIN은 가능하지만, 복잡한 JOIN은 정확도가 떨어집니다.**

**가능한 JOIN (단순):**
```sql
-- 향후 glossary 테이블 추가 시
질문: "논문에서 자주 언급되는 용어 Top 5"

생성 SQL:
SELECT g.term, COUNT(p.paper_id) AS mention_count
FROM glossary g
JOIN papers p ON g.paper_id = p.paper_id
GROUP BY g.term
ORDER BY mention_count DESC
LIMIT 5;
```

**어려운 JOIN (복잡):**
```sql
-- 3개 이상 테이블 JOIN
-- 서브쿼리 포함 JOIN
-- Self JOIN
```

**권장:**
- 단일 테이블 쿼리 위주 사용
- 복잡한 분석은 직접 SQL 작성
- BI 도구 (Metabase, Superset) 병행 사용

---

### Q8-3. Temperature를 높이면 더 창의적인 SQL 생성되나요?

**A:** **아니오. Text-to-SQL은 temperature=0.0이 최적**입니다.

**Temperature 효과:**

| Temperature | SQL 생성 품질 | 이유 |
|-------------|--------------|------|
| **0.0 (권장)** | ⭐⭐⭐ 일관됨 | 동일 질문 → 동일 SQL (재현성) |
| 0.3 | ⭐⭐ 중간 | 가끔 다른 SQL 생성 |
| 0.7 | ⭐ 불안정 | 잘못된 SQL 생성 확률 높음 |
| 1.0 | ❌ 사용 불가 | 문법 오류 빈번 |

**예시 (temperature=0.0):**
```
질문: "2024년 논문 개수"
1회: SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
2회: SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
3회: SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
→ 완전 동일 (재현성 100%)
```

**예시 (temperature=0.7):**
```
질문: "2024년 논문 개수"
1회: SELECT COUNT(*) FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;
2회: SELECT COUNT(*) FROM papers WHERE year=2024;  -- 잘못됨
3회: SELECT COUNT(*) AS count FROM papers WHERE publish_date LIKE '2024%';
→ 매번 다름 (재현성 낮음)
```

---

### Q8-4. Text-to-SQL 결과를 파일로 저장하려면?

**A:** **save_file 도구와 함께 사용**해야 하지만, 현재는 수동 저장만 가능합니다.

**현재 (수동 저장):**
```python
# Text-to-SQL 실행
result = text2sql("2024년 논문 개수")

# 결과 복사 후 파일 저장
exp_manager.save_output("query_result.md", result)
```

**향후 (도구 체이닝):**
```
질문: "2024년 논문 개수 조회하고 파일로 저장해줘"
    ↓
Router: [text2sql, save_file] 선택
    ↓
text2sql 실행 → 결과 생성
    ↓
save_file 실행 → 파일 저장
    ↓
"query_result.md 파일로 저장되었습니다."
```

---

### Q8-5. Text-to-SQL 프롬프트를 커스터마이징하려면?

**A:** `src/tools/text2sql.py`의 `_SYS_PROMPT`와 `_FEW_SHOTS`를 수정합니다.

**시스템 프롬프트 수정:**
```python
# src/tools/text2sql.py

_SYS_PROMPT = """You are a PostgreSQL expert.

Custom Rules:
- 한국어 질문도 영어 컬럼명으로 변환
- 날짜 형식은 항상 YYYY-MM-DD
- 집계 결과는 별칭(alias) 사용 필수

Schema:
{schema}
"""
```

**Few-shot 예시 추가:**
```python
_FEW_SHOTS.append((
    "인용수 상위 10개 논문의 카테고리 분포",
    """
    WITH top_papers AS (
        SELECT * FROM papers
        ORDER BY citation_count DESC
        LIMIT 10
    )
    SELECT category, COUNT(*) as count
    FROM top_papers
    GROUP BY category;
    """
))
```

**난이도별 프롬프트 (향후):**
```python
# Easy 모드: 단순 집계만
# Hard 모드: 복잡한 JOIN, 서브쿼리 허용
```

---

## 참고 자료

### 관련 문서
- [09_도구_시스템.md](../modularization/09_도구_시스템.md) - Text-to-SQL 도구 설명
- [08_데이터베이스_통합_가이드.md](../modularization/08_데이터베이스_통합_가이드.md)
- [04_LLM_클라이언트.md](../modularization/04_LLM_클라이언트.md)

### 구현 파일
- `src/tools/text2sql.py` - Text-to-SQL 도구 메인 파일
- `src/database/db.py` - PostgreSQL 연결 풀
- `configs/model_config.yaml` - Text-to-SQL 모델 설정

### 외부 자료
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [Text-to-SQL 논문](https://arxiv.org/abs/2204.00498) - Survey
- [Few-shot Learning](https://arxiv.org/abs/2005.14165) - GPT-3 논문

---

## 작성자
- **최현화[팀장]** (Text-to-SQL 시스템 구현 및 문서화)
