# ==========================================
# 📘 RAG 논문 검색 도구 모듈 + Agent 노드 통합
# ------------------------------------------
# - @tool: search_paper_database
# - Agent 노드: search_paper_node
# - 검색 모드 선택 (similarity/MMR), MultiQuery 옵션
# - 메타데이터 필터(year/author/category)
# - PostgreSQL 메타 조회 → 결과 합성 → Markdown 반환
# ==========================================

import os
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain.schema import SystemMessage, HumanMessage

from src.rag.retriever import RAGRetriever
from src.prompts import get_tool_prompt
from src.llm.client import LLMClient


# ==================== 내부 유틸: 환경/DB ==================== #

def _env(primary: str, alt: str, default: Optional[str] = None) -> Optional[str]:
    """환경 변수 조회 (우선순위: primary > alt > default)"""
    return os.getenv(primary) or os.getenv(alt) or default


def _pg_conn_str() -> str:
    """PostgreSQL 연결 문자열 생성"""
    user = _env("POSTGRES_USER", "PGUSER", "postgres")
    password = _env("POSTGRES_PASSWORD", "PGPASSWORD", "postgres")
    host = _env("POSTGRES_HOST", "PGHOST", "localhost")
    port = _env("POSTGRES_PORT", "PGPORT", "5432")
    db = _env("POSTGRES_DB", "PGDATABASE", "papers")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _fetch_paper_meta(paper_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    papers 테이블에서 ID 목록에 해당하는 메타데이터를 일괄 조회.

    Args:
        paper_ids: 논문 ID 리스트

    Returns:
        Dict[int, Dict[str, Any]]: {paper_id: {title, authors, ...}}
    """
    if not paper_ids:
        return {}

    conn = psycopg2.connect(_pg_conn_str())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT paper_id, title, authors, publish_date, url, category, citation_count
                FROM papers
                WHERE paper_id = ANY(%s)
                """,
                (paper_ids,),
            )
            rows = cur.fetchall()
            out: Dict[int, Dict[str, Any]] = {}
            for row in rows:
                out[row["paper_id"]] = dict(row)
            return out
    finally:
        conn.close()


def _format_markdown(results: List[Dict[str, Any]]) -> str:
    """
    검색 결과를 Markdown 문자열로 변환.

    Args:
        results: 검색 결과 리스트

    Returns:
        str: Markdown 형식의 문자열
    """
    if not results:
        return "관련 논문을 찾을 수 없습니다."

    # ✅ 유사도 점수 검증: 최소 하나의 결과가 임계값 이하(유사도 높음)여야 함
    SIMILARITY_THRESHOLD = 0.5  # distance 기준 (낮을수록 유사, pgvector cosine distance)
    has_relevant_result = False

    for r in results:
        score = r.get("score")
        # score가 None이 아니고 임계값 이하(유사도 높음)인 경우
        if score is not None and score <= SIMILARITY_THRESHOLD:
            has_relevant_result = True
            break

    # 모든 결과의 유사도가 낮으면 (score가 모두 임계값 초과) 실패 처리
    if not has_relevant_result:
        return "관련 논문을 찾을 수 없습니다."

    lines: List[str] = ["## 검색된 논문\n"]
    for i, r in enumerate(results, 1):
        score_str = f"{r['score']:.4f}" if r.get("score") is not None else "N/A"

        lines.append(f"### {i}. {r.get('title','(Untitled)')}")
        lines.append(f"- **저자**: {r.get('authors','')}")
        lines.append(f"- **출판일**: {r.get('publish_date','')}")
        lines.append(f"- **카테고리**: {r.get('category','')}")
        lines.append(f"- **인용수**: {r.get('citation_count','')}")
        lines.append(f"- **URL**: {r.get('url','')}")
        lines.append(f"- **섹션**: {r.get('section','본문')}")
        lines.append(f"- **유사도 점수(낮을수록 유사)**: {score_str}\n")

        preview = (r.get("content") or "")[:600]
        if preview:
            lines.append(preview + ("..." if len(r.get("content","")) > 600 else ""))
        lines.append("\n---\n")

    return "\n".join(lines)


def _build_filter(year_gte: Optional[int], author: Optional[str], category: Optional[str]) -> Dict[str, Any]:
    """
    VectorStore 메타데이터 필터 구성.

    Args:
        year_gte: 연도 이상 필터
        author: 저자 부분일치 필터
        category: 카테고리 필터

    Returns:
        Dict[str, Any]: 필터 딕셔너리
    """
    f: Dict[str, Any] = {}
    if year_gte is not None:
        f["year"] = {"$gte": int(year_gte)}
    if author:
        f["authors"] = {"$ilike": f"%{author}%"}
    if category:
        f["category"] = category
    return f


