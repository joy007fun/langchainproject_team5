# src/agent/nodes.py
"""
Agent 노드 함수 모듈

LangGraph Agent의 노드 함수들:
- router_node: 질문 분석 및 도구 선택
- 6개 도구 노드 (src/tools/에서 import)
"""

# ==================== 라이브러리 Import ==================== #
from datetime import datetime
from src.agent.state import AgentState
from src.llm.client import LLMClient
from src.prompts import get_routing_prompt
from src.agent.config_loader import get_priority_chain, get_max_retries, get_max_validation_retries, get_multi_request_patterns
from src.agent.question_classifier import classify_question

# ==================== 도구 Import ==================== #
from src.tools.general_answer import general_answer_node
from src.tools.save_file import save_file_node
from src.tools.search_paper import search_paper_node
from src.tools.web_search import web_search_node
from src.tools.glossary import glossary_node
from src.tools.summarize import summarize_node
from src.tools.text2sql import text2sql


# ==================== 라우터 노드 ==================== #
# ---------------------- 질문 분석 및 도구 선택 ---------------------- #
def router_node(state: AgentState, exp_manager=None):
    """
    라우터 노드: 질문을 분석하여 적절한 도구 선택

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태 (tool_choice 포함)
    """
    # -------------- 상태에서 질문 추출 -------------- #
    question = state["question"]                # 사용자 질문

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write(f"라우터 노드 실행: {question}")

    # -------------- Multi-turn 맥락 참조 감지 -------------- #
    # 대명사나 맥락 참조 표현이 있으면 이전 대화 컨텍스트를 고려해야 함
    contextual_keywords = ["관련", "그거", "이거", "저거", "해당", "방금", "위", "앞서", "이전", "그"]
    has_contextual_ref = any(kw in question for kw in contextual_keywords)

    # 명확한 다중 요청 키워드 (저장, 요약 등)가 있으면 패턴 매칭 우선 시도
    multi_request_indicators = ["저장", "요약", "정리"]
    has_multi_request_indicator = any(kw in question for kw in multi_request_indicators)

    # 맥락 참조가 있어도 명확한 다중 요청 키워드가 있으면 패턴 매칭 시도
    skip_pattern_matching = has_contextual_ref and len(state.get("messages", [])) > 1 and not has_multi_request_indicator

    if skip_pattern_matching:
        # 맥락 참조가 있고 다중 요청 아닌 경우만 패턴 매칭 건너뛰기
        if exp_manager:
            exp_manager.logger.write(f"Multi-turn 맥락 참조 감지: 패턴 매칭 건너뛰고 LLM 라우팅 사용")
        # 패턴 매칭을 건너뛰고 LLM 라우팅으로 진행
        pass
    else:
        # -------------- 다중 요청 감지 (YAML 패턴 기반) -------------- #
        # YAML 파일에서 패턴 로드 (우선순위 정렬됨)
        multi_request_patterns = get_multi_request_patterns()

        # 다중 요청 패턴 확인 (우선순위 높은 순서대로)
        for pattern in multi_request_patterns:
            keywords = pattern.get("keywords", [])
            exclude_keywords = pattern.get("exclude_keywords", [])
            tools = pattern.get("tools", [])

            # 모든 키워드가 질문에 포함되는지 확인
            keywords_match = all(kw in question for kw in keywords)

            # 제외 키워드가 하나라도 있으면 패턴 불일치
            exclude_match = any(ex_kw in question for ex_kw in exclude_keywords) if exclude_keywords else False

            if keywords_match and not exclude_match:
                description = pattern.get('description', 'N/A')

                if exp_manager:
                    exp_manager.logger.write(f"다중 요청 감지: {keywords} (제외: {exclude_keywords}) → {tools}")
                    exp_manager.logger.write(f"패턴 설명: {description}")
                    if len(tools) > 1:
                        exp_manager.logger.write(f"순차 실행 도구: {' → '.join(tools)}")
                    else:
                        exp_manager.logger.write(f"단일 도구 실행: {tools[0]}")

                # tool_pipeline 설정 (순차 실행 도구 목록)
                state["tool_pipeline"] = tools
                state["tool_choice"] = tools[0]  # 첫 번째 도구부터 실행
                state["pipeline_index"] = 1      # 첫 번째 도구 실행 후 index는 1

                # 도구 선택 이유 및 방법 기록
                state["routing_method"] = "pattern_based"
                state["routing_reason"] = f"패턴 매칭: {description}"

                if len(tools) > 1:
                    state["pipeline_description"] = f"순차 실행: {' → '.join(tools)}"
                else:
                    state["pipeline_description"] = f"단일 도구: {tools[0]}"

                return state

    # -------------- 단일 요청 처리 (기존 로직) -------------- #
    # 난이도 추출 (프롬프트 포맷팅 전에 필요)
    difficulty = state.get("difficulty", "easy")  # 난이도 (기본값: easy)

    # ========== 우선순위 1: 질문 유형 기반 도구 선택 (가장 정확) ==========
    question_type = state.get("question_type", "")
    fallback_chain = state.get("fallback_chain", [])

    # 질문 유형별 도구 매핑
    tool_choice = None
    if question_type and fallback_chain:
        # fallback_chain의 첫 번째 도구를 우선 사용
        tool_choice = fallback_chain[0]
        if exp_manager:
            exp_manager.logger.write(f"질문 유형 기반 라우팅: {question_type} → {tool_choice}")

        # 도구 선택 이유 및 방법 기록
        state["routing_method"] = "question_type"
        state["routing_reason"] = f"질문 유형 '{question_type}'에 가장 적합한 도구"

    # ========== 우선순위 2: LLM 라우팅 (보조) ==========
    if tool_choice is None:
        # JSON 프롬프트 로드
        routing_prompt_template = get_routing_prompt()    # JSON 파일에서 프롬프트 로드

        # Multi-turn 지원: 이전 대화 컨텍스트 추출 (최근 3개 메시지)
        messages = state.get("messages", [])
        context = ""
        if len(messages) > 1:
            recent_messages = messages[-3:]  # 최근 3개 메시지
            context = "\n\n[이전 대화 컨텍스트]\n"
            for msg in recent_messages[:-1]:  # 마지막 메시지(현재 질문)는 제외
                role = "사용자" if hasattr(msg, 'type') and msg.type == "human" else "AI"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                context += f"{role}: {content[:200]}...\n" if len(content) > 200 else f"{role}: {content}\n"

        # 프롬프트에 컨텍스트 추가
        base_prompt = routing_prompt_template.format(question=question, difficulty=difficulty)
        routing_prompt = f"{context}{base_prompt}" if context else base_prompt

        # 난이도별 LLM 초기화
        llm_client = LLMClient.from_difficulty(
            difficulty=difficulty,
            logger=exp_manager.logger if exp_manager else None
        )

        # LLM 호출
        raw_response = llm_client.llm.invoke(routing_prompt).content.strip()  # 도구 선택

        # 마크다운 코드 펜스 제거 (LLM이 ```json ... ``` 형식으로 응답하는 경우 처리)
        cleaned_response = raw_response
        if "```" in cleaned_response:
            # ```json, ```, 또는 ```python 등 모든 코드 펜스 제거
            lines = cleaned_response.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned_response = "\n".join(lines).strip()

        # 디버깅: 정제된 응답 로깅
        if exp_manager:
            exp_manager.logger.write(f"정제된 응답 (파싱 전): {cleaned_response[:200]}...")

        # 응답 파싱: JSON 형식이면 JSON으로, 아니면 첫 단어 추출
        tool_choice = "general"  # 기본값

        # 1. JSON 파싱 시도
        if cleaned_response.strip().startswith("{"):
            try:
                import json
                parsed = json.loads(cleaned_response)

                # {"tools": [{"name": "xxx", "query": "..."}]} 형식
                if "tools" in parsed and len(parsed["tools"]) > 0:
                    tool_info = parsed["tools"][0]
                    tool_name = tool_info.get("name", "general")

                    # ✅ query 필드 추출 (Multi-turn 지원)
                    if "query" in tool_info and tool_info["query"]:
                        refined_query = tool_info["query"].strip()
                        if refined_query:
                            state["refined_query"] = refined_query
                            if exp_manager:
                                exp_manager.logger.write(f"재작성된 질문: {refined_query}")

                    # 도구명 추출 (full name이 아닌 짧은 이름으로 매핑)
                    if ("search_paper" in tool_name.lower() or "paper" in tool_name.lower() or "논문" in tool_name.lower() or
                        "arxiv" in tool_name.lower() or "검색" in tool_name.lower() or "찾" in tool_name.lower() or
                        "탐색" in tool_name.lower() or "retrieval" in tool_name.lower() or "학술" in tool_name.lower()):
                        tool_choice = "search_paper"
                    elif ("web_search" in tool_name.lower() or "web" in tool_name.lower() or "웹" in tool_name.lower() or "위키" in tool_name.lower() or
                          "인터넷" in tool_name.lower() or "온라인" in tool_name.lower() or "뉴스" in tool_name.lower()):
                        tool_choice = "web_search"
                    elif ("glossary" in tool_name.lower() or "용어" in tool_name.lower() or "정의" in tool_name.lower() or
                          "뭐야" in tool_name.lower() or "뭔지" in tool_name.lower() or "란" in tool_name.lower() or
                          "의미" in tool_name.lower() or "설명" in tool_name.lower()):
                        tool_choice = "glossary"
                    elif ("summarize" in tool_name.lower() or "요약" in tool_name.lower() or
                          "정리" in tool_name.lower() or "summary" in tool_name.lower()):
                        tool_choice = "summarize"
                    elif ("text2sql" in tool_name.lower() or "sql" in tool_name.lower() or "통계" in tool_name.lower() or
                          "데이터베이스" in tool_name.lower() or "조회" in tool_name.lower() or "쿼리" in tool_name.lower()):
                        tool_choice = "text2sql"
                    elif "save" in tool_name.lower() or "저장" in tool_name.lower():
                        tool_choice = "save_file"
                    else:
                        tool_choice = "general"
                elif "tool" in parsed:
                    # {"tool": "xxx"} 형식
                    tool_choice = parsed["tool"]

                # JSON 파싱 성공 시 routing_method 설정
                state["routing_method"] = "llm"
                state["routing_reason"] = f"LLM이 질문 분석 후 '{tool_choice}' 도구 선택"

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                # JSON 파싱 실패 시 키워드 기반 폴백 매칭
                if exp_manager:
                    exp_manager.logger.write(f"JSON 파싱 실패: {str(e)}", print_error=True)

                # ✅ 파싱 실패해도 query 필드 추출 시도 (regex 사용)
                import re
                query_match = re.search(r'"query"\s*:\s*"([^"]+)"', cleaned_response)
                if query_match:
                    refined_query = query_match.group(1).strip()
                    if refined_query:
                        state["refined_query"] = refined_query
                        if exp_manager:
                            exp_manager.logger.write(f"재작성된 질문 (regex 추출): {refined_query}")

                # 사용자 질문과 LLM 응답 모두 체크 (대소문자 무시)
                question_lower = question.lower()
                response_lower = raw_response.lower()

                # 우선순위 1: 사용자 질문에 "용어" 명시적으로 포함된 경우
                if "용어" in question_lower:
                    tool_choice = "glossary"
                # 우선순위 2: 질문에 용어 정의 패턴이 있는 경우
                elif any(pattern in question_lower for pattern in ["뭐야", "뭔가", "뭔지", "무엇", "정의", "의미", "설명해"]) and not any(kw in question_lower for kw in ["논문", "연구", "찾아"]):
                    tool_choice = "glossary"
                # 우선순위 3: LLM 응답 기반 키워드 매칭
                elif any(keyword in response_lower for keyword in ["search_paper", "paper", "논문", "arxiv", "검색", "찾", "탐색", "retrieval", "학술"]):
                    tool_choice = "search_paper"
                elif any(keyword in response_lower for keyword in ["web_search", "web", "웹", "위키", "인터넷", "온라인", "뉴스"]):
                    tool_choice = "web_search"
                elif any(keyword in response_lower for keyword in ["glossary", "용어", "정의", "뭐야", "뭔지", "란", "의미", "설명"]):
                    tool_choice = "glossary"
                elif any(keyword in response_lower for keyword in ["summarize", "요약", "정리", "summary"]):
                    tool_choice = "summarize"
                elif any(keyword in response_lower for keyword in ["text2sql", "sql", "통계", "데이터베이스", "조회", "쿼리"]):
                    tool_choice = "text2sql"
                elif any(keyword in response_lower for keyword in ["save", "저장"]):
                    tool_choice = "save_file"
                else:
                    tool_choice = "general"

                # 키워드 폴백 시 routing_method 설정
                state["routing_method"] = "keyword_fallback"
                state["routing_reason"] = f"LLM 파싱 실패로 키워드 기반 매칭하여 '{tool_choice}' 도구 선택"

                if exp_manager:
                    exp_manager.logger.write(f"키워드 기반 폴백 매칭 결과: {tool_choice}")
        else:
            # 2. 일반 텍스트: 첫 번째 단어만 추출
            tool_choice = cleaned_response.split()[0] if cleaned_response else "general"

        # 유효한 도구 목록
        valid_tools = ["general", "glossary", "search_paper", "web_search", "summarize", "text2sql", "save_file"]

        # 유효하지 않은 도구명이면 general로 폴백
        if tool_choice not in valid_tools:
            if exp_manager:
                exp_manager.logger.write(f"⚠️ 유효하지 않은 도구: {tool_choice} → general로 폴백", print_error=True)
            tool_choice = "general"

        # 로깅
        if exp_manager:
            exp_manager.logger.write(f"LLM 라우팅 결정 (원본): {raw_response[:100]}...")
            exp_manager.logger.write(f"LLM 라우팅 결정 (파싱): {tool_choice}")

    # 최종 로깅
    if exp_manager:
        exp_manager.logger.write(f"최종 선택 도구: {tool_choice}")

    # 상태 업데이트
    state["tool_choice"] = tool_choice          # 선택된 도구 저장
    state["tool_pipeline"] = [tool_choice]      # 단일 도구도 파이프라인으로 관리
    state["pipeline_index"] = 1                 # 단일 도구 실행 후 종료

    return state                                # 업데이트된 상태 반환


