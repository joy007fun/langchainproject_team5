# src/tools/web_search.py
"""
웹 검색 도구 모듈

Tavily API로 최신 논문 정보 검색
검색 결과 LLM 정리
난이도별 프롬프트 적용
"""

# ==================== Import ==================== #
import os
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from src.agent.state import AgentState
from src.llm.client import LLMClient
from src.tools.arxiv_handler import ArxivPaperHandler
from src.prompts import get_tool_prompt, get_web_search_user_prompt_template


# ==================== 도구 4: 웹 검색 노드 ==================== #
def web_search_node(state: AgentState, exp_manager=None):
    """
    웹 검색 노드: Tavily API로 최신 논문 정보 검색

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태
    """
    # -------------- 상태에서 질문 및 난이도 추출 -------------- #
    question = state["question"]                # 사용자 질문
    difficulty = state.get("difficulty", "easy")  # 난이도 (기본값: easy)

    # -------------- 도구별 Logger 생성 -------------- #
    tool_logger = exp_manager.get_tool_logger('web_search') if exp_manager else None

    if tool_logger:
        tool_logger.write(f"웹 검색 노드 실행: {question}")
        tool_logger.write(f"난이도: {difficulty}")

    # -------------- Tavily Search API 초기화 -------------- #
    try:
        search_tool = TavilySearchResults(
            max_results=5,                      # 최대 검색 결과 수
            api_key=os.getenv("TAVILY_API_KEY")  # Tavily API 키
        )

        if tool_logger:
            tool_logger.write("Tavily Search API 초기화 완료")
    except Exception as e:
        if tool_logger:
            tool_logger.write(f"Tavily API 초기화 실패: {e}")
            tool_logger.close()
        state["final_answer"] = f"웹 검색 API 초기화 오류: {str(e)}"
        return state

    # -------------- 웹 검색 실행 -------------- #
    try:
        if tool_logger:
            tool_logger.write("Tavily Search API 호출 시작")

        search_results = search_tool.invoke({"query": question})  # 검색 실행

        if tool_logger:
            tool_logger.write(f"검색 결과 수: {len(search_results)}")
    except Exception as e:
        if tool_logger:
            tool_logger.write(f"웹 검색 실패: {e}")
            tool_logger.close()
        state["final_answer"] = f"웹 검색 오류: {str(e)}"
        return state

    # -------------- 검색 결과 확인 -------------- #
    if not search_results:
        if tool_logger:
            tool_logger.write("검색 결과가 없음")
            tool_logger.close()
        state["final_answer"] = "웹에서 관련 정보를 찾을 수 없습니다."
        return state

    # -------------- arXiv 논문 자동 저장 -------------- #
    arxiv_handler = ArxivPaperHandler(logger=tool_logger)
    arxiv_count = 0

    for result in search_results:
        url = result.get('url', '')

        # arXiv URL 확인
        if 'arxiv.org' in url:
            if tool_logger:
                tool_logger.write(f"arXiv 논문 발견: {url}")

            try:
                # arXiv 논문 처리 (다운로드 + DB 저장)
                success = arxiv_handler.process_arxiv_paper(url)

                if success:
                    arxiv_count += 1
                    if tool_logger:
                        tool_logger.write(f"arXiv 논문 저장 성공: {url}")
                else:
                    if tool_logger:
                        tool_logger.write(f"arXiv 논문 저장 실패: {url}")
            except Exception as e:
                if tool_logger:
                    tool_logger.write(f"arXiv 논문 처리 오류: {e}", print_error=True)

    if arxiv_count > 0 and tool_logger:
        tool_logger.write(f"총 {arxiv_count}개 arXiv 논문 저장 완료")

    # -------------- 검색 결과 포맷팅 -------------- #
    formatted_results = "\n\n".join([
        f"[결과 {i+1}]\n제목: {result.get('title', 'N/A')}\n내용: {result.get('content', 'N/A')}\nURL: {result.get('url', 'N/A')}"
        for i, result in enumerate(search_results)
    ])

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

    # -------------- LLM 답변 생성 -------------- #
    try:
        # 각 수준별로 답변 생성
        for level in levels:
            if tool_logger:
                tool_logger.write(f"수준 '{level}' 답변 생성 시작")

            # JSON 프롬프트 로드
            system_prompt = get_tool_prompt("web_search", level)
            user_prompt_template = get_web_search_user_prompt_template(level)
            user_prompt = user_prompt_template.format(
                formatted_results=formatted_results,
                question=question
            )

            # 메시지 구성
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # 프롬프트 저장
            if exp_manager:
                exp_manager.save_system_prompt(system_prompt, metadata={
                    "difficulty": difficulty,
                    "level": level,
                    "results_count": len(search_results)
                })
                final_prompt = f"""[SYSTEM PROMPT - {level}]
{system_prompt}

[USER PROMPT]
{user_prompt}"""
                exp_manager.save_final_prompt(final_prompt, {
                    "tool": "web_search",
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
        state["tool_result"] = final_answers[levels[1]]  # Skip 로직을 위한 tool_result 설정

    except Exception as e:
        if tool_logger:
            tool_logger.write(f"LLM 호출 실패: {e}")
            tool_logger.close()
        state["final_answer"] = f"답변 생성 오류: {str(e)}"

    return state
