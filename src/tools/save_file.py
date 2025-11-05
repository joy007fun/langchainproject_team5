# src/tools/save_file.py
"""
파일 저장 도구 모듈

답변 내용을 파일로 저장
타임스탬프 기반 파일명 생성
"""

# ==================== Import ==================== #
from datetime import datetime
import os
from src.agent.state import AgentState


# ==================== 도구 2: 파일 저장 노드 ==================== #
def save_file_node(state: AgentState, exp_manager=None):
    """
    파일 저장 노드: 답변 내용을 파일로 저장

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태
    """
    # -------------- 상태에서 질문 추출 -------------- #
    question = state["question"]                # 사용자 질문

    # -------------- 로깅 -------------- #
    if exp_manager:
        exp_manager.logger.write(f"파일 저장 노드 실행: {question}")

    # -------------- 저장 모드 결정 -------------- #
    # "전체"와 "저장" 키워드가 동시에 있으면 전체 대화 저장, 아니면 단일 답변만 저장
    is_full_save = "전체" in question and "저장" in question

    if exp_manager:
        exp_manager.logger.write(f"저장 모드: {'전체 대화 저장' if is_full_save else '단일 답변 저장'}")

    # -------------- 저장할 내용 확인 -------------- #
    messages = state.get("messages", [])

    if is_full_save and messages:
        # 전체 대화 저장: 마크다운 형식으로 대화 내용 구성
        content_lines = ["# 대화 내용\n"]

        for i, msg in enumerate(messages, 1):
            # 메시지 역할 확인 (user/assistant)
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # 역할에 따라 헤더 설정
            if role == "user":
                header = f"## [{i}] 🙋 사용자"
            elif role == "assistant":
                header = f"## [{i}] 🤖 AI"
            else:
                header = f"## [{i}] {role}"

            # 질의응답 구분하여 추가
            content_lines.append(f"{header}\n\n{content}\n")

        content_to_save = "\n".join(content_lines)
    else:
        # 단일 답변 저장: LLM 답변만 저장 (사용자 질문 제외)
        # 우선순위: tool_result → final_answer → messages의 마지막 assistant 답변
        content_to_save = ""

        # 우선순위 1: tool_result (파이프라인 실행 결과)
        tool_result = state.get("tool_result", "")
        if tool_result and tool_result.strip():
            content_to_save = tool_result
            if exp_manager:
                exp_manager.logger.write(f"저장 출처: tool_result")

        # 우선순위 2: final_answer
        if not content_to_save:
            final_answer = state.get("final_answer", "")
            if final_answer and final_answer.strip():
                content_to_save = final_answer
                if exp_manager:
                    exp_manager.logger.write(f"저장 출처: final_answer")

        # 우선순위 3: messages에서 마지막 assistant 답변
        if not content_to_save and messages:
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if content.strip():
                        content_to_save = content
                        if exp_manager:
                            exp_manager.logger.write(f"저장 출처: messages")
                        break

        # 저장할 내용이 없는 경우
        if not content_to_save or not content_to_save.strip():
            content_to_save = "저장할 내용이 없습니다."
            if exp_manager:
                exp_manager.logger.write(f"경고: 저장할 내용을 찾지 못함")

    if exp_manager:
        exp_manager.logger.write(f"저장할 내용 길이: {len(content_to_save)} 글자")

    # -------------- 파일명 생성 -------------- #
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 타임스탬프 생성

    # 저장 카운터 증가 (세션별 누적 번호)
    save_counter = state.get("save_counter", 0) + 1
    state["save_counter"] = save_counter

    # 파일명 형식: 날짜_시간_response_번호.md
    filename = f"{timestamp}_response_{save_counter}.md"

    if exp_manager:
        exp_manager.logger.write(f"파일명: {filename}")

    # -------------- 파일 저장 -------------- #
    if exp_manager:
        # ExperimentManager의 save_output 메서드 사용
        file_path = exp_manager.save_output(filename, content_to_save)  # 파일 저장

        exp_manager.logger.write(f"파일 저장 완료: {file_path}")

        # 성공 메시지 구성
        answer = f"파일이 성공적으로 저장되었습니다.\n파일 경로: {file_path}"
    else:
        # ExperimentManager 없을 때 (테스트 환경)
        output_dir = "outputs"                  # 기본 출력 디렉토리
        os.makedirs(output_dir, exist_ok=True)  # 디렉토리 생성
        file_path = os.path.join(output_dir, filename)  # 파일 경로 생성

        # 파일 쓰기
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content_to_save)            # 내용 저장

        # 성공 메시지 구성
        answer = f"파일이 성공적으로 저장되었습니다.\n파일 경로: {file_path}"

    # -------------- 최종 답변 저장 -------------- #
    state["final_answer"] = answer              # 성공 메시지 저장

    return state                                # 업데이트된 상태 반환