# ==================== Text-to-SQL 노드 ==================== #
# ---------------------- 논문 통계 정보 조회 ---------------------- #
def text2sql_node(state: AgentState, exp_manager=None):
    """
    Text-to-SQL 노드: 자연어 질문을 SQL로 변환하여 논문 통계 조회

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태 (final_answer 포함)
    """
    # -------------- 상태에서 질문 추출 -------------- #
    question = state["question"]                # 사용자 질문

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write(f"Text-to-SQL 노드 실행: {question}")

    # -------------- Text-to-SQL 도구 호출 -------------- #
    try:
        result = text2sql.run(question)         # Tool 객체의 run() 메서드 호출

        # -------------- 로깅 -------------- #
        if exp_manager:
            exp_manager.logger.write(f"SQL 실행 완료: {len(result)} 글자")

        # -------------- 최종 답변 저장 -------------- #
        state["final_answer"] = result          # 통계 조회 결과 저장

    except Exception as e:
        # -------------- 오류 처리 -------------- #
        if exp_manager:
            exp_manager.logger.write(f"Text-to-SQL 실행 오류: {e}", print_error=True)

        state["final_answer"] = f"논문 통계 조회 중 오류가 발생했습니다: {str(e)}"

    return state                                # 업데이트된 상태 반환


