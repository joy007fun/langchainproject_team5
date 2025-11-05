from __future__ import annotations
import os
import re
import time
import json
import psycopg2
import psycopg2.extras
from typing import List, Tuple, Any, Optional

from langchain.tools import tool
from dotenv import load_dotenv

# LLMClient import 추가 (config 기반)
from src.utils.config_loader import get_model_config
from src.llm.client import LLMClient
from src.prompts import get_tool_prompt

load_dotenv()
# ==============================================================================
# 📘 모듈 목적 (Text-to-SQL for PostgreSQL)
# ------------------------------------------------------------------------------
# - 자연어 질문 → 안전한 SELECT/WITH 쿼리 생성 → 실행 → Markdown 표로 반환
# - 접근 허용 테이블/컬럼(화이트리스트)만 사용하여 보안·안정성 강화
# - 집계가 아닌 결과는 기본 LIMIT 100 부여
# - 금지 패턴(DDL/DML/권한 명령 등) 필터링 + 간단한 EXPLAIN 안전 점검
#
# 📌 환경 변수(필수/선택)
#   - POSTGRES_HOST/PORT/USER/PASSWORD/DB      : DB 접속 정보
#   - SOLAR_API_KEY 또는 OPENAI_API_KEY       : LLM API Key (config에서 지정된 provider에 따라)
#   ⚠️ configs/model_config.yaml의 text2sql 섹션에서 모델 설정
#
# 🔎 사용 예시
#   >>> from text2sql import text2sql
#   >>> print(text2sql.run("2024년에 발표된 논문 개수는?"))
#
# ⚠️ 주의
#   - 현재는 public.papers 테이블만 허용(ALLOWED_TABLES/ALLOWED_COLUMNS)
#   - INSERT/UPDATE/DELETE/DDL 등은 철저히 차단됩니다.
# ==============================================================================
 


# ───────────────────────────────────────────────────────────────────────────────
# DB 연결 유틸
# ───────────────────────────────────────────────────────────────────────────────
def _get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
    )


# ───────────────────────────────────────────────────────────────────────────────
# 스키마 스냅샷
# ───────────────────────────────────────────────────────────────────────────────
ALLOWED_TABLES = {"papers"}  # 현재 버전은 papers만 허용
ALLOWED_COLUMNS = {
    "paper_id", "title", "authors", "publish_date",
    "source", "url", "category", "citation_count",
    "abstract", "created_at", "updated_at",
}


def _fetch_schema_snapshot() -> str:
    """
    information_schema에서 허용 테이블/컬럼만 스냅샷 텍스트 생성
    """
    q = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema='public'
      AND table_name = ANY(%s)
    ORDER BY table_name, ordinal_position;
    """
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, (list(ALLOWED_TABLES),))
        rows = cur.fetchall()

    lines = []
    for t, c, dt in rows:
        if c in ALLOWED_COLUMNS:
            lines.append(f"- {t}.{c} :: {dt}")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────────
# 프롬프트 설정
# ───────────────────────────────────────────────────────────────────────────────
_SYS_PROMPT = """You are a careful Text-to-SQL generator for PostgreSQL.

Rules:
- Output ONLY a single SQL query with no extra prose or comments.
- SELECT / WITH (CTE) only. No writes (INSERT/UPDATE/DELETE), no DDL (ALTER/DROP/CREATE), no GRANT/REVOKE.
- Use only the whitelisted table and columns below.
- Prefer COUNT/SUM/AVG/MAX/MIN for numeric answers.
- For year filters, use EXTRACT(YEAR FROM publish_date).
- For keyword search in text columns, use ILIKE with %...%.
- IMPORTANT: When combining AND/OR in WHERE clause, use parentheses to group OR conditions. Example: WHERE date >= '2022-01-01' AND (field1 ILIKE '%keyword%' OR field2 ILIKE '%keyword%')
- Add LIMIT 100 when returning rows (non-aggregate).
- Do NOT reference tables not listed below; do NOT call undefined functions.
- Use single semicolon at the end.

Whitelisted schema (public):
{schema}

