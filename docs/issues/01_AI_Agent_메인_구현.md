## 제목 : AI Agent 메인 시스템 구현 (LangGraph + 도구 통합)

---

## 📋 작업 개요
- **작업 주제:** LangGraph 기반 AI Agent 시스템 개발 및 도구 통합
- **작성자:** 최현화[팀장]
- **담당자:** @최현화
- **마감일:** 11/03 24:00

## 📅 기간
- 시작일: 2025-10-28
- 종료일: 2025-11-03

---

## 📌 이슈 목적

LangGraph를 사용하여 논문 리뷰 챗봇의 핵심 AI Agent 시스템을 구현합니다. 사용자 질문을 분석하여 적절한 도구(일반 답변, RAG 검색, 웹 검색, 용어집, 논문 요약, 파일 저장)를 자동으로 선택하고 실행하는 지능형 Agent를 개발합니다.

**핵심 목표:**
- LangGraph StateGraph 구조 설계 및 구현
- 질문 라우팅 로직 구현 (일반 답변 / RAG 검색 / 용어집 / 웹 검색 / 요약 / 저장)
- 6가지 도구 노드 통합
- 멀티턴 대화 메모리 관리
- OpenAI + Solar(Upstage) 듀얼 LLM 전략
- ExperimentManager 기반 실험 추적 및 로깅

---

## ✅ 작업 항목 체크리스트

### Phase 1: 기반 시스템 (`feature/agent-system`) - 2일
**브랜치**: `feature/agent-system`
**우선순위**: P0 (최우선)

#### 1-1. LLM 클라이언트 구현
- [x] LLMClient 클래스 구현 (`src/llm/client.py`)
  - [x] ChatOpenAI 지원 (gpt-5, gpt-5)
  - [x] Solar(Upstage) 지원 (solar-pro2, solar-pro2)
  - [x] 에러 핸들링 및 재시도 (tenacity)
  - [x] 토큰 사용량 추적 (get_openai_callback)
  - [x] 스트리밍 응답 처리 (astream)
- [x] get_llm_for_task() 함수 구현 (작업 유형별 LLM 선택)

#### 1-2. Agent 그래프 기본 구조
- [x] AgentState 정의 (`src/agent/state.py`)
  - [x] question, difficulty, tool_choice, tool_result, final_answer, messages
- [x] create_agent_graph() 함수 구현 (`src/agent/graph.py`)
  - [x] StateGraph 생성
  - [x] 노드 추가 (router + 6개 빈 노드)
  - [x] 조건부 엣지 설정
  - [x] 그래프 컴파일
- [x] 라우터 노드 구현 (`src/agent/nodes.py`)
  - [x] 질문 분석 및 도구 선택 로직
  - [x] LLM으로 라우팅 결정
- [x] 6개 빈 노드 함수 정의 (placeholder)
  - [x] general_answer_node
  - [x] search_paper_node
  - [x] web_search_node
  - [x] glossary_node
  - [x] summarize_node
  - [x] save_file_node

#### 1-3. 테스트
- [x] LLM 클라이언트 단독 테스트
- [x] Agent 그래프 컴파일 테스트
- [x] 라우터 노드 테스트

---

### Phase 2: 6개 도구 구현 (`feature/agent-tools`) - 2~3일
**브랜치**: `feature/agent-tools`
**우선순위**: P1
**의존성**: `feature/agent-system`

#### 2-1. 간단한 도구 (DB/API 불필요)
- [x] 도구 1: 일반 답변 (general_answer_node)
  - [x] 난이도별 SystemMessage 설정
  - [x] LLM 직접 호출
  - [x] ExperimentManager 통합
- [x] 도구 2: 파일 저장 (save_file_node)
  - [x] ExperimentManager.save_output() 사용
  - [x] 파일명 자동 생성 (timestamp)
  - [x] outputs/ 폴더에 저장

