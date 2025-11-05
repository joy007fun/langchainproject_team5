# ui/components/sidebar.py

"""
사이드바 UI 컴포넌트

Streamlit 사이드바 구성 요소:
- 난이도 설명 및 선택 (Easy/Hard)
- 새 채팅 버튼 - 선택된 난이도로 채팅 생성
- 채팅 목록 (ChatGPT 스타일)
- 설정 정보 표시
"""

# ------------------------- 표준 라이브러리 ------------------------- #
from datetime import datetime, timedelta

# ------------------------- 서드파티 라이브러리 ------------------------- #
import streamlit as st

# ------------------------- 프로젝트 모듈 ------------------------- #
from ui.components.chat_manager import (
    create_new_chat,
    switch_chat,
    delete_chat,
    get_chat_list,
    get_current_difficulty,
    export_chat
)
from ui.components.storage import (
    save_chats_to_local_storage,
    clear_local_storage,
    get_storage_info
)


# ==================== 사이드바 렌더링 함수 ==================== #
# ---------------------- 날짜별 그룹화 ---------------------- #
def group_chats_by_date(chat_list):
    """
    채팅 목록을 날짜별로 그룹화 (ChatGPT 스타일)

    Returns:
        dict: {"오늘": [...], "어제": [...], "지난 7일": [...], "그 이전": [...]}
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_ago = today_start - timedelta(days=7)

    groups = {
        "오늘": [],
        "어제": [],
        "지난 7일": [],
        "그 이전": []
    }

    for chat in chat_list:
        # 문자열을 datetime으로 변환
        created_at = datetime.strptime(chat["created_at"], "%Y-%m-%d %H:%M:%S")

        if created_at >= today_start:
            groups["오늘"].append(chat)
        elif created_at >= yesterday_start:
            groups["어제"].append(chat)
        elif created_at >= week_ago:
            groups["지난 7일"].append(chat)
        else:
            groups["그 이전"].append(chat)

    # 빈 그룹 제거
    return {k: v for k, v in groups.items() if v}


# ---------------------- 난이도 선택 사이드바 ---------------------- #
def render_sidebar(exp_manager=None):
    """
    사이드바 UI 렌더링

    Args:
        exp_manager: ExperimentManager 인스턴스 (선택)

    Returns:
        str: 선택된 난이도 (easy 또는 hard)
    """
    with st.sidebar:
        # -------------- 난이도 설정 섹션 -------------- #
        st.markdown("### ⚙️ 설정")

        # 다크 모드 토글
        if "dark_mode" not in st.session_state:
            st.session_state.dark_mode = False

        dark_mode = st.toggle("🌙 다크 모드", value=st.session_state.dark_mode, key="dark_mode_toggle")

        # 다크 모드 CSS 적용
        if dark_mode:
            st.markdown("""
            <style>
            :root {
                --background-color: #0E1117;
                --secondary-background-color: #262730;
                --text-color: #FAFAFA;
            }
            .stApp {
                background-color: #0E1117;
                color: #FAFAFA;
            }
            .stSidebar {
                background-color: #262730;
            }
            .stChatMessage {
                background-color: #262730;
            }
            .stTextInput > div > div > input {
                background-color: #262730;
                color: #FAFAFA;
            }
            </style>
            """, unsafe_allow_html=True)

            st.session_state.dark_mode = True

            if exp_manager:
                exp_manager.log_ui_interaction("다크 모드 활성화")
        else:
            st.session_state.dark_mode = False

        st.divider()

        # 난이도 설명 (위쪽에 배치)
        with st.expander("ℹ️ 난이도 설명", expanded=False):
            st.markdown("""
            **🟢 초급 모드**:
            - 쉬운 용어 사용
            - 비유와 예시 활용
            - 수식 최소화

            **🔴 전문가 모드**:
            - 전문 용어 사용
            - 수식 및 알고리즘 상세 설명
            - 기술적 세부사항 포함
            """)

        # 현재 채팅이 있으면 그 난이도를 기본값으로
        current_difficulty = get_current_difficulty()
        default_index = 0 if current_difficulty == "easy" else 1 if current_difficulty else 0

        # 난이도 선택 라디오 버튼 (콜백 제거)
        difficulty = st.radio(
            "난이도 선택",
            options=["easy", "hard"],
            format_func=lambda x: "🟢 초급" if x == "easy" else "🔴 전문가",
            index=default_index,
            help="답변의 난이도를 선택하세요",
            key="difficulty_selector",
            horizontal=True
        )

        # 새 채팅 버튼
        if st.button("➕ 새 채팅", use_container_width=True, type="primary"):
            selected_difficulty = st.session_state.difficulty_selector
            create_new_chat(selected_difficulty)

            if exp_manager:
                exp_manager.log_ui_interaction(f"새 채팅 생성: 난이도={selected_difficulty}")

            st.rerun()

        # 구분선 추가
        st.divider()

        # -------------- 용어 추출 설정 섹션 -------------- #
        st.markdown("### 📖 용어 추출 설정")

        # session_state 초기화 (위젯 키도 함께 초기화)
        if "glossary_min_terms" not in st.session_state:
            st.session_state.glossary_min_terms = 1
        if "glossary_max_terms" not in st.session_state:
            st.session_state.glossary_max_terms = 5
        if "glossary_slider" not in st.session_state:
            st.session_state.glossary_slider = (1, 5)
        if "glossary_min_input" not in st.session_state:
            st.session_state.glossary_min_input = 1
        if "glossary_max_input" not in st.session_state:
            st.session_state.glossary_max_input = 5

        # 콜백 함수: 슬라이더 변경 시 session_state 업데이트
        def update_from_slider():
            """슬라이더 값 변경 시 session_state 즉시 업데이트 + number_input 위젯도 동기화"""
            slider_value = st.session_state.glossary_slider
            st.session_state.glossary_min_terms = slider_value[0]
            st.session_state.glossary_max_terms = slider_value[1]

            # number_input 위젯의 키도 동시 업데이트 (UI 동기화)
            st.session_state.glossary_min_input = slider_value[0]
            st.session_state.glossary_max_input = slider_value[1]

            if exp_manager:
                exp_manager.log_ui_interaction(
                    f"용어 추출 범위 변경 (슬라이더): {slider_value[0]}-{slider_value[1]}개"
                )

        # 콜백 함수: number_input 변경 시 검증 및 업데이트
        def update_from_inputs():
            """텍스트 입력 값 변경 시 검증 후 session_state 업데이트 + 슬라이더도 동기화"""
            min_val = st.session_state.glossary_min_input
            max_val = st.session_state.glossary_max_input

            # 최소값이 최대값보다 크지 않도록 검증
            if min_val <= max_val:
                st.session_state.glossary_min_terms = min_val
                st.session_state.glossary_max_terms = max_val

                # 슬라이더 위젯의 키도 동시 업데이트 (UI 동기화)
                st.session_state.glossary_slider = (min_val, max_val)

                if exp_manager:
                    exp_manager.log_ui_interaction(
                        f"용어 추출 범위 변경 (수동): {min_val}-{max_val}개"
                    )

        # 슬라이더 위젯 (범위 선택) - key를 통해 session_state와 자동 바인딩
        st.caption("용어 추출 개수 범위:")
        st.slider(
            "슬라이더로 범위 조정",
            min_value=1,
            max_value=100,
            key="glossary_slider",
            on_change=update_from_slider,
            label_visibility="collapsed"
        )

        # 텍스트 입력 위젯 (수동 입력) - key를 통해 session_state와 자동 바인딩
        col1, col2 = st.columns(2)

        with col1:
            st.number_input(
                "최소 개수",
                min_value=1,
                max_value=100,
                step=1,
                key="glossary_min_input",
                on_change=update_from_inputs
            )

        with col2:
            st.number_input(
                "최대 개수",
                min_value=1,
                max_value=100,
                step=1,
                key="glossary_max_input",
                on_change=update_from_inputs
            )

        # 검증: 최소값이 최대값보다 큰 경우 경고
        if st.session_state.glossary_min_terms > st.session_state.glossary_max_terms:
            st.warning("⚠️ 최소 개수는 최대 개수보다 작거나 같아야 합니다.")
            # 자동 수정: 최소값을 최대값과 같게 설정
            st.session_state.glossary_min_terms = st.session_state.glossary_max_terms

        # 설명 표시
        st.info(
            "ℹ️ 답변에서 추출할 AI/ML 용어 개수 범위를 설정합니다.\n\n"
            "IT 관련 용어만 추출되며, 품질 우선으로 저장됩니다."
        )

        # 구분선 추가
        st.divider()

        # -------------- 채팅 목록 -------------- #
        st.markdown("### 💬 채팅 기록")

        chat_list = get_chat_list()

        if not chat_list:
            st.caption("📝 채팅 기록이 없습니다.")
            st.caption("아래에서 질문을 시작하세요!")
        else:
            # 날짜별 그룹화
            grouped_chats = group_chats_by_date(chat_list)

            # 각 그룹별로 표시
            for group_name, chats in grouped_chats.items():
                # 그룹 헤더
                st.markdown(f"**{group_name}**")

                for chat_info in chats:
                    chat_id = chat_info["id"]
                    title = chat_info["title"]
                    difficulty_icon = "🟢" if chat_info["difficulty"] == "easy" else "🔴"

                    # 현재 활성 채팅 표시
                    is_current = (chat_id == st.session_state.current_chat_id)

                    # 채팅 컨테이너 (현재 채팅은 배경색 표시)
                    if is_current:
                        # 현재 채팅 - 다른 스타일
                        st.markdown(
                            f"""
                            <div style="
                                background-color: rgba(255, 75, 75, 0.1);
                                padding: 8px;
                                border-radius: 6px;
                                margin-bottom: 4px;
                                border-left: 3px solid #FF4B4B;
                            ">
                                {difficulty_icon} {title}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        # 일반 채팅 - 버튼으로 표시
                        col1, col2, col3 = st.columns([5, 1, 1])

                        with col1:
                            if st.button(
                                f"{difficulty_icon} {title}",
                                key=f"chat_{chat_id}",
                                use_container_width=True
                            ):
                                # 채팅 전환
                                switch_chat(chat_id)

                                if exp_manager:
                                    exp_manager.log_ui_interaction(f"채팅 전환: {chat_id}")

                                st.rerun()

                        with col2:
                            # 저장 버튼
                            chat_content = export_chat(chat_id)
                            if chat_content:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                filename = f"chat_{title[:20]}_{timestamp}.md"

                                st.download_button(
                                    label="💾",
                                    data=chat_content,
                                    file_name=filename,
                                    mime="text/markdown",
                                    key=f"save_{chat_id}",
                                    help="저장"
                                )

                        with col3:
                            # 삭제 버튼
                            if st.button("🗑️", key=f"delete_{chat_id}", help="삭제"):
                                delete_chat(chat_id)

                                if exp_manager:
                                    exp_manager.log_ui_interaction(f"채팅 삭제: {chat_id}")

                                st.rerun()

                # 그룹 구분선
                st.markdown("<div style='margin: 12px 0;'></div>", unsafe_allow_html=True)

        # 구분선 추가
        st.divider()

        # -------------- 저장소 관리 섹션 -------------- #
        with st.expander("💾 저장소 관리", expanded=False):
            storage_info = get_storage_info()

            st.caption(f"📊 총 채팅 수: {storage_info['total_chats']}개")
            st.caption(f"🔄 자동 저장: {'✅ 활성화' if storage_info['auto_save_enabled'] else '❌ 비활성화'}")

            col1, col2 = st.columns(2)

            with col1:
                # 수동 저장 버튼
                if st.button("💾 저장", help="현재 채팅을 브라우저에 저장", use_container_width=True):
                    save_chats_to_local_storage()
                    st.success("저장 완료!")

                    if exp_manager:
                        exp_manager.log_ui_interaction("LocalStorage 수동 저장")

            with col2:
                # 저장소 초기화 버튼
                if st.button("🗑️ 초기화", help="브라우저 저장소 초기화", use_container_width=True):
                    clear_local_storage()

                    if exp_manager:
                        exp_manager.log_ui_interaction("LocalStorage 초기화")

            st.caption("💡 채팅은 브라우저에 자동 저장됩니다")

        # 구분선 추가
        st.divider()

        # -------------- 시스템 정보 표시 -------------- #
        st.caption("📚 논문 리뷰 챗봇")
        st.caption("🤖 LangGraph + RAG 기반")
        st.caption("💬 OpenAI GPT-5 / Solar-pro2")

    # 자동 저장 실행
    if st.session_state.get("auto_save_enabled", True) and st.session_state.get("chats"):
        save_chats_to_local_storage()

    # 선택된 난이도 반환
    return difficulty