Only these columns are guaranteed to exist:
papers(paper_id, title, authors, publish_date, source, url, category, citation_count, abstract, created_at, updated_at)
"""

# Few-shot: 실제 스키마에 맞춰 구성
_FEW_SHOTS = [
    (
        "2024년에 발표된 논문 개수는?",
        "SELECT COUNT(*) AS paper_count FROM papers WHERE EXTRACT(YEAR FROM publish_date)=2024;"
    ),
    (
        "카테고리별 논문 수를 보여줘",
        "SELECT category, COUNT(*) AS paper_count FROM papers GROUP BY category ORDER BY paper_count DESC LIMIT 100;"
    ),
    (
        "2021년 이후 발표된 논문들의 평균 인용수는?",
        "SELECT AVG(citation_count) AS avg_citations FROM papers WHERE publish_date >= DATE '2021-01-01';"
    ),
    (
        "AI 관련 논문 중 가장 인용이 많은 건?",
        "SELECT title, citation_count FROM papers WHERE category ILIKE '%AI%' ORDER BY citation_count DESC LIMIT 1;"
    ),
    (
        "저자가 3명 이상인 논문은 몇 편이야?",
        "SELECT COUNT(*) AS paper_count FROM papers WHERE array_length(string_to_array(authors, ','), 1) >= 3;"
    ),
]


def _fewshot_block() -> str:
    parts = []
    for q, s in _FEW_SHOTS:
        parts.append(f"-- Q: {q}\n{s}")
    return "\n\n".join(parts)


# ───────────────────────────────────────────────────────────────────────────────
# 생성 SQL 정리/검증
# ───────────────────────────────────────────────────────────────────────────────
_FORBIDDEN_PATTERNS = [
    r"\bdrop\b", r"\balter\b", r"\btruncate\b", r"\binsert\b",
    r"\bupdate\b", r"\bdelete\b", r"\bgrant\b", r"\brevoke\b",
    r"\bcopy\b", r"\bcreate\b", r";\s*--", r"/\*", r"\*/"
]
_READONLY_START = {"select", "with"}


def _extract_sql(text: str) -> str:
    """LLM이 코드펜스 등을 포함해도 SQL만 추출"""
    s = text.strip()
    # ```sql ... ```
    m = re.search(r"```sql(.*?)```", s, flags=re.I | re.S)
    if m:
        s = m.group(1).strip()
    # ``` ... ```
    m = re.search(r"```(.*?)```", s, flags=re.S)
    if m:
        s = m.group(1).strip()
    # 첫 줄에 주석/문장 제거 시도
    # 여러 줄 중 SQL로 보이는 첫 세미콜론 전까지
    if s.count(";") > 1:
        s = s.split(";")[0] + ";"
    return s

def _find_tables_outside_parens(sql_lower: str) -> set:
    """
    괄호 밖에서만 FROM/JOIN을 인식하여 테이블명을 추출합니다.
    예: EXTRACT(YEAR FROM publish_date) 내부의 'from'은 무시됩니다.
    """
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[(),]", sql_lower)
    paren = 0
    tables = set()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "(":
            paren += 1
        elif tok == ")":
            paren = max(0, paren - 1)
        else:
            if paren == 0 and tok in {"from", "join"}:
                # 다음 토큰들이 (옵션) schema.table 형태일 수 있음
                j = i + 1
                # 공백 토큰은 정규식에서 이미 제거됨
                if j < len(tokens):
                    # public.schema 같은 prefix 무시
                    tname = tokens[j]
                    # 쉼표/괄호/예약어는 테이블 아님
                    if re.match(r"[a-z_][a-z0-9_]*", tname):
                        tables.add(tname)
            # else: 괄호 안의 from/join은 무시
        i += 1
    return tables

def _sanitize(sql: str) -> str:
    s = sql.strip()
    if not s.endswith(";"):
        s += ";"
    s = s.rstrip(";")  # 일단 끝 세미콜론 제거 후 점검 → 다시 1개 붙임
    low = s.lower()

    # 금지 패턴
    for pat in _FORBIDDEN_PATTERNS:
        if re.search(pat, low):
            raise ValueError("금지된 SQL 패턴이 감지되었습니다.")

    # 읽기 전용 동사만 허용
    first = re.split(r"\s+", low, maxsplit=1)[0]
    if first not in _READONLY_START:
        raise ValueError("SELECT/WITH 쿼리만 허용됩니다.")

    # papers 테이블만 허용
    # FROM/JOIN 근처에 등장하는 테이블 토큰 검증(간단 버전)
    tbl_tokens = re.findall(r"\bfrom\s+([a-zA-Z0-9_\.]+)|\bjoin\s+([a-zA-Z0-9_\.]+)", low)
    flat_tbls = _find_tables_outside_parens(low)
    for t in flat_tbls:
        tname = t.split(".")[-1]
        if tname not in ALLOWED_TABLES:
            raise ValueError(f"허용되지 않은 테이블 참조: {tname}")

    # 허용 컬럼 힌트(강제는 아님): SELECT 목록의 토큰 중 명백한 외부 식별자 경고
    # (실서비스에서는 실제 파서/카탈로그를 권장)
    return s + ";"  # 단일 세미콜론 강제


def _ensure_limit(sql: str) -> str:
    """집계가 아닌 경우 LIMIT 100 자동 부여"""
    low = sql.lower()
    if any(k in low for k in ["count(", "avg(", "sum(", "max(", "min("]):
        return sql
    if " limit " in low:
        return sql
    # ORDER BY가 있든 없든 마지막에 LIMIT 추가
    return sql.rstrip(";") + " LIMIT 100;"

def _explain_safe(sql: str) -> bool:
    """
    간단한 실행계획 사전점검: 너무 큰 Seq Scan 등을 완화(프로덕션에서는 임계값/통계 기반 권장)
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("EXPLAIN " + sql)
            plan_rows = cur.fetchall()
            plan_text = "\n".join(r[0] for r in plan_rows)
            # 데모용으로 무조건 통과(원하면 여기서 rows= 추정치 파싱해 임계치 차단)
            return True
    except Exception:
        return False