#### 2-2. DB/API 통합 도구 (팀원 협업)
- [x] 도구 3: RAG 검색 (search_paper_node) ⭐ 신준엽 협업
  - [x] pgvector 유사도 검색 (Top-5)
  - [x] PostgreSQL papers 테이블 조회
  - [x] 난이도별 프롬프트 구성
  - [x] ExperimentManager 통합
- [x] 도구 4: 용어집 (glossary_node) ⭐ 신준엽 협업
  - [x] PostgreSQL glossary 테이블 검색
  - [x] 난이도별 설명 제공
  - [x] 용어 추출 로직
  - [x] ExperimentManager 통합
- [x] 도구 5: 웹 검색 (web_search_node) ⭐ 임예슬 협업
  - [x] Tavily Search API 호출
  - [x] 검색 결과 LLM 정리
  - [x] 난이도별 프롬프트 적용
  - [x] ExperimentManager 통합

#### 2-3. 복잡한 도구
- [x] 도구 6: 논문 요약 (summarize_node)
  - [x] PostgreSQL papers 테이블 검색
  - [x] pgvector 논문 전체 청크 조회
  - [x] load_summarize_chain (stuff, map_reduce, refine)
  - [x] 난이도별 프롬프트 설계
  - [x] ExperimentManager 통합

#### 2-4. 테스트
- [x] 각 도구별 단독 테스트
- [x] Agent 그래프에서 도구 호출 테스트
- [x] ExperimentManager 로깅 확인

---

### Phase 3: 통합 (`feature/agent-integration`) - 1~2일
**브랜치**: `feature/agent-integration`
**우선순위**: P2
**의존성**: `feature/agent-system`, `feature/agent-tools`

#### 3-1. 대화 메모리 시스템
- [x] ChatMemoryManager 클래스 구현 (`src/memory/chat_history.py`)
  - [x] ConversationBufferMemory 초기화
  - [x] add_user_message() 구현
  - [x] add_ai_message() 구현
  - [x] get_history() 구현
  - [x] clear() 구현
- [x] 세션 기반 메모리 (선택)
  - [x] PostgresChatMessageHistory 구현
  - [x] get_session_history() 함수

#### 3-2. main.py 작성
- [x] Agent 실행 루프 구현
- [x] ExperimentManager 전역 통합
- [x] 테스트 질문 리스트로 Agent 실행
- [x] 결과 출력 및 로깅

#### 3-3. 전체 통합 테스트
- [x] 10개 시나리오 테스트 (PRD 09 평가 기준)
- [x] 디버깅 및 오류 수정
- [x] 성능 최적화
- [x] 로그 파일 확인
- [x] 문서화 작성

---

## 📦 설치/실행 명령어 예시

```bash
# 가상환경 활성화
pyenv activate langchain_py3_11_9

# 필요한 패키지 설치
pip install langchain langchain-openai langchain-upstage langgraph

# 환경변수 설정
export OPENAI_API_KEY="your-openai-api-key"
export SOLAR_API_KEY="your-upstage-api-key"

# Agent 실행 테스트
python src/agent/graph.py

# 단위 테스트 실행
pytest tests/test_agent.py -v
```

---

### ⚡️ 참고

**중요 사항:**
1. **ExperimentManager 필수 사용**: 모든 도구에서 ExperimentManager 통합
   - with ExperimentManager() as exp: 패턴 사용
   - 도구별 Logger 생성: exp.get_tool_logger('tool_name')
   - DB 쿼리 기록: exp.log_sql_query(), exp.log_pgvector_search()
   - 프롬프트 저장: exp.save_system_prompt(), exp.save_user_prompt()
2. **PRD 05, 06 필수 준수**: 실험 폴더 구조 준수, Session ID 자동 부여
3. **LangGraph 패턴**: StateGraph → add_node → add_edge → add_conditional_edges → compile
4. **6가지 도구 노드**: 일반 답변, RAG 검색, 웹 검색, 용어집, 논문 요약, 파일 저장
5. **AgentState 필드**: question, difficulty, tool_choice, tool_result, final_answer, messages
6. **듀얼 LLM**: OpenAI 우선, 실패 시 Solar로 fallback
7. **난이도 모드**: Easy(초심자용), Hard(전문가용) 프롬프트 분리

