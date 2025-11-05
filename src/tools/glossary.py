# ==========================================
# 📘 Phase 3: 용어집 시스템 구현
# 📍 Step 5: 용어집 도구(@tool) + 하이브리드 검색 + Agent 노드 통합
# ------------------------------------------
# - @tool: search_glossary (hybrid/sql/vector)
# - PostgreSQL(ILIKE/필터) + PGVector(유사도) 병합
# - 난이도 모드(easy/hard/auto)로 설명 선택
# - Agent 노드 통합: glossary_node
# ==========================================

# ------------------------- 표준 라이브러리 ------------------------- #
import os
from typing import Any, Dict, List, Optional, Tuple

# ------------------------- 서드파티 라이브러리 ------------------------- #
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector

# ------------------------- 프로젝트 모듈 ------------------------- #
from src.utils.config_loader import get_postgres_connection_string, get_db_config
from src.prompts import get_tool_prompt
from src.llm.client import LLMClient
from langchain.schema import SystemMessage, HumanMessage


# ==================== 용어 추출 유틸리티 ==================== #

def _extract_term_from_question(question: str) -> str:
    """
    질문에서 핵심 용어 추출

    Args:
        question: 사용자 질문 (예: "BLEU Score가 뭐야?")

    Returns:
        추출된 용어 (예: "BLEU Score")

    처리 규칙:
    - "가 뭐야", "이 뭐야", "는 뭐야" 등 조사 제거
    - 물음표 제거
    - 양쪽 공백 제거
    """
    import re

    # 원본 보존
    term = question.strip()

    # 한국어 질문 패턴 제거 (순서 중요: 긴 패턴부터 매칭)
    patterns = [
        r'에\s*대해(서)?\s*설명해[줘주세요]*\??',
        r'에\s*대해(서)?\s*알려[줘주세요]*\??',
        r'[이가]\s*무엇인가요?\??',
        r'[은는]\s*무엇인가요?\??',
        r'[이가]\s*뭐야\??',
        r'[은는]\s*뭐야\??',
        r'[을를]\s*설명해[줘주세요]*\??',
        r'[을를]\s*알려[줘주세요]*\??',
        r'\s*뭐야\??',
        r'\s*정의\??',
        r'\s*의미\??',
    ]

    for pattern in patterns:
        term = re.sub(pattern, '', term, flags=re.IGNORECASE | re.UNICODE)

    # 물음표 제거
    term = term.replace('?', '').replace('？', '')

    # 양쪽 공백 제거
    term = term.strip()

    return term


# ==================== 환경/커넥션 유틸리티 ==================== #

def _env(primary: str, alt: str, default: Optional[str] = None) -> Optional[str]:
    """
    환경변수 읽기 헬퍼 함수

    Args:
        primary: 우선순위 환경변수명
        alt: 대체 환경변수명
        default: 기본값

    Returns:
        환경변수 값
    """
    return os.getenv(primary) or os.getenv(alt) or default


def _pg_conn_str() -> str:
    """
    PostgreSQL 연결 문자열 생성

    configs/db_config.yaml 설정을 우선 사용하고,
    없으면 환경변수로 폴백

    Returns:
        PostgreSQL 연결 문자열
    """
    try:
        # configs/db_config.yaml 사용 (권장)
        return get_postgres_connection_string()
    except Exception:
        # 환경변수 폴백
        user = _env("POSTGRES_USER", "PGUSER", "postgres")
        password = _env("POSTGRES_PASSWORD", "PGPASSWORD", "postgres")
        host = _env("POSTGRES_HOST", "PGHOST", "localhost")
        port = _env("POSTGRES_PORT", "PGPORT", "5432")
        db = _env("POSTGRES_DB", "PGDATABASE", "papers")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _get_glossary_vectorstore() -> PGVector:
    """
    용어집 전용 VectorStore 초기화

    Returns:
        PGVector 인스턴스 (glossary_embeddings 컬렉션)
    """
    # PostgreSQL 연결 문자열 가져오기
    conn_str = _pg_conn_str()

    # 컬렉션명 가져오기 (환경변수 또는 기본값)
    collection = os.getenv("PGV_COLLECTION_GLOSSARY", "glossary_embeddings")

    # Embeddings 초기화
    embeddings = OpenAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )

    # PGVector VectorStore 생성
    return PGVector(
        collection_name=collection,
        embeddings=embeddings,
        connection=conn_str,
        use_jsonb=True,
    )


