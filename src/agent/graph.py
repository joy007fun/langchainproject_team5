# src/agent/graph.py
"""
Agent 그래프 구성 모듈

LangGraph StateGraph 기반 AI Agent 그래프:
- 노드 추가 (router + 7개 도구 + Fallback 노드들)
- 조건부 엣지 설정 (Fallback Chain 지원)
- 그래프 컴파일
"""

# ------------------------- 표준 라이브러리 ------------------------- #
from functools import partial

# ------------------------- LangGraph 라이브러리 ------------------------- #
from langgraph.graph import StateGraph, END
# StateGraph: LangGraph 상태 그래프
# END: 종료 노드

# ------------------------- 프로젝트 모듈 ------------------------- #
from src.agent.state import AgentState
from src.agent.nodes import (
    router_node,
    general_answer_node,
    save_file_node,
    search_paper_node,
    web_search_node,
    glossary_node,
    summarize_node,
    text2sql_node,
    fallback_router_node,
    validate_tool_choice_node,
    final_fallback_node
)
from src.agent.config_loader import (
    load_fallback_config,
    get_priority_chain,
    is_fallback_enabled,
    is_validation_enabled
)
from src.agent.question_classifier import classify_question
from src.agent.failure_detector import is_tool_failed
from src.agent.tool_wrapper import wrap_tool_node


# ==================== 라우팅 함수 ==================== #
# ---------------------- 다음 노드 결정 ---------------------- #
def route_to_tool(state: AgentState):
    """
    라우팅 결정에 따라 다음 노드 선택

    Args:
        state (AgentState): Agent 상태

    Returns:
        str: 다음 노드 이름
    """
    # -------------- tool_choice 값을 반환 -------------- #
    return state["tool_choice"]                 # 선택된 도구 이름 반환


# ==================== 다중 요청 처리 함수 ==================== #
# ---------------------- tool_pipeline 순차 실행 판단 ---------------------- #
def should_continue_pipeline(state: AgentState) -> str:
    """
    tool_pipeline에 남은 도구가 있는지 확인

    Args:
        state (AgentState): Agent 상태

    Returns:
        str: "continue" (다음 도구 실행) 또는 "end" (종료)
    """
    # -------------- pipeline 정보 추출 -------------- #
    tool_pipeline = state.get("tool_pipeline", [])
    pipeline_index = state.get("pipeline_index", 0)

    # -------------- pipeline이 없으면 종료 -------------- #
    if not tool_pipeline:
        return "end"

    # -------------- 다음 도구가 있으면 계속 실행 -------------- #
    if pipeline_index < len(tool_pipeline):
        return "continue"

    # -------------- 모든 도구 실행 완료 시 종료 -------------- #
    return "end"


# ==================== Pipeline 다음 도구 선택 ==================== #
# ---------------------- tool_pipeline에서 다음 도구 반환 ---------------------- #
def route_next_pipeline_tool(state: AgentState) -> str:
    """
    tool_pipeline에서 다음 실행할 도구 선택

    Args:
        state (AgentState): Agent 상태

    Returns:
        str: 다음 도구 이름
    """
    # -------------- pipeline 정보 추출 -------------- #
    tool_pipeline = state.get("tool_pipeline", [])
    pipeline_index = state.get("pipeline_index", 0)

    # -------------- 다음 도구 반환 -------------- #
    if pipeline_index < len(tool_pipeline):
        next_tool = tool_pipeline[pipeline_index]
        state["tool_choice"] = next_tool
        state["pipeline_index"] = pipeline_index + 1

        # 타임라인 기록 (다중 요청 진행 상황)
        from datetime import datetime
        timeline = state.get("tool_timeline", [])
        timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "pipeline_progress",
            "tool": next_tool,
            "pipeline_index": pipeline_index + 1,
            "total_tools": len(tool_pipeline),
            "description": f"다중 요청 진행: {pipeline_index + 1}/{len(tool_pipeline)} - '{next_tool}' 도구 실행"
        })
        state["tool_timeline"] = timeline

        return next_tool

    # -------------- 기본값 (도달하지 않아야 함) -------------- #
    return "general"


# ==================== Fallback 판단 함수 ==================== #
# ---------------------- 도구 실행 후 Fallback 여부 결정 ---------------------- #
def should_fallback(state: AgentState) -> str:
    """
    도구 실행 후 Fallback 여부 결정

    Args:
        state (AgentState): Agent 상태

    Returns:
        str: "end", "retry", "final_fallback" 중 하나
    """
    # -------------- 상태 정보 추출 -------------- #
    tool_status = state.get("tool_status", "success")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    # -------------- 성공 시 종료 -------------- #
    if tool_status == "success":
        return "end"

    # -------------- 재시도 횟수 초과 시 최종 Fallback -------------- #
    if retry_count >= max_retries:
        return "final_fallback"

    # -------------- 실패 시 재라우팅 -------------- #
    return "retry"


