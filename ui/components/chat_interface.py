# ui/components/chat_interface.py

"""
채팅 인터페이스 UI 컴포넌트

Streamlit 채팅 UI 구성:
- 채팅 히스토리 표시
- 사용자 입력 처리
- Agent 실행 및 답변 표시
"""

# ------------------------- 표준 라이브러리 ------------------------- #
from datetime import datetime

# ------------------------- 서드파티 라이브러리 ------------------------- #
import streamlit as st
from langchain.callbacks import StreamlitCallbackHandler

# ------------------------- 프로젝트 모듈 ------------------------- #
from ui.components.file_download import show_download_success, create_download_button
from src.utils.glossary_extractor import extract_and_save_terms
from ui.components.chat_manager import (
    get_current_messages,
    add_message_to_current_chat,
    export_current_chat
)
from src.evaluation import AnswerEvaluator, save_evaluation_results


# ==================== 채팅 히스토리 관리 ==================== #
# ---------------------- 기존 메시지 표시 ---------------------- #
def display_chat_history():
    """
    현재 채팅의 저장된 히스토리 표시

    chat_manager를 통해 현재 채팅의 메시지를 렌더링
    """
    # 현재 채팅의 모든 메시지 가져오기
    messages = get_current_messages()

    # 모든 메시지 순회
    for idx, message in enumerate(messages):
        role = message["role"]                      # user 또는 assistant
        content = message["content"]                # 메시지 내용

        # 역할별 채팅 버블 표시
        with st.chat_message(role):
            # -------------- 도구 선택 정보 표시 -------------- #
            # assistant 메시지에 도구 선택 정보가 있으면 배지로 표시
            if role == "assistant" and "tool_choice" in message:
                tool_choice = message["tool_choice"]
                tool_labels = {
                    "general": "🗣️ 일반 답변",
                    "search_paper": "📚 RAG 논문 검색",
                    "web_search": "🌐 웹 검색",
                    "glossary": "📖 RAG 용어집",
                    "summarize": "📄 논문 요약",
                    "save_file": "💾 파일 저장"
                }
                tool_label = tool_labels.get(tool_choice, f"🔧 {tool_choice}")
                st.caption(f"**사용된 도구**: {tool_label}")

            st.markdown(content)

            # -------------- 답변 복사 버튼 (assistant만) -------------- #
            if role == "assistant":
                import json
                safe_answer = json.dumps(content)
                unique_id = abs(hash(content + str(idx)))  # idx 추가로 고유 ID 생성

                copy_button_html = f"""
                <button id="copy_history_btn_{unique_id}" onclick="copyHistoryToClipboard_{unique_id}()" style="
                    background-color: #FF4B4B;
                    color: white;
                    border: none;
                    padding: 0.4rem 0.8rem;
                    border-radius: 0.25rem;
                    cursor: pointer;
                    font-size: 0.85rem;
                    font-weight: 500;
                    margin-top: 0.5rem;
                ">📋 복사</button>

                <script>
                function copyHistoryToClipboard_{unique_id}() {{
                    const text = {safe_answer};
                    const button = document.getElementById('copy_history_btn_{unique_id}');

                    if (!navigator.clipboard) {{
                        const textArea = document.createElement('textarea');
                        textArea.value = text;
                        textArea.style.position = 'fixed';
                        textArea.style.left = '-9999px';
                        document.body.appendChild(textArea);
                        textArea.select();
                        try {{
                            document.execCommand('copy');
                            button.textContent = '✅ 복사됨!';
                            setTimeout(() => {{ button.textContent = '📋 복사'; }}, 2000);
                        }} catch (err) {{
                            alert('❌ 복사 실패: ' + err);
                        }}
                        document.body.removeChild(textArea);
                        return;
                    }}

                    navigator.clipboard.writeText(text).then(function() {{
                        button.textContent = '✅ 복사됨!';
                        setTimeout(() => {{ button.textContent = '📋 복사'; }}, 2000);
                    }}, function(err) {{
                        alert('❌ 복사 실패: ' + err);
                    }});
                }}
                </script>
                """
                st.markdown(copy_button_html, unsafe_allow_html=True)

            # -------------- 출처 정보 표시 -------------- #
            # assistant 메시지에 출처가 있으면 expander로 표시
            if role == "assistant" and message.get("sources") and len(message["sources"]) > 0:
                with st.expander("📚 참고 논문"):
                    for doc in message["sources"]:
                        st.markdown(f"""
                        **제목**: {doc.get('title', 'N/A')}
                        **저자**: {doc.get('authors', 'N/A')}
                        **연도**: {doc.get('year', 'N/A')}
                        """)
                        st.divider()