def _keyword_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    PostgreSQL Full-Text Search로 키워드 검색.

    Args:
        query: 검색 질문
        top_k: 반환할 결과 수

    Returns:
        List[Dict[str, Any]]: 키워드 검색 결과 (paper_id, title, abstract, score)
    """
    import re

    # 쿼리 전처리: 영어 키워드 추출
    # 1. 괄호 안의 영어 우선 사용 (예: "RAG (Retrieval-Augmented Generation)" → "Retrieval-Augmented Generation")
    # 2. 없으면 영어 단어들 추출
    english_keywords = []

    # 괄호 안의 영어 추출
    paren_match = re.search(r'\(([A-Za-z0-9\s\-]+)\)', query)
    if paren_match:
        english_keywords.append(paren_match.group(1).strip())

    # 영어 단어 추출 (3글자 이상)
    words = re.findall(r'\b[A-Za-z]{3,}(?:-[A-Za-z]+)*\b', query)
    english_keywords.extend(words)

    # 중복 제거 및 공백 제거
    english_keywords = list(dict.fromkeys([k.strip() for k in english_keywords if k.strip()]))

    if not english_keywords:
        # 영어가 없으면 원본 쿼리 사용
        search_query = query
    else:
        # 가장 긴 키워드 우선 사용 (더 구체적)
        search_query = max(english_keywords, key=len)

    conn = psycopg2.connect(_pg_conn_str())
    try:
        cursor = conn.cursor()

        # PostgreSQL Full-Text Search (title, abstract)
        sql = """
        SELECT
            paper_id,
            title,
            abstract,
            authors,
            publish_date,
            category,
            citation_count,
            url,
            (
                CASE
                    WHEN title ILIKE %s THEN 2.0
                    ELSE 0.0
                END +
                CASE
                    WHEN abstract ILIKE %s THEN 1.0
                    ELSE 0.0
                END
            ) AS keyword_score
        FROM papers
        WHERE title ILIKE %s OR abstract ILIKE %s
        ORDER BY keyword_score DESC, citation_count DESC
        LIMIT %s
        """

        search_pattern = f"%{search_query}%"
        cursor.execute(sql, (search_pattern, search_pattern, search_pattern, search_pattern, top_k))

        results = []
        for row in cursor.fetchall():
            results.append({
                "paper_id": row[0],
                "title": row[1],
                "abstract": row[2],
                "authors": row[3],
                "publish_date": row[4],
                "category": row[5],
                "citation_count": row[6],
                "url": row[7],
                "keyword_score": float(row[8]),
            })

        cursor.close()
        return results

    except Exception as e:
        return []
    finally:
        conn.close()


# ==================== @tool: 논문 검색 ==================== #

@tool
def search_paper_database(
    query: str,
    year_gte: Optional[int] = None,
    author: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 5,
    with_scores: bool = True,
    use_multi_query: bool = True,
    search_mode: str = "mmr",  # "similarity" | "mmr"
    use_hybrid: bool = True,   # 하이브리드 검색 사용 여부
    tool_name: str = "search_paper",  # 도구명 (가중치 조정용)
) -> str:
    """
    논문 VectorDB + PostgreSQL 메타데이터를 함께 조회하여 결과를 반환.
    하이브리드 검색: 벡터 검색 + 키워드 검색 가중치 결합

    Parameters
    ----------
    query : str
        사용자 질의
    year_gte : Optional[int]
        특정 연도 이상 필터 (예: 2020)
    author : Optional[str]
        저자 부분일치 필터
    category : Optional[str]
        카테고리 필터 (예: 'cs.CL')
    top_k : int
        반환할 문서 수
    with_scores : bool
        유사도 점수 포함 여부
    use_multi_query : bool
        MultiQuery(LLM 쿼리 확장) 사용 여부
    search_mode : str
        "similarity" 또는 "mmr"
    use_hybrid : bool
        하이브리드 검색 사용 여부
    tool_name : str
        도구명 (glossary, search_paper 등)
    """

    # ---------- Config에서 하이브리드 검색 가중치 로드 ----------
    from src.utils.config_loader import get_model_config

    config = get_model_config()
    hybrid_config = config.get("rag", {}).get("hybrid_search", {})
    hybrid_enabled = hybrid_config.get("enabled", True) and use_hybrid

    # 도구별 가중치 우선 사용, 없으면 기본 가중치
    tool_weights = hybrid_config.get("tool_specific_weights", {}).get(tool_name, {})
    vector_weight = tool_weights.get("vector_weight", hybrid_config.get("vector_weight", 0.7))
    keyword_weight = tool_weights.get("keyword_weight", hybrid_config.get("keyword_weight", 0.3))

    # ---------- Retriever 준비 ----------
    r = RAGRetriever(search_type=search_mode, k=top_k)

    # ---------- 검색 실행 (필터/멀티쿼리 처리) ----------
    filter_dict = _build_filter(year_gte, author, category)
    docs: List[Document] = []
    pairs: List[Tuple[Document, float]] = []

    if any(filter_dict.values()):
        # 메타데이터 필터가 있으면 similarity + filter로 수행
        docs = r.search_with_filter(query, filter_dict, k=top_k)
        if with_scores:
            pairs = [(d, None) for d in docs]  # type: ignore
    else:
        if use_multi_query:
            docs = r.multi_query_search(query, k=top_k)
            if with_scores:
                pairs = r.similarity_search_with_score(query, k=len(docs) or top_k)
        else:
            if with_scores:
                pairs = r.similarity_search_with_score(query, k=top_k)
                docs = [d for d, _ in pairs]
            else:
                docs = r.similarity_search(query, k=top_k)

    # ---------- 하이브리드 검색: 키워드 검색 추가 ----------
    keyword_results = []
    if hybrid_enabled:
        keyword_results = _keyword_search(query, top_k=top_k)

    # ---------- paper_id 메타로 PostgreSQL 메타데이터 조회 ----------
    paper_ids = []
    for d in docs:
        pid = d.metadata.get("paper_id")
        if isinstance(pid, int):
            paper_ids.append(pid)
        else:
            # 혹시 str이면 int 로 변환 시도
            try:
                paper_ids.append(int(pid))
            except Exception:
                pass
    meta_map = _fetch_paper_meta(list(set(paper_ids)))

    # ---------- 결과 합성 (하이브리드 검색 가중치 적용) ----------
    score_map: Dict[int, float] = {}  # paper_id → final_score

    # 1. 벡터 검색 점수 (가중치 적용)
    if with_scores and pairs:
        for d, s in pairs:
            if s is None:
                continue
            pid = d.metadata.get("paper_id")
            if pid:
                # 벡터 검색 점수: 낮을수록 유사 (distance) → 정규화 필요
                # score = 1 / (1 + distance) 형태로 변환
                normalized_score = 1.0 / (1.0 + float(s))
                score_map[pid] = score_map.get(pid, 0.0) + normalized_score * vector_weight

    # 2. 키워드 검색 점수 (가중치 적용)
    if hybrid_enabled and keyword_results:
        for kw_result in keyword_results:
            pid = kw_result["paper_id"]
            keyword_score = kw_result["keyword_score"]
            # 키워드 점수: 높을수록 좋음 (title: 2.0, abstract: 1.0)
            # 정규화: 최대 3.0 기준 (title + abstract)
            normalized_kw_score = keyword_score / 3.0
            score_map[pid] = score_map.get(pid, 0.0) + normalized_kw_score * keyword_weight

    # 3. 최종 결과 생성 (score 기준 정렬)
    results: List[Dict[str, Any]] = []
    seen_pids = set()

    # 벡터 검색 결과 추가
    for d in docs:
        pid = d.metadata.get("paper_id")
        if pid and pid not in seen_pids:
            seen_pids.add(pid)
            meta = meta_map.get(pid, {}) if pid is not None else {}
            results.append({
                "paper_id": pid,
                "title": meta.get("title") or d.metadata.get("title"),
                "authors": meta.get("authors") or d.metadata.get("authors"),
                "publish_date": meta.get("publish_date") or d.metadata.get("publish_date"),
                "url": meta.get("url") or d.metadata.get("url"),
                "category": meta.get("category") or d.metadata.get("category"),
                "citation_count": meta.get("citation_count"),
                "section": d.metadata.get("section", "본문"),
                "content": d.page_content,
                "score": score_map.get(pid, 0.0) if with_scores else None,
            })

    # 키워드 검색 결과 추가 (중복 제외)
    if hybrid_enabled and keyword_results:
        for kw_result in keyword_results:
            pid = kw_result["paper_id"]
            if pid not in seen_pids:
                seen_pids.add(pid)
                # 키워드 검색으로만 찾은 경우 content는 abstract 사용
                results.append({
                    "paper_id": pid,
                    "title": kw_result.get("title"),
                    "authors": kw_result.get("authors"),
                    "publish_date": kw_result.get("publish_date"),
                    "url": kw_result.get("url"),
                    "category": kw_result.get("category"),
                    "citation_count": kw_result.get("citation_count"),
                    "section": "초록",
                    "content": kw_result.get("abstract", ""),
                    "score": score_map.get(pid, 0.0) if with_scores else None,
                })

    # 점수 기준 정렬 (높은 점수부터)
    if with_scores and hybrid_enabled:
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

    # top_k 제한
    results = results[:top_k]

    # ---------- Markdown 포맷으로 반환 ----------
    return _format_markdown(results)


# ==================== Agent 노드: RAG 검색 ==================== #

def search_paper_node(state, exp_manager=None):
    """
    Agent 노드: 논문 DB에서 관련 논문 검색 및 답변 생성

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
    tool_logger = exp_manager.get_tool_logger('rag_paper') if exp_manager else None

    if tool_logger:
        if "refined_query" in state:
            tool_logger.write(f"RAG 검색 노드 실행: {question} (재작성된 질문)")
        else:
            tool_logger.write(f"RAG 검색 노드 실행: {question}")
        tool_logger.write(f"난이도: {difficulty}")

    # -------------- search_paper_database 도구 호출 -------------- #
    try:
        # Langchain @tool 함수 호출
        raw_results = search_paper_database.invoke({
            "query": question,                            # 검색 쿼리
            "year_gte": None,                             # 연도 필터 없음
            "author": None,                               # 저자 필터 없음
            "category": None,                             # 카테고리 필터 없음
            "top_k": 5,                                   # Top-5 검색
            "with_scores": True,                          # 유사도 점수 포함
            "use_multi_query": True,                      # ✅ MultiQuery 활성화 (검색 강화)
            "search_mode": "similarity",                  # 유사도 검색
            "use_hybrid": True,                           # ✅ 하이브리드 검색 활성화 (벡터+키워드)
            "tool_name": "search_paper",                  # ✅ 도구명 (가중치 조정용)
        })

        if tool_logger:
            tool_logger.write(f"검색 결과: {len(raw_results)} 글자")

        # -------------- 검색 결과 없음 체크 (Fallback 트리거) -------------- #
        if "관련 논문을 찾을 수 없습니다" in raw_results:
            if tool_logger:
                tool_logger.write("데이터베이스에서 논문을 찾지 못했습니다. Fallback 필요.")
                tool_logger.close()

            # 명확한 실패 메시지 반환 (failure_detector 패턴과 정확히 일치)
            state["final_answer"] = "데이터베이스에서 찾지 못했습니다."
            return state

        # -------------- pgvector 검색 기록 -------------- #
        if exp_manager:
            exp_manager.log_pgvector_search({
                "tool": "search_paper",
                "collection": "paper_chunks",
                "query_text": question,
                "search_mode": "similarity",
                "top_k": 5,
                "use_multi_query": False,
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
        user_content = f"""[논문 검색 결과]
{raw_results}

[질문]
{question}

위 검색 결과를 바탕으로 질문에 답변해주세요."""

        # 각 수준별로 답변 생성
        for level in levels:
            if tool_logger:
                tool_logger.write(f"수준 '{level}' 답변 생성 시작")

            # JSON 프롬프트 로드
            system_prompt = get_tool_prompt("search_paper", level)

            # 메시지 구성
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content)
            ]

            # 프롬프트 저장
            if exp_manager:
                exp_manager.save_system_prompt(system_prompt, {
                    "tool": "search_paper",
                    "difficulty": difficulty,
                    "level": level
                })
                final_prompt = f"""[SYSTEM PROMPT - {level}]
{system_prompt}

[USER PROMPT]
{user_content}"""
                exp_manager.save_final_prompt(final_prompt, {
                    "tool": "search_paper",
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
            tool_logger.write(f"논문 검색 실패: {e}")
            tool_logger.close()

        # 에러 메시지 저장
        state["final_answer"] = f"논문 검색 오류: {str(e)}"

    # -------------- 업데이트된 상태 반환 -------------- #
    return state