# ───────────────────────────────────────────────────────────────────────────────
# 실행 & 포맷
# ───────────────────────────────────────────────────────────────────────────────
def _run_query(sql: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    with _get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
        return cols, rows

def _to_markdown_table(cols: List[str], rows: List[Tuple[Any, ...]]) -> str:
    if not rows:
        return "_결과가 없습니다._"
    header = " | ".join(cols)
    sep = " | ".join(["---"] * len(cols))
    body_lines = []
    for r in rows:
        body_lines.append(" | ".join("" if v is None else str(v) for v in r))
    return f"{header}\n{sep}\n" + "\n".join(body_lines)



# ───────────────────────────────────────────────────────────────────────────────
# 로깅
# ───────────────────────────────────────────────────────────────────────────────
def _log_query(user_query: str,
               generated_sql: str,
               response_text: str,
               success: bool,
               response_time_ms: int,
               error_message: Optional[str] = None) -> None:
    """
    query_logs 테이블에 기록 (스키마: log_id, user_query, difficulty_mode, tool_used, response,
                           response_time_ms, success, error_message, created_at)
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_logs (user_query, difficulty_mode, tool_used, response,
                                        response_time_ms, success, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    user_query,
                    None,  # difficulty_mode는 현재 미사용
                    "text2sql",
                    response_text,
                    response_time_ms,
                    success,
                    error_message,
                ),
            )
            conn.commit()
    except Exception:
        # 로깅 실패는 무시(서비스 흐름 방해 X)
        pass



# ───────────────────────────────────────────────────────────────────────────────
# 메인 Tool
# ───────────────────────────────────────────────────────────────────────────────
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

    사용 예시)
      - "2024년에 발표된 논문 개수는?"
      - "카테고리별 논문 수를 보여줘"
      - "AI 관련 논문 중 가장 인용이 많은 건?"
    """
    t0 = time.time()

    # ==================== config에서 text2sql 모델 설정 읽기 ==================== #
    try:
        model_config = get_model_config()
        text2sql_config = model_config.get("text2sql", {})
        provider = text2sql_config.get("provider", "solar")
        model = text2sql_config.get("model", "solar-pro2")
        temperature = text2sql_config.get("temperature", 0.0)
    except Exception:
        # config 로드 실패 시 기본값
        provider = "solar"
        model = "solar-pro2"
        temperature = 0.0

    # LLMClient 생성 (config 기반)
    llm_client = LLMClient(provider=provider, model=model, temperature=temperature)

    schema = _fetch_schema_snapshot()
    sys_prompt = _SYS_PROMPT.format(schema=schema)
    few_shot = _fewshot_block()
    user_block = f"-- Q: {user_question}\n-- Generate ONE SQL ONLY."

    # LLM 호출
    from langchain.schema import SystemMessage, HumanMessage
    raw = llm_client.llm.invoke(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=few_shot + "\n\n" + user_block),
        ]
    ).content

    # LLM 응답 로깅 (선택적)
    # tool_logger가 필요한 경우 여기서 Logger 초기화 가능
    # from src.utils.logger import Logger
    # tool_logger = Logger("logs/text2sql.log")

    # SQL 추출/검증/보정
    sql_generated = _extract_sql(raw)
    try:
        sql_sanitized = _sanitize(sql_generated)
        sql_ready = _ensure_limit(sql_sanitized)
        if not _explain_safe(sql_ready):
            raise ValueError("실행 계획 검증에 실패했습니다.")
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

        elapsed = int((time.time() - t0) * 1000)

        # 로그 저장(응답 일부만 저장하여 크기 제한)
        _log_query(
            user_query=user_question,
            generated_sql=sql_ready,
            response_text=out[:2000],
            success=True,
            response_time_ms=elapsed,
        )
        return out

    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        err = f"{type(e).__name__}: {str(e)}"
        # 에러 로그
        _log_query(
            user_query=user_question,
            generated_sql=sql_generated,
            response_text=err,
            success=False,
            response_time_ms=elapsed,
            error_message=err,
        )
        return (
            f"**질문**: {user_question}\n\n"
            f"**생성된 SQL(검증 전)**:\n```sql\n{sql_generated}\n```\n"
            f"요청을 처리하는 중 오류가 발생했습니다:\n```\n{err}\n```"
        )


# ───────────────────────────────────────────────────────────────────────────────
# 로컬 테스트용 진입점(선택)
# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 간단 수동 테스트
    q = "AI 관련 논문 중 가장 인용이 많은 건?"
    print(text2sql.run(q))