# ==================== 사용자 입력 처리 ==================== #
# ---------------------- 사용자 메시지 추가 ---------------------- #
def add_user_message(prompt: str, exp_manager=None):
    """
    사용자 메시지를 현재 채팅에 추가하고 표시

    Args:
        prompt: 사용자 입력 텍스트
        exp_manager: ExperimentManager 인스턴스 (선택)
    """
    # 현재 채팅에 메시지 추가
    add_message_to_current_chat(role="user", content=prompt)

    # 채팅 버블로 표시
    with st.chat_message("user"):
        st.markdown(prompt)

    # -------------- 사용자 질문 로그 기록 -------------- #
    if exp_manager:
        exp_manager.log_ui_interaction(f"사용자 질문: {prompt}")
        exp_manager.update_metadata(user_query=prompt)


# ---------------------- Agent 응답 처리 ---------------------- #
def handle_agent_response(agent_executor, prompt: str, difficulty: str, exp_manager=None):
    """
    Agent를 실행하고 응답을 처리

    Args:
        agent_executor: Agent 실행기
        prompt: 사용자 질문
        difficulty: 난이도 (easy/hard)
        exp_manager: ExperimentManager 인스턴스 (선택)

    Returns:
        dict: Agent 응답 결과
    """
    # Assistant 채팅 버블 표시
    with st.chat_message("assistant"):
        # 메시지 플레이스홀더 생성
        message_placeholder = st.empty()

        # -------------- StreamlitCallbackHandler 생성 -------------- #
        # Agent 실행 과정을 접힌 상태의 expander에 표시
        process_expander = st.expander("🔍 처리 과정 보기", expanded=False)
        st_callback = StreamlitCallbackHandler(
            parent_container=process_expander,
            expand_new_thoughts=False,              # 새 단계 접힌 상태로
            collapse_completed_thoughts=True        # 완료 단계 자동 접기
        )

        try:
            # -------------- Agent 실행 -------------- #
            if exp_manager:
                exp_manager.log_ui_interaction(f"Agent 실행 시작 (난이도: {difficulty})")
                exp_manager.update_metadata(difficulty=difficulty)

            # 시작 시간 기록
            from datetime import datetime
            start_time = datetime.now()

            # 이전 대화 히스토리 가져오기 (멀티턴 대화 지원)
            from ui.components.chat_manager import get_current_messages
            previous_messages = get_current_messages()

            with st.spinner("🤖 답변 생성 중..."):
                response = agent_executor.invoke(
                    {
                        "question": prompt,
                        "difficulty": difficulty,
                        "messages": previous_messages  # 이전 대화 전달
                    },
                    config={"callbacks": [st_callback]}
                )

            # 종료 시간 계산
            end_time = datetime.now()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # 성공 시 메타데이터 업데이트
            if exp_manager:
                exp_manager.update_metadata(
                    success=True,
                    response_time_ms=response_time_ms
                )

            # -------------- 도구 선택 정보 표시 -------------- #
            tool_choice = response.get("tool_choice", "unknown")
            tool_labels = {
                "general": "🗣️ 일반 답변",
                "search_paper": "📚 RAG 논문 검색",
                "web_search": "🌐 웹 검색",
                "glossary": "📖 RAG 용어집",
                "summarize": "📄 논문 요약",
                "save_file": "💾 파일 저장",
                "text2sql": "📊 통계 조회"
            }
            tool_label = tool_labels.get(tool_choice, f"🔧 {tool_choice}")
            st.caption(f"**사용된 도구**: {tool_label}")

            # -------------- 도구 선택 이유 표시 -------------- #
            routing_reason = response.get("routing_reason")
            routing_method = response.get("routing_method")
            pipeline_description = response.get("pipeline_description")

            if routing_reason or routing_method:
                with st.expander("🔍 도구 선택 이유", expanded=False):
                    if routing_method:
                        method_labels = {
                            "multi_request": "다중 요청 패턴",
                            "question_type": "질문 유형 분석",
                            "llm": "LLM 분석",
                            "keyword_fallback": "키워드 매칭"
                        }
                        method_label = method_labels.get(routing_method, routing_method)
                        st.info(f"**선택 방법**: {method_label}")

                    if routing_reason:
                        st.write(f"**이유**: {routing_reason}")

                    if pipeline_description:
                        st.success(f"**파이프라인**: {pipeline_description}")

            # -------------- 도구 선택 로그 기록 -------------- #
            if exp_manager:
                exp_manager.log_ui_interaction(f"선택된 도구: {tool_choice} ({tool_label})")
                exp_manager.update_metadata(tool_used=tool_choice)

            # -------------- 도구 실행 타임라인 표시 -------------- #
            # response에 tool_timeline이 있으면 모든 이벤트 표시
            if "tool_timeline" in response and response["tool_timeline"]:
                timeline_events = response["tool_timeline"]

                if timeline_events:
                    with st.expander("📋 도구 실행 과정", expanded=False):
                        for idx, event in enumerate(timeline_events, 1):
                            event_type = event.get("event", "unknown")
                            description = event.get("description", "")

                            # 이벤트 타입별 아이콘 및 스타일
                            if event_type == "fallback":
                                from_tool = event.get("from_tool", "unknown")
                                to_tool = event.get("to_tool", "unknown")
                                from_label = tool_labels.get(from_tool, f"🔧 {from_tool}")
                                to_label = tool_labels.get(to_tool, f"🔧 {to_tool}")
                                st.warning(f"**{idx}. 🔄 도구 자동 전환**\n\n{description}\n\n- {from_label} → {to_label}")

                            elif event_type == "pipeline_fallback":
                                from_tool = event.get("from_tool", "unknown")
                                to_tool = event.get("to_tool", "unknown")
                                from_label = tool_labels.get(from_tool, f"🔧 {from_tool}")
                                to_label = tool_labels.get(to_tool, f"🔧 {to_tool}")
                                st.error(f"**{idx}. ⚠️ 파이프라인 도구 대체**\n\n{description}\n\n- {from_label} → {to_label}")

                            elif event_type == "pipeline_progress":
                                tool = event.get("tool", "unknown")
                                tool_label = tool_labels.get(tool, f"🔧 {tool}")
                                pipeline_idx = event.get("pipeline_index", "?")
                                total = event.get("total_tools", "?")
                                st.info(f"**{idx}. ▶️ 다중 요청 진행**\n\n{description}\n\n- 도구: {tool_label} ({pipeline_idx}/{total})")

                            else:
                                st.write(f"**{idx}. {event_type}**: {description}")

            # -------------- 답변 표시 (두 수준으로 분리) -------------- #
            final_answers = response.get("final_answers")
            answer = response.get("final_answer", "답변을 생성할 수 없습니다.")

            if final_answers and isinstance(final_answers, dict) and len(final_answers) == 2:
                # 두 수준의 답변이 있는 경우 탭으로 표시
                level_names = list(final_answers.keys())

                # 한글 라벨 매핑
                level_labels = {
                    "elementary": "초등학생용 (8-13세)",
                    "beginner": "초급자용 (14-22세)",
                    "intermediate": "중급자용 (23-30세)",
                    "advanced": "고급자용 (30세 이상)"
                }

                tab_labels = [level_labels.get(level, level) for level in level_names]
                tabs = st.tabs(tab_labels)

                for tab, level_name in zip(tabs, level_names):
                    with tab:
                        st.markdown(final_answers[level_name])

                # message_placeholder는 안내 메시지 표시
                message_placeholder.info("💡 위 탭에서 두 가지 수준의 답변을 확인하세요!")
            else:
                # 기존 방식 (하나의 답변만)
                message_placeholder.markdown(answer)

            # -------------- 답변 복사 및 저장 버튼 -------------- #
            # 두 수준의 답변을 하나로 합치기 (복사/저장용)
            if final_answers and isinstance(final_answers, dict):
                combined_answer = ""
                level_labels = {
                    "elementary": "초등학생용 (8-13세)",
                    "beginner": "초급자용 (14-22세)",
                    "intermediate": "중급자용 (23-30세)",
                    "advanced": "고급자용 (30세 이상)"
                }
                for level_name, content in final_answers.items():
                    combined_answer += f"### {level_labels.get(level_name, level_name)}\n\n"
                    combined_answer += f"{content}\n\n---\n\n"
                answer_for_export = combined_answer.strip()
            else:
                answer_for_export = answer

            col_copy, col_save = st.columns(2)

            with col_copy:
                # JavaScript 클립보드 복사 버튼 (항상 사용)
                import json
                safe_answer = json.dumps(answer_for_export)
                unique_id = abs(hash(answer_for_export))

                copy_button_html = f"""
                <button id="copy_btn_{unique_id}" onclick="copyToClipboard_{unique_id}()" style="
                    background-color: #FF4B4B;
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 0.25rem;
                    cursor: pointer;
                    width: 100%;
                    font-size: 1rem;
                    font-weight: 500;
                ">📋 복사</button>

                <script>
                function copyToClipboard_{unique_id}() {{
                    const text = {safe_answer};
                    const button = document.getElementById('copy_btn_{unique_id}');

                    // navigator.clipboard API 우선 시도
                    if (navigator.clipboard && navigator.clipboard.writeText) {{
                        navigator.clipboard.writeText(text).then(function() {{
                            button.textContent = '✅ 복사됨!';
                            setTimeout(() => {{ button.textContent = '📋 복사'; }}, 2000);
                        }}, function(err) {{
                            // clipboard API 실패 시 fallback
                            fallbackCopy_{unique_id}(text, button);
                        }});
                    }} else {{
                        // clipboard API 미지원 시 fallback
                        fallbackCopy_{unique_id}(text, button);
                    }}
                }}

                function fallbackCopy_{unique_id}(text, button) {{
                    const textArea = document.createElement('textarea');
                    textArea.value = text;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-9999px';
                    document.body.appendChild(textArea);
                    textArea.select();
                    try {{
                        document.execCommand('copy');
                        button.textContent = '✅ 복사됨!';
                        setTimeout(() => {{ button.textContent = '📋 복사'; }}, 2000);
                    }} catch (err) {{
                        button.textContent = '❌ 복사 실패';
                        setTimeout(() => {{ button.textContent = '📋 복사'; }}, 2000);
                    }}
                    document.body.removeChild(textArea);
                }}
                </script>
                """
                st.markdown(copy_button_html, unsafe_allow_html=True)

            with col_save:
                # 파일명 생성 (마크다운 형식)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"response_{timestamp}.md"

                # 마크다운 형식으로 저장 내용 구성
                markdown_content = f"# LLM 답변\n\n"
                markdown_content += f"**생성 시간**: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}\n\n"
                markdown_content += f"---\n\n{answer_for_export}"

                # 다운로드 버튼
                st.download_button(
                    label="💾 저장",
                    data=markdown_content,
                    file_name=filename,
                    mime="text/markdown",
                    use_container_width=True,
                    key=f"save_{hash(answer_for_export)}"
                )

            # -------------- LLM 응답 로그 기록 -------------- #
            if exp_manager:
                # response.txt 중복 저장 제거 (save_file 도구 실행 시에만 저장)
                # exp_manager.save_output("response.txt", answer)
                exp_manager.log_ui_interaction(f"답변 생성 완료 ({len(answer)} 글자)")

            # -------------- AI/ML 용어 자동 추출 및 저장 -------------- #
            # 용어 추출이 의미 있는 도구만 실행 (text2sql, save_file 제외)
            GLOSSARY_ENABLED_TOOLS = {"general", "search_paper", "web_search", "glossary", "summarize"}

            if tool_choice in GLOSSARY_ENABLED_TOOLS:
                try:
                    if exp_manager:
                        # session_state에서 용어 추출 설정 읽기
                        min_terms = st.session_state.get("glossary_min_terms", 1)
                        max_terms = st.session_state.get("glossary_max_terms", 5)

                        saved_count = extract_and_save_terms(
                            answer=answer_for_export,
                            difficulty=difficulty,
                            min_terms=min_terms,
                            max_terms=max_terms,
                            logger=exp_manager.logger
                        )
                        if saved_count > 0:
                            exp_manager.log_ui_interaction(
                                f"용어집에 {saved_count}개 용어 자동 저장 (설정: {min_terms}-{max_terms}개)"
                            )
                            st.toast(f"✅ {saved_count}개 용어가 용어집에 추가되었습니다!", icon="📚")
                except Exception as e:
                    if exp_manager:
                        exp_manager.logger.write(f"용어 자동 저장 실패: {e}", print_error=True)
            else:
                if exp_manager:
                    exp_manager.log_ui_interaction(f"용어 추출 스킵 (도구: {tool_choice})")

            # -------------- 실시간 답변 품질 평가 -------------- #
            evaluation_result = None
            try:
                if exp_manager:
                    exp_manager.log_ui_interaction("답변 품질 평가 시작")

                with st.spinner("📊 답변 품질 평가 중..."):
                    # 참고 문서 문자열 생성
                    reference_docs = ""
                    if "source_documents" in response and response["source_documents"]:
                        doc_texts = []
                        for doc in response["source_documents"]:
                            metadata = doc.metadata
                            doc_text = f"제목: {metadata.get('title', 'N/A')}\n"
                            doc_text += f"저자: {metadata.get('authors', 'N/A')}\n"
                            doc_text += f"내용: {doc.page_content[:200]}..."
                            doc_texts.append(doc_text)
                        reference_docs = "\n\n".join(doc_texts)
                    else:
                        reference_docs = "참고 문서 없음 (일반 답변)"

                    # 평가 수행
                    evaluator = AnswerEvaluator(exp_manager=exp_manager)
                    evaluation_result = evaluator.evaluate(
                        question=prompt,
                        answer=answer_for_export,
                        reference_docs=reference_docs,
                        difficulty=difficulty
                    )

                    # 평가 결과 DB 저장
                    save_evaluation_results([evaluation_result])

                    # 평가 결과 evaluation 폴더에 저장
                    if exp_manager:
                        exp_manager.save_evaluation_result(evaluation_result)
                        exp_manager.log_ui_interaction(
                            f"평가 완료 - 총점: {evaluation_result.get('total_score', 0)}/40"
                        )

                    st.toast(f"✅ 답변 평가 완료: {evaluation_result.get('total_score', 0)}/40점", icon="📊")

            except Exception as e:
                if exp_manager:
                    exp_manager.logger.write(f"답변 평가 실패: {e}", print_error=True)
                st.warning(f"⚠️ 답변 평가 중 오류 발생: {str(e)}")

            # -------------- 평가 결과 표시 -------------- #
            if evaluation_result:
                with st.expander("📊 답변 품질 평가 결과", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("정확도", f"{evaluation_result.get('accuracy_score', 0)}/10")
                        st.metric("관련성", f"{evaluation_result.get('relevance_score', 0)}/10")

                    with col2:
                        st.metric("난이도 적합성", f"{evaluation_result.get('difficulty_score', 0)}/10")
                        st.metric("출처 명시", f"{evaluation_result.get('citation_score', 0)}/10")

                    st.divider()
                    st.metric("총점", f"{evaluation_result.get('total_score', 0)}/40",
                             delta=None, delta_color="normal")

                    if evaluation_result.get('comment'):
                        st.info(f"💬 **평가 코멘트**\n\n{evaluation_result['comment']}")

            # -------------- 출처 정보 표시 -------------- #
            sources = []
            if "source_documents" in response and response["source_documents"]:
                with st.expander("📚 참고 논문"):
                    for doc in response["source_documents"]:
                        metadata = doc.metadata
                        st.markdown(f"""
                        **제목**: {metadata.get('title', 'N/A')}
                        **저자**: {metadata.get('authors', 'N/A')}
                        **연도**: {metadata.get('year', 'N/A')}
                        """)
                        st.divider()

                        # 출처 정보 저장
                        sources.append(metadata)

            # -------------- 파일 저장 도구 실행 시 다운로드 버튼 -------------- #
            if tool_choice == "save_file":
                st.divider()
                show_download_success()
                create_download_button(
                    content=answer_for_export,
                    filename=f"paper_response_{response.get('timestamp', 'unknown')}.txt"
                )

            # -------------- 메시지 히스토리에 추가 -------------- #
            add_message_to_current_chat(
                role="assistant",
                content=answer_for_export,
                tool_choice=tool_choice,
                sources=sources if sources else None
            )

            # -------------- 전체 대화 outputs 폴더에 저장 -------------- #
            if exp_manager:
                # 현재 채팅의 전체 메시지 가져오기
                from ui.components.chat_manager import get_current_messages
                messages = get_current_messages()
                if messages:
                    exp_manager.save_conversation(messages, difficulty=difficulty)

                # Q&A 완료 분기점
                exp_manager.logger.write_separator()

            return response

        except Exception as e:
            # -------------- 에러 처리 -------------- #
            error_msg = f"❌ 오류 발생: {str(e)}"
            st.error(error_msg)

            # 실패 시 메타데이터 업데이트
            if exp_manager:
                exp_manager.update_metadata(success=False, error=str(e))

            # 로그 기록 (ExperimentManager 사용 시)
            if exp_manager:
                import traceback

                # UI 에러 로그 저장
                error_log = f"""에러 발생 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
질문: {prompt}
난이도: {difficulty}
에러 메시지: {str(e)}

상세 트레이스:
{traceback.format_exc()}
"""
                # UI 폴더에 에러 로그 저장
                error_file = exp_manager.ui_dir / "errors.log"
                with open(error_file, 'a', encoding='utf-8') as f:
                    f.write(error_log)
                    f.write("=" * 80 + "\n\n")

                # 메인 로거에도 기록
                exp_manager.logger.write(f"UI 에러: {e}", print_error=True)
                exp_manager.log_ui_interaction(f"에러 발생: {str(e)}")
                exp_manager.update_metadata(success=False, error=str(e))

            return None


# ==================== 채팅 입력 처리 ==================== #
# ---------------------- 전체 채팅 저장/복사 버튼 ---------------------- #
def render_chat_export_buttons():
    """
    전체 채팅 내역 저장/복사 버튼 표시
    """
    # 현재 채팅에 메시지가 있는지 확인
    messages = get_current_messages()

    if messages:
        col_export_copy, col_export_save = st.columns(2)

        with col_export_copy:
            # 전체 채팅 복사 버튼
            import json
            chat_content = export_current_chat()
            safe_content = json.dumps(chat_content)
            unique_id = abs(hash(chat_content + "export"))

            export_copy_html = f"""
            <button id="export_copy_btn_{unique_id}" onclick="exportCopyToClipboard_{unique_id}()" style="
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 0.25rem;
                cursor: pointer;
                width: 100%;
                font-size: 0.9rem;
                font-weight: 500;
            ">💬 전체 대화 복사</button>

            <script>
            function exportCopyToClipboard_{unique_id}() {{
                const text = {safe_content};
                const button = document.getElementById('export_copy_btn_{unique_id}');

                if (!navigator.clipboard) {{
                    const textArea = document.createElement('textarea');
                    textArea.value = text;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-9999px';
                    document.body.appendChild(textArea);
                    textArea.select();
                    try {{
                        document.execCommand('copy');
                        button.textContent = '✅ 복사됨!';
                        setTimeout(() => {{ button.textContent = '💬 전체 대화 복사'; }}, 2000);
                    }} catch (err) {{
                        alert('❌ 복사 실패: ' + err);
                    }}
                    document.body.removeChild(textArea);
                    return;
                }}

                navigator.clipboard.writeText(text).then(function() {{
                    button.textContent = '✅ 복사됨!';
                    setTimeout(() => {{ button.textContent = '💬 전체 대화 복사'; }}, 2000);
                }}, function(err) {{
                    alert('❌ 복사 실패: ' + err);
                }});
            }}
            </script>
            """
            st.markdown(export_copy_html, unsafe_allow_html=True)

        with col_export_save:
            # 경로 지정 저장 버튼 (마크다운 형식)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_history_{timestamp}.md"

            st.download_button(
                label="💾 경로 지정 저장",
                data=chat_content,
                file_name=filename,
                mime="text/markdown",
                use_container_width=True,
                key=f"export_save_{unique_id}"
            )


# ---------------------- 채팅 입력 UI ---------------------- #
def render_chat_input(agent_executor, difficulty: str, exp_manager=None):
    """
    채팅 입력 UI 렌더링 및 처리

    Args:
        agent_executor: Agent 실행기
        difficulty: 난이도
        exp_manager: ExperimentManager 인스턴스 (선택)
    """
    # 채팅 입력창 표시
    if prompt := st.chat_input("논문에 대해 질문해보세요..."):
        # 사용자 메시지 추가
        add_user_message(prompt, exp_manager=exp_manager)

        # Agent 응답 처리
        handle_agent_response(
            agent_executor=agent_executor,
            prompt=prompt,
            difficulty=difficulty,
            exp_manager=exp_manager
        )