# ==================== SQL 1차 조회 ==================== #

def _fetch_glossary_sql(
    query: Optional[str],
    category: Optional[str],
    difficulty: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """
    PostgreSQL glossary 테이블에서 검색

    Args:
        query: 검색 쿼리 (term, definition, explanation에서 ILIKE 검색)
        category: 카테고리 필터
        difficulty: 난이도 필터 (beginner/intermediate/advanced)
        limit: 최대 결과 수

    Returns:
        검색 결과 리스트 (딕셔너리)
    """
    # PostgreSQL 연결
    conn = psycopg2.connect(_pg_conn_str())

    try:
        # WHERE 절 조건 구성
        where = []
        params: List[Any] = []

        # 쿼리 필터 (term, definition, easy_explanation, hard_explanation에서 검색)
        if query:
            where.append("(term ILIKE %s OR definition ILIKE %s OR easy_explanation ILIKE %s OR hard_explanation ILIKE %s)")
            like = f"%{query}%"
            params.extend([like, like, like, like])

        # 카테고리 필터
        if category:
            where.append("category = %s")
            params.append(category)

        # 난이도 필터
        if difficulty:
            where.append("difficulty_level = %s")
            params.append(difficulty)

        # SQL 쿼리 구성
        sql = """
            SELECT term_id, term, definition, easy_explanation, hard_explanation,
                   category, difficulty_level, related_terms, examples, created_at, updated_at
            FROM glossary
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY term_id ASC LIMIT %s"
        params.append(limit)

        # 쿼리 실행
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    finally:
        # 연결 종료
        conn.close()


# ==================== Vector 2차 조회 ==================== #

def _vector_search_glossary(query: str, k: int) -> List[Tuple[Document, float]]:
    """
    Vector DB에서 용어집 유사도 검색

    Args:
        query: 검색 쿼리
        k: 반환할 문서 수

    Returns:
        (Document, score) 튜플 리스트
    """
    # VectorStore 초기화
    vs = _get_glossary_vectorstore()

    # 유사도 검색 + 점수 반환
    pairs = vs.similarity_search_with_score(query, k=k)

    return pairs


# ==================== 결과 포맷/설명 선택 ==================== #

def _pick_explanation(row: Dict[str, Any], difficulty_mode: str) -> str:
    """
    난이도 모드에 맞는 설명 선택

    Args:
        row: glossary 테이블 행 (딕셔너리)
        difficulty_mode: 'easy' | 'hard' | 'auto'

    Returns:
        선택된 설명 텍스트
    """
    # Easy 모드: easy_explanation 우선
    if difficulty_mode == "easy":
        return row.get("easy_explanation") or row.get("definition") or ""

    # Hard 모드: hard_explanation 우선
    if difficulty_mode == "hard":
        return row.get("hard_explanation") or row.get("definition") or ""

    # Auto 모드: difficulty_level 기준 자동 선택
    level = (row.get("difficulty_level") or "").lower()
    if level in ("beginner", "intermediate") and row.get("easy_explanation"):
        return row["easy_explanation"]
    if level == "advanced" and row.get("hard_explanation"):
        return row["hard_explanation"]

    # Fallback: easy → hard → definition 순서
    return row.get("easy_explanation") or row.get("hard_explanation") or row.get("definition") or ""


def _format_glossary_md(items: List[Dict[str, Any]]) -> str:
    """
    검색 결과를 Markdown 형식으로 포맷팅

    Args:
        items: 검색 결과 리스트 (딕셔너리)

    Returns:
        Markdown 형식 문자열
    """
    # 결과가 없으면 안내 메시지 반환
    if not items:
        return "관련 용어를 찾을 수 없습니다."

    # Markdown 문자열 구성
    out: List[str] = ["## 용어집 검색 결과\n"]

    for i, r in enumerate(items, 1):
        # 용어명
        out.append(f"### {i}. {r.get('term','(term)')}")

        # 카테고리
        out.append(f"- **카테고리**: {r.get('category','')}")

        # 난이도
        out.append(f"- **난이도**: {r.get('difficulty_level','')}")

        # 유사도 점수 (있으면)
        if r.get("score") is not None:
            out.append(f"- **유사도 점수(낮을수록 유사)**: {r['score']:.4f}")

        # 연관 용어 (있으면)
        if r.get("related_terms"):
            related = ', '.join(r['related_terms']) if isinstance(r['related_terms'], list) else r['related_terms']
            out.append(f"- **연관 용어**: {related}")

        # 예시 (있으면)
        if r.get("examples"):
            out.append(f"- **예시**: {r['examples']}")

        # 정의
        if r.get("definition"):
            out.append(f"- **정의**: {r['definition']}")

        # 설명
        if r.get("explanation"):
            out.append(f"\n{r['explanation']}\n")

        # 구분선
        out.append("\n---\n")

    return "\n".join(out)


# ==================== @tool: 용어집 검색 도구 ==================== #

@tool
def search_glossary(
    query: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: str = "auto",  # 'easy' | 'hard' | 'auto'
    mode: str = "hybrid",      # 'hybrid' | 'sql' | 'vector'
    top_k: int = 5,
    with_scores: bool = True,
) -> str:
    """
    용어집 검색 도구 (하이브리드/SQL/Vector 지원)

    Args:
        query: 검색 쿼리
        category: 카테고리 필터
        difficulty: 난이도 모드 ('easy', 'hard', 'auto')
        mode: 검색 모드 ('hybrid', 'sql', 'vector')
        top_k: 최대 결과 수
        with_scores: 유사도 점수 포함 여부

    Returns:
        Markdown 형식 검색 결과

    검색 방식:
    - SQL: PostgreSQL ILIKE + 필터
    - Vector: glossary_embeddings 컬렉션 유사도 검색
    - hybrid: SQL + Vector 결과 병합 후 중복 제거
    """
    # ---------------------- 질문에서 핵심 용어 추출 ---------------------- #
    # "BLEU Score가 뭐야?" -> "BLEU Score"
    if query:
        query = _extract_term_from_question(query)

    items: List[Dict[str, Any]] = []

    # ---------------------- Vector 검색 ---------------------- #
    if mode in ("hybrid", "vector") and query:
        try:
            # Vector DB 유사도 검색
            vector_pairs = _vector_search_glossary(query, k=top_k)

            # 결과 변환
            for doc, score in vector_pairs:
                md = doc.metadata or {}
                row = {
                    "term": md.get("term") or md.get("title") or "",
                    "category": md.get("category"),
                    "difficulty_level": md.get("difficulty_level"),
                    "related_terms": md.get("related_terms"),
                    "examples": md.get("examples"),
                    "definition": md.get("definition"),
                    "explanation": _pick_explanation(md, difficulty),
                    "score": float(score) if with_scores else None,
                }
                items.append(row)

        except Exception:
            # 벡터 인덱스가 비어 있거나 컬렉션 미생성 시 조용히 패스
            # hybrid 모드면 SQL 결과로 보완
            pass

    # ---------------------- SQL 검색 ---------------------- #
    if mode in ("hybrid", "sql"):
        # difficulty_level 값 변환 (easy/hard → beginner/advanced)
        sql_difficulty = None
        if difficulty in ("beginner", "intermediate", "advanced"):
            sql_difficulty = difficulty

        # PostgreSQL 검색
        sql_rows = _fetch_glossary_sql(
            query=query,
            category=category,
            difficulty=sql_difficulty,
            limit=top_k,
        )

        # 결과 변환
        for r in sql_rows:
            items.append({
                "term": r.get("term"),
                "category": r.get("category"),
                "difficulty_level": r.get("difficulty_level"),
                "related_terms": r.get("related_terms"),
                "examples": r.get("examples"),
                "definition": r.get("definition"),
                "explanation": _pick_explanation(r, difficulty),
                "score": None,
            })

    # ---------------------- 중복 제거 ---------------------- #
    seen = set()
    uniq: List[Dict[str, Any]] = []

    for it in items:
        # (term, definition) 조합으로 중복 체크
        key = (it.get("term"), it.get("definition"))
        if key not in seen:
            seen.add(key)
            uniq.append(it)

    # ---------------------- top_k 보장 및 포맷팅 ---------------------- #
    return _format_glossary_md(uniq[:top_k])


# ==================== Agent 노드: 용어집 검색 ==================== #

def glossary_node(state, exp_manager=None):
    """
    Agent 노드: glossary 테이블에서 용어 정의 검색

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태
    """
    # -------------- 상태에서 질문 및 난이도 추출 -------------- #
    # ✅ refined_query 우선 사용 (Multi-turn 지원)
    question = state.get("refined_query", state["question"])  # 재작성된 질문 우선, 없으면 원본
    difficulty = state.get("difficulty", "easy")              # 난이도 (기본값: easy)

    # -------------- 도구별 Logger 생성 -------------- #
    tool_logger = exp_manager.get_tool_logger('rag_glossary') if exp_manager else None

    if tool_logger:
        if "refined_query" in state:
            tool_logger.write(f"용어집 노드 실행: {question} (재작성된 질문)")
        else:
            tool_logger.write(f"용어집 노드 실행: {question}")
        tool_logger.write(f"난이도: {difficulty}")

    # -------------- search_glossary 도구 호출 -------------- #
    try:
        # Langchain @tool 함수 호출
        raw_results = search_glossary.invoke({
            "query": question,                            # 검색 쿼리
            "category": None,                             # 카테고리 필터 없음
            "difficulty": difficulty,                     # 난이도 모드
            "mode": "hybrid",                             # 하이브리드 검색
            "top_k": 3,                                   # 최대 3개 결과
            "with_scores": True,                          # 유사도 점수 포함
        })

        if tool_logger:
            tool_logger.write(f"검색 결과: {len(raw_results)} 글자")

        # -------------- pgvector 검색 기록 -------------- #
        if exp_manager:
            exp_manager.log_pgvector_search({
                "tool": "glossary",
                "collection": "glossary_embeddings",
                "query_text": question,
                "search_mode": "hybrid",
                "top_k": 3,
                "with_scores": True,
                "result_length": len(raw_results)
            })

        # -------------- 두 수준의 답변 생성 -------------- #
        level_mapping = {
            "easy": ["elementary", "beginner"],
            "hard": ["intermediate", "advanced"]
        }

        levels = level_mapping.get(difficulty, ["beginner", "intermediate"])
        final_answers = {}

        # 난이도별 LLM 초기화 (공통)
        llm_client = LLMClient.from_difficulty(
            difficulty=difficulty,
            logger=exp_manager.logger if exp_manager else None
        )

        # 사용자 프롬프트 (공통)
        user_content = f"""[용어집 검색 결과]
{raw_results}

[질문]
{question}

위 검색 결과를 바탕으로 질문에 답변해주세요."""

        # 각 수준별로 답변 생성
        for level in levels:
            if tool_logger:
                tool_logger.write(f"수준 '{level}' 답변 생성 시작")

            # JSON 프롬프트 로드
            system_prompt = get_tool_prompt("glossary", level)

            # 메시지 구성
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content)
            ]

            # 프롬프트 저장
            if exp_manager:
                exp_manager.save_system_prompt(system_prompt, {
                    "tool": "glossary",
                    "difficulty": difficulty,
                    "level": level
                })
                final_prompt = f"""[SYSTEM PROMPT - {level}]
{system_prompt}

[USER PROMPT]
{user_content}"""
                exp_manager.save_final_prompt(final_prompt, {
                    "tool": "glossary",
                    "difficulty": difficulty,
                    "level": level
                })

            # LLM 호출
            response = llm_client.llm.invoke(messages)
            final_answers[level] = response.content

            # 로깅
            if tool_logger:
                tool_logger.write(f"수준 '{level}' 답변 생성 완료: {len(response.content)} 글자")
                tool_logger.write("=" * 80)
                tool_logger.write(f"[{level} 답변 전체 내용]")
                tool_logger.write(response.content)
                tool_logger.write("=" * 80)

        if tool_logger:
            tool_logger.close()

        # -------------- 최종 답변 저장 -------------- #
        state["final_answers"] = final_answers
        state["final_answer"] = final_answers[levels[1]]

    except Exception as e:
        if tool_logger:
            tool_logger.write(f"용어집 검색 실패: {e}")
            tool_logger.close()

        # 에러 메시지 저장
        state["final_answer"] = f"용어집 검색 오류: {str(e)}"

    # -------------- 업데이트된 상태 반환 -------------- #
    return state
