# ui/pages/1_📚_Glossary.py

"""
용어집 페이지

AI/ML 용어 검색 및 조회:
- 전체 용어 리스트
- 검색 기능
- 카테고리 필터
- 난이도별 설명 표시
"""

# ==================== Import ==================== #
# ------------------------- 표준 라이브러리 ------------------------- #
import os
import sys

# ------------------------- 서드파티 라이브러리 ------------------------- #
import streamlit as st
import psycopg2

# ------------------------- 프로젝트 모듈 ------------------------- #
# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


# ==================== 페이지 설정 ==================== #
st.set_page_config(
    page_title="용어집 | 논문 리뷰 챗봇",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== 메인 헤더 ==================== #
st.title("📚 AI/ML 용어집")
st.caption("논문 리뷰 챗봇에서 자동으로 수집된 AI/ML 전문 용어")
st.divider()


# ==================== 데이터베이스 연결 함수 ==================== #
# ---------------------- 용어 검색 함수 ---------------------- #
def search_glossary(search_term: str = "", category_filter: str = "전체"):
    """
    용어집 검색 함수

    Args:
        search_term: 검색어
        category_filter: 카테고리 필터

    Returns:
        검색 결과 리스트
    """
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        # -------------- 쿼리 구성 -------------- #
        query = """
        SELECT term, definition, easy_explanation, hard_explanation, category, difficulty_level, created_at
        FROM glossary
        WHERE 1=1
        """
        params = []

        # 검색어 조건 추가
        if search_term:
            query += " AND (term ILIKE %s OR definition ILIKE %s)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        # 카테고리 필터 추가
        if category_filter != "전체":
            query += " AND category = %s"
            params.append(category_filter)

        query += " ORDER BY created_at DESC"

        # -------------- 쿼리 실행 -------------- #
        cursor.execute(query, params)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

    except Exception as e:
        st.error(f"❌ 데이터베이스 오류: {str(e)}")
        return []


# ---------------------- 카테고리 목록 가져오기 ---------------------- #
def get_categories():
    """
    용어집의 모든 카테고리 가져오기

    Returns:
        카테고리 리스트
    """
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT category FROM glossary WHERE category IS NOT NULL ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return ["전체"] + categories

    except Exception as e:
        st.error(f"❌ 데이터베이스 오류: {str(e)}")
        return ["전체"]


# ==================== 검색 UI ==================== #
# ---------------------- 검색 바 및 필터 ---------------------- #
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    search_term = st.text_input(
        "🔍 용어 검색",
        placeholder="검색어를 입력하세요...",
        help="용어명 또는 정의에서 검색합니다"
    )

with col2:
    categories = get_categories()
    category_filter = st.selectbox(
        "📂 카테고리",
        options=categories,
        help="카테고리별로 필터링합니다"
    )

with col3:
    difficulty_display = st.radio(
        "🎚️ 설명 난이도",
        options=["쉬운 설명", "상세 설명"],
        help="표시할 설명의 난이도를 선택하세요"
    )
    show_easy = (difficulty_display == "쉬운 설명")


st.divider()


# ==================== 용어 검색 및 표시 ==================== #
# ---------------------- 검색 실행 ---------------------- #
results = search_glossary(search_term, category_filter)

if not results:
    st.info("🔍 검색 결과가 없습니다.")
    st.caption("다른 검색어나 카테고리를 시도해보세요.")
else:
    st.success(f"✅ {len(results)}개의 용어를 찾았습니다")

    # -------------- 용어 표시 -------------- #
    for term, definition, easy_explanation, hard_explanation, category, difficulty_level, created_at in results:
        with st.expander(f"**{term}** ({category or 'N/A'})"):
            # 카테고리 및 난이도 정보
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.caption(f"📂 카테고리: **{category or 'N/A'}**")
            with col_b:
                if difficulty_level:
                    st.caption(f"🎚️ 난이도: **레벨 {difficulty_level}**")

            st.divider()

            # -------------- 정의 표시 -------------- #
            st.markdown("### 📖 정의")
            st.markdown(definition or "정의 없음")

            st.divider()

            # -------------- 난이도별 설명 표시 -------------- #
            if show_easy:
                st.markdown("### 🟢 쉬운 설명")
                if easy_explanation:
                    st.markdown(easy_explanation)
                else:
                    st.caption("쉬운 설명이 아직 추가되지 않았습니다.")
            else:
                st.markdown("### 🔴 상세 설명")
                if hard_explanation:
                    st.markdown(hard_explanation)
                else:
                    st.caption("상세 설명이 아직 추가되지 않았습니다.")

            # -------------- 추가 정보 -------------- #
            st.caption(f"*추가된 날짜: {created_at.strftime('%Y-%m-%d %H:%M') if created_at else 'N/A'}*")


# ==================== 푸터 ==================== #
st.divider()
st.caption("💡 용어는 챗봇 답변에서 자동으로 추가됩니다")
st.caption("Made with ❤️ by 연결의 민족 팀")