# ==================== 검증 및 라우팅 함수 ==================== #
# ---------------------- Router 검증 후 도구 선택 ---------------------- #
def should_validate_and_route(state: AgentState) -> str:
    """
    Router 검증 여부 결정 후 도구 라우팅

    Args:
        state (AgentState): Agent 상태

    Returns:
        str: "router" (재라우팅) 또는 도구 이름
    """
    # -------------- 검증 활성화 여부 확인 -------------- #
    validation_enabled = state.get("validation_enabled", False)

    # -------------- 검증 비활성화 시 바로 도구 실행 -------------- #
    if not validation_enabled:
        return state["tool_choice"]

    # -------------- 검증 결과 확인 -------------- #
    validation_failed = state.get("validation_failed", False)
    validation_retries = state.get("validation_retries", 0)
    max_validation = state.get("max_validation", 2)

    # -------------- 검증 실패 시 재라우팅 -------------- #
    if validation_failed and validation_retries < max_validation:
        return "router"

    # -------------- 검증 통과 시 도구 실행 -------------- #
    return state["tool_choice"]


# ==================== Agent 그래프 생성 함수 ==================== #
# ---------------------- LangGraph StateGraph 구성 ---------------------- #
def create_agent_graph(exp_manager=None):
    """
    LangGraph Agent 그래프 생성 (Fallback Chain 지원)

    Args:
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        CompiledGraph: 컴파일된 Agent 그래프
    """
    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write("Agent 그래프 생성 시작")

    # -------------- Fallback Chain 설정 로드 -------------- #
    fallback_config = load_fallback_config()
    fallback_enabled = fallback_config.get("enabled", True)

    if exp_manager:
        if fallback_enabled:
            exp_manager.logger.write("Fallback Chain 활성화")
            exp_manager.logger.write(f"최대 재시도 횟수: {fallback_config.get('max_retries', 3)}")
            exp_manager.logger.write(f"Router 검증 활성화: {fallback_config.get('validation_enabled', True)}")
        else:
            exp_manager.logger.write("Fallback Chain 비활성화 (기존 동작)")

    # -------------- StateGraph 생성 -------------- #
    workflow = StateGraph(AgentState)           # AgentState 기반 그래프 생성

    # -------------- exp_manager를 바인딩한 노드 함수 생성 -------------- #
    # partial을 사용하여 각 노드에 exp_manager를 미리 바인딩
    router_with_exp = partial(router_node, exp_manager=exp_manager)

    # Fallback 활성화 시 도구 래퍼 적용
    if fallback_enabled:
        # 래퍼 적용 (tool_status 자동 설정)
        general_with_exp = partial(wrap_tool_node(general_answer_node, "general"), exp_manager=exp_manager)
        save_file_with_exp = partial(wrap_tool_node(save_file_node, "save_file"), exp_manager=exp_manager)
        search_paper_with_exp = partial(wrap_tool_node(search_paper_node, "search_paper"), exp_manager=exp_manager)
        web_search_with_exp = partial(wrap_tool_node(web_search_node, "web_search"), exp_manager=exp_manager)
        glossary_with_exp = partial(wrap_tool_node(glossary_node, "glossary"), exp_manager=exp_manager)
        summarize_with_exp = partial(wrap_tool_node(summarize_node, "summarize"), exp_manager=exp_manager)
        text2sql_with_exp = partial(wrap_tool_node(text2sql_node, "text2sql"), exp_manager=exp_manager)
    else:
        # 래퍼 없이 기존 방식
        general_with_exp = partial(general_answer_node, exp_manager=exp_manager)
        save_file_with_exp = partial(save_file_node, exp_manager=exp_manager)
        search_paper_with_exp = partial(search_paper_node, exp_manager=exp_manager)
        web_search_with_exp = partial(web_search_node, exp_manager=exp_manager)
        glossary_with_exp = partial(glossary_node, exp_manager=exp_manager)
        summarize_with_exp = partial(summarize_node, exp_manager=exp_manager)
        text2sql_with_exp = partial(text2sql_node, exp_manager=exp_manager)

    # Fallback 관련 노드
    fallback_router_with_exp = partial(fallback_router_node, exp_manager=exp_manager)
    validator_with_exp = partial(validate_tool_choice_node, exp_manager=exp_manager)
    final_fallback_with_exp = partial(final_fallback_node, exp_manager=exp_manager)

    # -------------- 노드 추가 -------------- #
    workflow.add_node("router", router_with_exp)                    # 라우터 노드
    workflow.add_node("general", general_with_exp)                  # 일반 답변 노드
    workflow.add_node("save_file", save_file_with_exp)              # 파일 저장 노드
    workflow.add_node("search_paper", search_paper_with_exp)        # RAG 검색 노드
    workflow.add_node("web_search", web_search_with_exp)            # 웹 검색 노드
    workflow.add_node("glossary", glossary_with_exp)                # 용어집 노드
    workflow.add_node("summarize", summarize_with_exp)              # 논문 요약 노드
    workflow.add_node("text2sql", text2sql_with_exp)                # Text-to-SQL 노드

    # Fallback 관련 노드
    if fallback_enabled:
        workflow.add_node("fallback_router", fallback_router_with_exp)  # Fallback Router
        workflow.add_node("validator", validator_with_exp)              # Router 검증
        workflow.add_node("final_fallback", final_fallback_with_exp)    # 최종 Fallback

    # -------------- 시작점 설정 -------------- #
    workflow.set_entry_point("router")          # 라우터를 시작점으로 설정

    # -------------- 조건부 엣지 설정 -------------- #
    if fallback_enabled:
        # ========== Fallback Chain 활성화 모드 ========== #

        # Router → 검증 후 도구 선택
        workflow.add_conditional_edges(
            "router",
            should_validate_and_route,
            {
                "router": "router",                 # 검증 실패 → 재라우팅
                "general": "general",               # 도구 선택
                "glossary": "glossary",
                "search_paper": "search_paper",
                "web_search": "web_search",
                "summarize": "summarize",
                "text2sql": "text2sql",
                "save_file": "save_file"
            }
        )

        # 각 도구 → Pipeline 계속 실행 또는 Fallback 체크
        def check_pipeline_or_fallback(state: AgentState) -> str:
            """도구 실행 후 Pipeline 계속 또는 Fallback 체크"""
            # 1단계: 도구 실행 결과 확인
            tool_status = state.get("tool_status", "success")

            # 2단계: 도구 실행 실패 시 Fallback 체크 (파이프라인 중단)
            if tool_status != "success":
                return should_fallback(state)

            # 3단계: 도구 성공 시 Pipeline 계속 여부 확인
            tool_pipeline = state.get("tool_pipeline", [])
            pipeline_index = state.get("pipeline_index", 0)

            # 4단계: Pipeline이 있고 다음 도구가 있으면 계속 실행
            if tool_pipeline and pipeline_index < len(tool_pipeline):
                return should_continue_pipeline(state)

            # 5단계: Pipeline이 끝났으면 정상 종료
            return "end"

        # 각 도구 → Pipeline 또는 Fallback
        for tool_name in ["general", "glossary", "search_paper", "web_search", "summarize", "text2sql", "save_file"]:
            workflow.add_conditional_edges(
                tool_name,
                check_pipeline_or_fallback,
                {
                    "continue": "pipeline_router",      # Pipeline 계속 → 다음 도구
                    "end": END,                         # 성공 → 종료
                    "retry": "fallback_router",         # 실패 → Fallback Router
                    "final_fallback": "final_fallback"  # 최대 재시도 초과 → 최종 Fallback
                }
            )

        # Pipeline Router 노드 추가 (다음 도구 선택)
        def pipeline_router(state: AgentState, exp_manager=None):
            """Pipeline에서 다음 도구 선택"""
            tool_pipeline = state.get("tool_pipeline", [])
            pipeline_index = state.get("pipeline_index", 0)

            if exp_manager:
                exp_manager.logger.write(f"Pipeline 진행: {pipeline_index}/{len(tool_pipeline)}")

            # ✅ 검색 도구 스킵 로직: RAG 또는 웹 검색이 성공했으면 다른 검색 도구 스킵
            tool_result = state.get("tool_result", "")
            last_tool = tool_pipeline[pipeline_index - 1] if pipeline_index > 0 else None

            # search_paper 성공 시: web_search, general 스킵하고 summarize로 이동
            if last_tool == "search_paper" and tool_result and "찾을 수 없습니다" not in tool_result:
                # summarize 도구가 있으면 그 위치로 이동
                if "summarize" in tool_pipeline[pipeline_index:]:
                    summarize_index = tool_pipeline.index("summarize", pipeline_index)
                    state["pipeline_index"] = summarize_index
                    if exp_manager:
                        exp_manager.logger.write(f"RAG 검색 성공: web_search, general 스킵 → summarize로 이동")

            # web_search 성공 시: general 스킵하고 summarize로 이동
            elif last_tool == "web_search" and tool_result and len(tool_result) > 100:
                # summarize 도구가 있으면 그 위치로 이동
                if "summarize" in tool_pipeline[pipeline_index:]:
                    summarize_index = tool_pipeline.index("summarize", pipeline_index)
                    state["pipeline_index"] = summarize_index
                    if exp_manager:
                        exp_manager.logger.write(f"웹 검색 성공: general 스킵 → summarize로 이동")

            # 다음 도구로 이동 (route_next_pipeline_tool이 state 업데이트)
            route_next_pipeline_tool(state)

            if exp_manager:
                exp_manager.logger.write(f"다음 도구 실행: {state['tool_choice']}")

            return state

        pipeline_router_with_exp = partial(pipeline_router, exp_manager=exp_manager)
        workflow.add_node("pipeline_router", pipeline_router_with_exp)

        # Pipeline Router → 다음 도구
        workflow.add_conditional_edges(
            "pipeline_router",
            route_to_tool,
            {
                "general": "general",
                "glossary": "glossary",
                "search_paper": "search_paper",
                "web_search": "web_search",
                "summarize": "summarize",
                "text2sql": "text2sql",
                "save_file": "save_file"
            }
        )

        # Fallback Router → 다음 도구
        workflow.add_conditional_edges(
            "fallback_router",
            route_to_tool,
            {
                "general": "general",
                "glossary": "glossary",
                "search_paper": "search_paper",
                "web_search": "web_search",
                "summarize": "summarize",
                "text2sql": "text2sql",
                "save_file": "save_file"
            }
        )

        # final_fallback 노드는 종료
        workflow.add_edge("final_fallback", END)

    else:
        # ========== Fallback Chain 비활성화 모드 (기존 동작) ========== #

        # 라우터에서 선택된 도구로 분기
        workflow.add_conditional_edges(
            "router",                               # 출발 노드
            route_to_tool,                          # 라우팅 함수
            {
                "general": "general",               # general → general_answer_node
                "save_file": "save_file",           # save_file → save_file_node
                "search_paper": "search_paper",     # search_paper → search_paper_node
                "web_search": "web_search",         # web_search → web_search_node
                "glossary": "glossary",             # glossary → glossary_node
                "summarize": "summarize",           # summarize → summarize_node
                "text2sql": "text2sql"              # text2sql → text2sql_node
            }
        )

        # 모든 도구 노드에서 종료
        for node in ["general", "save_file", "search_paper", "web_search", "glossary", "summarize", "text2sql"]:
            workflow.add_edge(node, END)            # 각 노드 → END

    # -------------- 그래프 컴파일 -------------- #
    agent_executor = workflow.compile()         # 그래프 컴파일

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write("Agent 그래프 컴파일 완료")

    return agent_executor                       # 컴파일된 그래프 반환