**주의:**
- Agent 노드에서 반드시 `return state` (State 업데이트)
- 조건부 엣지에서 명확한 라우팅 키 반환 ("general", "search_paper", "web_search", "glossary", "summarize", "save_file")
- 메모리는 최근 10턴만 유지 (토큰 절약)
- 협업 필요: 신준엽 (RAG, 용어집), 임예슬 (Tavily API)

---

### 유용한 링크

**필수 참고 PRD 문서:**
- [docs/PRD/01_프로젝트_개요.md](../PRD/01_프로젝트_개요.md) - 프로젝트 전체 개요 및 목표
- [docs/PRD/02_프로젝트_구조.md](../PRD/02_프로젝트_구조.md) - 폴더 구조 및 모듈 배치
- [docs/PRD/05_로깅_시스템.md](../PRD/05_로깅_시스템.md) ⭐⭐⭐ - ExperimentManager 사용법 및 로깅 규칙
- [docs/PRD/06_실험_추적_관리.md](../PRD/06_실험_추적_관리.md) ⭐⭐⭐ - 실험 폴더 구조 및 Session ID 자동 부여 규칙
- [docs/PRD/09_평가_기준.md](../PRD/09_평가_기준.md) ⭐⭐ - RAG 평가, Agent 정확도, 응답 시간, 비용 분석
- [docs/PRD/10_기술_요구사항.md](../PRD/10_기술_요구사항.md) - 기술 스택 및 라이브러리
- [docs/PRD/12_AI_Agent_설계.md](../PRD/12_AI_Agent_설계.md) - LangGraph 구조 및 도구 정의
- [docs/PRD/14_LLM_설정.md](../PRD/14_LLM_설정.md) - LLM 선택 전략 및 에러 핸들링

**참고 역할 문서:**
- [docs/roles/담당역할_01_최현화_AI_Agent_메인.md](../roles/담당역할_01_최현화_AI_Agent_메인.md) ⭐⭐⭐ - 전체 구현 가이드
- [docs/roles/담당역할_01-1_최현화_실험_관리_시스템.md](../roles/담당역할_01-1_최현화_실험_관리_시스템.md) ⭐⭐⭐ - ExperimentManager 구현 가이드
- [docs/roles/담당역할_01-2_최현화_로깅_모니터링.md](../roles/담당역할_01-2_최현화_로깅_모니터링.md) ⭐⭐ - Logger 및 실험 관리 시스템

**참고 레퍼런스 문서:**
- [docs/rules/실험_폴더_구조.md](../rules/실험_폴더_구조.md) ⭐⭐⭐ - 전체 폴더 구조 및 ExperimentManager 전체 코드

**기타 참고 PRD 문서:**
- [docs/PRD/03_브랜치_전략.md](../PRD/03_브랜치_전략.md) - Feature 브랜치 전략
- [docs/PRD/04_일정_관리.md](../PRD/04_일정_관리.md) - 개발 일정 및 마일스톤
- [docs/PRD/11_데이터베이스_설계.md](../PRD/11_데이터베이스_설계.md) - DB 스키마
- [docs/PRD/13_RAG_시스템_설계.md](../PRD/13_RAG_시스템_설계.md) - RAG 파이프라인
- [docs/PRD/15_프롬프트_엔지니어링.md](../PRD/15_프롬프트_엔지니어링.md) - 프롬프트 템플릿

**외부 링크:**
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [Langchain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- [Langchain Memory](https://python.langchain.com/docs/modules/memory/)

## 🔖 추천 라벨

`feature` `agent` `tool` `memory` `integration` `high` `critical`

---