# ==================== Fallback Router 노드 ==================== #
# ---------------------- 도구 실패 시 다음 도구 선택 ---------------------- #
def fallback_router_node(state: AgentState, exp_manager=None):
    """
    Fallback Router 노드: 도구 실행 실패 시 다음 우선순위 도구 선택

    파이프라인 실행 중이면 실패한 도구를 대체 도구로 교체하고 파이프라인 계속 진행

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태 (tool_choice 포함)
    """
    # -------------- 도구별 Fallback 매핑 (파이프라인용) -------------- #
    TOOL_FALLBACKS = {
        "search_paper": "web_search",    # 논문 검색 실패 → 웹 검색
        "web_search": "general",         # 웹 검색 실패 → 일반 답변
        "summarize": "general",          # 요약 실패 → 일반 답변
        "glossary": "general",           # 용어 검색 실패 → 일반 답변
        "text2sql": "general",           # SQL 실패 → 일반 답변
    }

    # -------------- 현재 상태 정보 추출 -------------- #
    question = state["question"]
    failed_tool = state.get("tool_choice", "unknown")
    failure_reason = state.get("failure_reason", "알 수 없는 이유")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    fallback_chain = state.get("fallback_chain", [])
    failed_tools = state.get("failed_tools", [])

    # 파이프라인 정보
    tool_pipeline = state.get("tool_pipeline", [])
    pipeline_index = state.get("pipeline_index", 0)
    is_pipeline = len(tool_pipeline) > 1

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write("=" * 60)
        exp_manager.logger.write("Fallback Router 실행")
        exp_manager.logger.write(f"실패한 도구: {failed_tool}")
        exp_manager.logger.write(f"실패 사유: {failure_reason}")
        exp_manager.logger.write(f"재시도 횟수: {retry_count}/{max_retries}")
        if is_pipeline:
            exp_manager.logger.write(f"파이프라인 모드: {' → '.join(tool_pipeline)}")
            exp_manager.logger.write(f"현재 인덱스: {pipeline_index - 1}")

    # -------------- 실패한 도구 기록 -------------- #
    if failed_tool not in failed_tools:
        failed_tools.append(failed_tool)
        state["failed_tools"] = failed_tools

    # -------------- 재시도 횟수 증가 -------------- #
    retry_count += 1
    state["retry_count"] = retry_count

    # -------------- 최대 재시도 초과 확인 -------------- #
    if retry_count > max_retries:
        if exp_manager:
            exp_manager.logger.write(f"최대 재시도 횟수 초과 ({max_retries}회)")
            exp_manager.logger.write("최종 Fallback: general 도구로 강제 전환")

        state["tool_choice"] = "general"

        # 파이프라인 모드: general로 교체하고 계속 진행
        if is_pipeline:
            # 현재 도구를 general로 교체
            current_index = pipeline_index - 1
            if 0 <= current_index < len(tool_pipeline):
                tool_pipeline[current_index] = "general"
                state["tool_pipeline"] = tool_pipeline
                if exp_manager:
                    exp_manager.logger.write(f"파이프라인 업데이트: {' → '.join(tool_pipeline)}")

        state["tool_status"] = "pending"  # 상태 리셋 (재실행 가능하도록)
        return state

    # -------------- 파이프라인 모드: 도구 대체 로직 -------------- #
    if is_pipeline:
        # 실패한 도구에 대한 Fallback 도구 확인
        fallback_tool = TOOL_FALLBACKS.get(failed_tool)

        if fallback_tool:
            if exp_manager:
                exp_manager.logger.write(f"파이프라인 도구 대체: {failed_tool} → {fallback_tool}")

            # 파이프라인에서 실패한 도구를 Fallback 도구로 교체
            current_index = pipeline_index - 1
            if 0 <= current_index < len(tool_pipeline):
                tool_pipeline[current_index] = fallback_tool
                state["tool_pipeline"] = tool_pipeline
                state["tool_choice"] = fallback_tool
                state["tool_status"] = "pending"  # 상태 리셋

                if exp_manager:
                    exp_manager.logger.write(f"파이프라인 업데이트: {' → '.join(tool_pipeline)}")
                    exp_manager.logger.write(f"다음 도구 실행: {fallback_tool}")
                    exp_manager.logger.write("=" * 60)

                # 타임라인 기록
                timeline = state.get("tool_timeline", [])
                timeline.append({
                    "timestamp": datetime.now().isoformat(),
                    "event": "pipeline_fallback",
                    "from_tool": failed_tool,
                    "to_tool": fallback_tool,
                    "failure_reason": failure_reason,
                    "retry_count": retry_count,
                    "pipeline_index": current_index,
                    "description": f"파이프라인 도구 전환: '{failed_tool}' 실패 → '{fallback_tool}'로 대체 ({failure_reason})"
                })
                state["tool_timeline"] = timeline

                return state

        # Fallback 도구가 없으면 general로 대체
        if exp_manager:
            exp_manager.logger.write(f"{failed_tool}에 대한 Fallback 도구 없음 → general 사용")

        current_index = pipeline_index - 1
        if 0 <= current_index < len(tool_pipeline):
            tool_pipeline[current_index] = "general"
            state["tool_pipeline"] = tool_pipeline
            state["tool_choice"] = "general"
            state["tool_status"] = "pending"

            if exp_manager:
                exp_manager.logger.write(f"파이프라인 업데이트: {' → '.join(tool_pipeline)}")
                exp_manager.logger.write("=" * 60)

            return state

    # -------------- 단일 도구 모드: 기존 Fallback Chain 로직 -------------- #
    next_tool = None

    for tool in fallback_chain:
        if tool not in failed_tools:
            next_tool = tool
            break

    # 모든 도구 시도 완료
    if next_tool is None:
        if exp_manager:
            exp_manager.logger.write("모든 도구 시도 완료")
            exp_manager.logger.write("최종 Fallback: general 도구 선택")

        next_tool = "general"

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write(f"다음 도구로 전환: {next_tool}")
        exp_manager.logger.write(f"전환 이유: {failed_tool} 도구가 실패했기 때문")
        exp_manager.logger.write(f"Fallback Chain: {' → '.join(fallback_chain)}")
        exp_manager.logger.write("=" * 60)

    # -------------- 상태 업데이트 -------------- #
    state["tool_choice"] = next_tool

    # -------------- 타임라인 기록 -------------- #
    timeline = state.get("tool_timeline", [])
    timeline.append({
        "timestamp": datetime.now().isoformat(),
        "event": "fallback",
        "from_tool": failed_tool,
        "to_tool": next_tool,
        "failure_reason": failure_reason,
        "retry_count": retry_count,
        "description": f"도구 자동 전환: '{failed_tool}' 실패 (사유: {failure_reason}) → '{next_tool}'로 변경"
    })
    state["tool_timeline"] = timeline

    return state