# ==================== 상태 초기화 함수 ==================== #
# ---------------------- Fallback Chain 상태 초기화 ---------------------- #
def initialize_fallback_state(state: AgentState, exp_manager=None) -> AgentState:
    """
    Fallback Chain 관련 상태 초기화

    Args:
        state: Agent 상태
        exp_manager: ExperimentManager 인스턴스

    Returns:
        AgentState: 초기화된 상태
    """
    # -------------- Fallback Chain 설정 로드 -------------- #
    if not is_fallback_enabled():
        return state  # Fallback 비활성화 시 초기화 안 함

    fallback_config = load_fallback_config()

    # -------------- 질문 유형 분류 -------------- #
    question = state.get("question", "")
    difficulty = state.get("difficulty", "easy")

    question_type = classify_question(
        question=question,
        difficulty=difficulty,
        logger=exp_manager.logger if exp_manager else None
    )

    # -------------- 도구 우선순위 로드 -------------- #
    fallback_chain = get_priority_chain(question_type)

    # -------------- 상태 초기화 -------------- #
    state["retry_count"] = 0
    state["failed_tools"] = []
    state["question_type"] = question_type
    state["fallback_chain"] = fallback_chain
    state["validation_failed"] = False
    state["tool_status"] = "pending"
    state["tool_timeline"] = []
    state["max_retries"] = fallback_config.get("max_retries", 3)
    state["validation_enabled"] = fallback_config.get("validation_enabled", True)
    state["validation_retries"] = 0
    state["max_validation"] = fallback_config.get("validation_retries", 2)

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write("Fallback Chain 상태 초기화 완료")
        exp_manager.logger.write(f"질문 유형: {question_type}")
        exp_manager.logger.write(f"Fallback Chain: {' → '.join(fallback_chain)}")

    return state
