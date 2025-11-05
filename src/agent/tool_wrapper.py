# src/agent/tool_wrapper.py
"""
도구 래퍼 모듈

각 도구 노드를 래핑하여 tool_status를 자동으로 설정합니다.
Fallback Chain 메커니즘에 필요한 상태 업데이트를 처리합니다.
"""

# ------------------------- 프로젝트 모듈 ------------------------- #
from src.agent.state import AgentState
from src.agent.failure_detector import is_tool_failed
from datetime import datetime
from typing import Callable


def wrap_tool_node(tool_node_func: Callable, tool_name: str) -> Callable:
    """
    도구 노드를 래핑하여 tool_status 자동 설정

    Args:
        tool_node_func: 원본 도구 노드 함수
        tool_name: 도구 이름

    Returns:
        Callable: 래핑된 도구 노드 함수
    """
    def wrapped_tool_node(state: AgentState, exp_manager=None) -> AgentState:
        """
        래핑된 도구 노드 함수

        Args:
            state: Agent 상태
            exp_manager: ExperimentManager 인스턴스

        Returns:
            AgentState: 업데이트된 상태
        """
        # -------------- 타임라인 기록 (실행 전) -------------- #
        timeline = state.get("tool_timeline", [])
        timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "tool_start",
            "tool": tool_name,
            "retry_count": state.get("retry_count", 0)
        })
        state["tool_timeline"] = timeline

        # -------------- 원본 도구 실행 -------------- #
        try:
            state = tool_node_func(state, exp_manager)

            # -------------- 실행 결과 확인 -------------- #
            final_answer = state.get("final_answer", "")

            # general 도구는 fallback이므로 항상 성공 처리
            if tool_name == "general":
                state["tool_status"] = "success"
                state["failure_reason"] = ""

                if exp_manager:
                    exp_manager.logger.write(f"도구 실행 성공: {tool_name} (fallback 도구)")
            else:
                # 실패 패턴 감지 (general 제외)
                is_failed, failure_reason = is_tool_failed(final_answer)

                if is_failed:
                    # 실패
                    state["tool_status"] = "failed"
                    state["failure_reason"] = failure_reason

                    if exp_manager:
                        exp_manager.logger.write(f"도구 실행 실패 감지: {tool_name}")
                        exp_manager.logger.write(f"실패 사유: {failure_reason}")

                else:
                    # 성공
                    state["tool_status"] = "success"
                    state["failure_reason"] = ""  # 성공 시 초기화

                    if exp_manager:
                        exp_manager.logger.write(f"도구 실행 성공: {tool_name}")

        except Exception as e:
            # -------------- 예외 발생 시 -------------- #
            state["tool_status"] = "error"
            state["failure_reason"] = f"예외 발생: {str(e)}"
            state["final_answer"] = f"도구 실행 중 오류 발생: {str(e)}"

            if exp_manager:
                exp_manager.logger.write(f"도구 실행 오류: {tool_name}", print_error=True)
                exp_manager.logger.write(f"오류 내용: {str(e)}", print_error=True)

        # -------------- 타임라인 기록 (실행 후) -------------- #
        timeline = state.get("tool_timeline", [])
        timeline_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "tool_end",
            "tool": tool_name,
            "status": state.get("tool_status", "unknown"),
            "retry_count": state.get("retry_count", 0)
        }

        # 실패한 경우 사유 추가
        if state.get("tool_status") in ["failed", "error"]:
            timeline_entry["failure_reason"] = state.get("failure_reason", "")

        timeline.append(timeline_entry)
        state["tool_timeline"] = timeline

        return state

    return wrapped_tool_node