# ==================== Router 검증 노드 ==================== #
# ---------------------- Router 선택 검증 및 재라우팅 ---------------------- #
def validate_tool_choice_node(state: AgentState, exp_manager=None):
    """
    Router 검증 노드: Router가 선택한 도구가 적절한지 LLM으로 검증

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태 (validation_failed 포함)
    """
    # -------------- 상태 정보 추출 -------------- #
    question = state["question"]
    tool_choice = state.get("tool_choice", "general")
    validation_retries = state.get("validation_retries", 0)
    max_validation = state.get("max_validation", 2)

    # -------------- 도구 설명 --------- ---- #
    TOOL_DESCRIPTIONS = {
        "general": "일반 질문에 LLM 지식으로 답변",
        "glossary": "AI/ML 용어 정의 검색",
        "search_paper": "논문 DB에서 RAG 검색",
        "web_search": "웹에서 최신 논문 검색",
        "summarize": "논문 요약 생성",
        "text2sql": "논문 통계 정보 SQL 조회",
        "save_file": "답변을 파일로 저장"
    }

    tool_desc = TOOL_DESCRIPTIONS.get(tool_choice, "알 수 없는 도구")

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write("=" * 60)
        exp_manager.logger.write("Router 검증 시작")
        exp_manager.logger.write(f"선택된 도구: {tool_choice}")
        exp_manager.logger.write(f"도구 설명: {tool_desc}")

    # -------------- 검증 프롬프트 생성 -------------- #
    validation_prompt = f"""질문: {question}

선택된 도구: {tool_choice}
도구 설명: {tool_desc}

이 도구 선택이 질문에 적절한가요?

- yes: 적절함 (도구를 사용하여 질문에 답변 가능)
- no: 부적절함 (다른 도구를 사용해야 함)

답변 (yes/no):"""

    # -------------- LLM 초기화 -------------- #
    difficulty = state.get("difficulty", "easy")
    llm_client = LLMClient.from_difficulty(
        difficulty=difficulty,
        logger=exp_manager.logger if exp_manager else None
    )

    # -------------- LLM 호출 -------------- #
    try:
        response = llm_client.llm.invoke(validation_prompt).content.strip().lower()

        # 응답 파싱
        is_valid = "yes" in response or "적절" in response

        # -------------- 검증 결과 처리 -------------- #
        if is_valid:
            if exp_manager:
                exp_manager.logger.write("검증 결과: 적절함 (PASS)")
                exp_manager.logger.write("=" * 60)

            state["validation_failed"] = False

        else:
            if exp_manager:
                exp_manager.logger.write("검증 결과: 부적절함 (FAIL)")

            # 검증 재시도 횟수 증가
            validation_retries += 1
            state["validation_retries"] = validation_retries

            # 최대 검증 재시도 초과 확인
            if validation_retries > max_validation:
                if exp_manager:
                    exp_manager.logger.write(f"최대 검증 재시도 초과 ({max_validation}회)")
                    exp_manager.logger.write("강제로 general 도구 선택")
                    exp_manager.logger.write("=" * 60)

                state["tool_choice"] = "general"
                state["validation_failed"] = False  # 더 이상 재검증 안 함

            else:
                if exp_manager:
                    exp_manager.logger.write(f"재라우팅 진행 (재시도 {validation_retries}/{max_validation})")
                    exp_manager.logger.write("=" * 60)

                state["validation_failed"] = True

        return state

    except Exception as e:
        if exp_manager:
            exp_manager.logger.write(f"검증 실패: {e}", print_error=True)
            exp_manager.logger.write("검증 통과로 간주")
            exp_manager.logger.write("=" * 60)

        # 검증 실패 시 통과로 간주
        state["validation_failed"] = False
        return state


# ==================== 최종 Fallback 노드 ==================== #
# ---------------------- 강제로 general 도구 실행 ---------------------- #
def final_fallback_node(state: AgentState, exp_manager=None):
    """
    최종 Fallback 노드: 모든 시도 실패 시 general 도구 강제 실행

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태
    """
    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write("=" * 60)
        exp_manager.logger.write("최종 Fallback 노드 실행")
        exp_manager.logger.write("general 도구로 강제 전환")
        exp_manager.logger.write("=" * 60)

    # -------------- general 도구 실행 -------------- #
    return general_answer_node(state, exp_manager)


# ==================== Export 목록 ==================== #
__all__ = [
    'router_node',
    'general_answer_node',
    'save_file_node',
    'search_paper_node',
    'web_search_node',
    'glossary_node',
    'summarize_node',
    'text2sql_node',
    'fallback_router_node',
    'validate_tool_choice_node',
    'final_fallback_node',
]
