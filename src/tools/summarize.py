# src/tools/summarize.py
"""
논문 요약 도구 모듈

PostgreSQL papers 테이블에서 논문 검색
pgvector에서 논문 청크 조회
load_summarize_chain (stuff 방식) 사용
난이도별 요약 프롬프트 적용
"""

# ==================== Import ==================== #
import os
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
import psycopg2
from src.agent.state import AgentState
from src.llm.client import LLMClient
from src.prompts import get_summarize_title_extraction_prompt, get_summarize_template


# ==================== 도구 6: 논문 요약 노드 ==================== #
def summarize_node(state: AgentState, exp_manager=None):
    """
    논문 요약 노드
    PostgreSQL papers 테이블에서 논문을 검색하고,
    pgvector에서 해당 논문의 모든 청크를 조회하여 요약 생성
    난이도별(Easy/Hard) 요약 프롬프트 적용

    Args:
        state (AgentState): Agent 상태
        exp_manager: ExperimentManager 인스턴스 (선택 사항)

    Returns:
        AgentState: 업데이트된 상태 (final_answer에 요약 결과)
    """
    # ============================================================ #
    #                     초기화 및 상태 추출                      #
    # ============================================================ #
    question = state.get("question", "")        # 사용자 질문
    difficulty = state.get("difficulty", "easy") # 난이도

    # ExperimentManager 로거 설정
    tool_logger = None
    if exp_manager:
        tool_logger = exp_manager.get_tool_logger('summarize')
        tool_logger.write(f"논문 요약 노드 실행 - 질문: {question}, 난이도: {difficulty}")

    # ============================================================ #
    #           파이프라인 모드: 이전 도구 결과 사용               #
    # ============================================================ #
    tool_pipeline = state.get("tool_pipeline", [])
    pipeline_index = state.get("pipeline_index", 0)
    tool_result = state.get("tool_result", "")

    # 파이프라인 실행 중이고 이전 도구 결과가 있으면 바로 요약
    if tool_pipeline and pipeline_index > 1 and tool_result:
        if tool_logger:
            tool_logger.write(f"파이프라인 모드: 이전 도구 결과 사용 ({len(tool_result)} 글자)")

        # 난이도별 LLM 초기화
        llm_client = LLMClient.from_difficulty(
            difficulty=difficulty,
            logger=exp_manager.logger if exp_manager else None
        )

        # 요약 프롬프트 템플릿 로드
        summarize_template_str = get_summarize_template(difficulty=difficulty)
        summarize_prompt = PromptTemplate(
            template=summarize_template_str,
            input_variables=["text"]
        )

        # load_summarize_chain 사용 (stuff 방식)
        chain = load_summarize_chain(
            llm=llm_client.llm,
            chain_type="stuff",
            prompt=summarize_prompt
        )

        # 이전 도구 결과를 Document 형식으로 변환
        from langchain.schema import Document
        doc = Document(page_content=tool_result, metadata={"source": "pipeline"})

        # 요약 실행
        summary = chain.run([doc])

        if tool_logger:
            tool_logger.write(f"파이프라인 요약 완료: {len(summary)} 글자")

        state["final_answer"] = summary
        state["tool_result"] = summary
        return state

    try:
        # ============================================================ #
        #              1단계: 논문 제목 추출 (LLM 사용)               #
        # ============================================================ #
        # 난이도별 LLM 초기화
        llm_client = LLMClient.from_difficulty(
            difficulty=difficulty,
            logger=exp_manager.logger if exp_manager else None
        )
        # JSON 프롬프트 로드
        extract_prompt_template = get_summarize_title_extraction_prompt()
        extract_prompt = extract_prompt_template.format(question=question)

        if tool_logger:
            tool_logger.write(f"논문 제목 추출 프롬프트: {extract_prompt}")

        paper_title = llm_client.llm.invoke(extract_prompt).content.strip()

        if tool_logger:
            tool_logger.write(f"추출된 논문 제목: {paper_title}")

        # ============================================================ #
        #       2단계: PostgreSQL papers 테이블에서 논문 검색          #
        # ============================================================ #
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        # 논문 제목으로 검색 (ILIKE로 부분 일치 허용)
        query = """
        SELECT paper_id, title, authors, abstract, publish_date
        FROM papers
        WHERE title ILIKE %s
        LIMIT 1
        """

        cursor.execute(query, (f"%{paper_title}%",))
        result = cursor.fetchone()

        # ExperimentManager SQL 쿼리 기록
        if exp_manager:
            exp_manager.log_sql_query(
                query=query,
                params=(f"%{paper_title}%",),
                result_count=1 if result else 0
            )

        # 논문을 찾지 못한 경우
        if not result:
            if tool_logger:
                tool_logger.write(f"논문을 찾지 못함: {paper_title}")

            cursor.close()
            conn.close()

            state["final_answer"] = f"'{paper_title}' 논문을 데이터베이스에서 찾지 못했습니다. 논문 제목을 정확히 확인해주세요."
            return state

        # 논문 정보 추출
        paper_id, title, authors, abstract, publish_date = result

        if tool_logger:
            tool_logger.write(f"논문 발견 - ID: {paper_id}, 제목: {title}")

        cursor.close()
        conn.close()

        # ============================================================ #
        #      3단계: pgvector에서 논문의 모든 청크 조회               #
        # ============================================================ #
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = PGVector(
            collection_name="paper_chunks",
            embeddings=embeddings,
            connection=os.getenv("DATABASE_URL")
        )

        # 논문 제목으로 시맨틱 검색하여 관련 청크 조회
        # filter는 source 필드와 정확히 매치되지 않을 수 있으므로
        # 제목을 query로 사용하여 관련 청크를 찾음
        docs = vectorstore.similarity_search(
            query=title,  # 논문 제목으로 검색
            k=50          # 충분한 청크 수
        )

        if tool_logger:
            tool_logger.write(f"조회된 청크 수: {len(docs)}")

        # ExperimentManager pgvector 검색 기록
        if exp_manager:
            exp_manager.log_pgvector_search({
                "tool": "summarize",
                "collection": "paper_chunks",
                "query_text": title,
                "top_k": 50,
                "result_count": len(docs)
            })

        # 청크가 없는 경우
        if not docs:
            state["final_answer"] = f"'{title}' 논문의 내용을 찾지 못했습니다."
            return state

        # ============================================================ #
        #        4단계: JSON 프롬프트 로드 및 두 수준 요약 생성           #
        # ============================================================ #
        level_mapping = {
            "easy": ["elementary", "beginner"],
            "hard": ["intermediate", "advanced"]
        }

        levels = level_mapping.get(difficulty, ["beginner", "intermediate"])
        final_answers = {}

        # 난이도별 LLM 초기화 (공통)
        llm_client_summarize = LLMClient.from_difficulty(
            difficulty=difficulty,
            logger=exp_manager.logger if exp_manager else None
        )

        # 논문 청크들을 하나의 텍스트로 결합 (공통)
        combined_text = "\n\n".join([doc.page_content for doc in docs])

        # 각 수준별로 요약 생성
        for level in levels:
            if tool_logger:
                tool_logger.write(f"수준 '{level}' 요약 생성 시작")

            # JSON에서 요약 템플릿 로드
            summary_template_str = get_summarize_template(level)

            # 템플릿에 논문 정보 포맷팅
            system_content = summary_template_str.format(
                system_prompt=f"난이도: {level}",
                title=title,
                authors=authors if authors else "N/A",
                publish_date=publish_date if publish_date else "N/A",
                abstract=abstract if abstract else "N/A",
                combined_text=combined_text
            )

            # 프롬프트 생성
            summary_prompt = f"""{system_content}

논문 정보:
- 제목: {title}
- 저자: {authors}
- 발행일: {publish_date}
- 초록: {abstract}

논문 내용:
{combined_text}

위 논문의 방법론 부분을 중심으로 요약해주세요.
요약:"""

            # SystemMessage 저장
            if exp_manager:
                exp_manager.save_system_prompt(system_content, {
                    "tool": "summarize",
                    "level": level
                })
                exp_manager.save_final_prompt(summary_prompt, {
                    "tool": "summarize",
                    "difficulty": difficulty,
                    "level": level,
                    "paper_title": title
                })

            if tool_logger:
                tool_logger.write(f"LLM 요약 생성 중 (수준: {level})...")
                tool_logger.write(f"결합된 텍스트 길이: {len(combined_text)} 문자")

            # LLM으로 요약 생성
            summary = llm_client_summarize.llm.invoke(summary_prompt).content
            final_answers[level] = summary

            if tool_logger:
                tool_logger.write(f"수준 '{level}' 요약 생성 완료 - 길이: {len(summary)} 문자")
                tool_logger.write("=" * 80)
                tool_logger.write(f"[{level} 요약 전체 내용]")
                tool_logger.write(summary)
                tool_logger.write("=" * 80)

        if tool_logger:
            tool_logger.close()

        # ============================================================ #
        #                  5단계: 최종 답변 저장                       #
        # ============================================================ #
        state["final_answers"] = final_answers
        state["final_answer"] = final_answers[levels[1]]

        # ============================================================ #
        #                  6단계: summary.md 저장                      #
        # ============================================================ #
        if exp_manager:
            # 두 수준의 요약을 하나의 Markdown으로 저장
            level_labels = {
                "elementary": "초등학생용 (8-13세)",
                "beginner": "초급자용 (14-22세)",
                "intermediate": "중급자용 (23-30세)",
                "advanced": "고급자용 (30세 이상)"
            }

            summary_md = f"""# 논문 요약

## 기본 정보

- **제목**: {title}
- **저자**: {authors}
- **발행일**: {publish_date}

"""
            # 각 수준별 요약 추가
            for level_name, content in final_answers.items():
                summary_md += f"## 요약: {level_labels.get(level_name, level_name)}\n\n"
                summary_md += f"{content}\n\n---\n\n"

            summary_md += f"*생성 시간: {exp_manager.metadata.get('start_time', '')}*\n"

            # summary 폴더에 논문 제목을 파일명으로 저장
            summary_dir = exp_manager.outputs_dir / "summary"
            summary_dir.mkdir(exist_ok=True)

            # 논문 제목을 파일명으로 사용 (특수문자 제거)
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:100]  # 최대 100자

            summary_file = summary_dir / f"{safe_title}.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_md)

            if tool_logger:
                tool_logger.write(f"논문 요약 저장 완료: {summary_file.name}")

        state["tool_result"] = state["final_answer"]  # 도구 실행 결과

        if tool_logger:
            tool_logger.write("논문 요약 노드 실행 완료")

        return state

    except Exception as e:
        # 예외 처리
        error_msg = f"논문 요약 중 오류 발생: {str(e)}"

        if tool_logger:
            tool_logger.write(f"오류: {error_msg}")

        state["final_answer"] = error_msg
        return state
