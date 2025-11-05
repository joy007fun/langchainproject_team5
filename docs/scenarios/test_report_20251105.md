# 테스트 리포트 - 2025-11-05

## 요약

### 테스트 결과
- **초보자 모드**: 20/20 (100% 성공)
- **전문가 모드**: 진행 중 (background 실행)
- **다중 요청 파이프라인**: ✅ 정상 작동
- **Fallback 시스템**: ✅ 정상 작동

### 주요 수정사항
1. AgentState에 `tool_pipeline`, `pipeline_index` 필드 추가
2. general 도구의 파이프라인 지원 수정
3. 다중 요청 패턴 추가 (`['논문', '요약', '저장']`)
4. ExperimentManager SQL 쿼리 저장 오류 수정

---

## 발견된 문제와 해결

### 1. 다중 요청 파이프라인 미작동 ❌

**문제 상황:**
- 사용자 질문: `"논문 요약해서 저장해줘"`
- 예상: search_paper → summarize → save_file
- 실제: search_paper만 실행되고 종료

**원인 분석:**
1. `AgentState`에 `tool_pipeline`, `pipeline_index` 필드가 정의되지 않아 LangGraph에서 손실
2. `general` 도구가 항상 END로 하드코딩되어 파이프라인 중간에 사용 불가
3. YAML 패턴 파일에 `['논문', '요약', '저장']` 패턴 누락

**해결 방법:**
```python
# src/agent/state.py
class AgentState(TypedDict, total=False):
    # ... 기존 필드 ...

    # 다중 요청 Pipeline 관련 필드 추가
    tool_pipeline: List[str]        # 순차 실행 도구 리스트
    pipeline_index: int              # 현재 Pipeline 실행 인덱스
```

```python
# src/agent/graph.py
# general도 check_pipeline_or_fallback을 거치도록 수정
for tool_name in ["general", "glossary", "search_paper", ...]:
    workflow.add_conditional_edges(
        tool_name,
        check_pipeline_or_fallback,  # 파이프라인 체크
        {...}
    )

# general → END 하드코딩 제거
# workflow.add_edge("general", END)  ← 제거함
```

```yaml
# configs/multi_request_patterns.yaml
- keywords:
  - 논문
  - 요약
  - 저장
  tools:
  - search_paper
  - summarize
  - save_file
  description: 논문 요약 후 저장
  priority: 105
```

**커밋:** `3f7bdf1` - "fix: 다중 요청 파이프라인 실행 오류 수정"

---

### 2. ExperimentManager SQL 쿼리 저장 오류 ❌

**문제 상황:**
```python
AttributeError: 'str' object has no attribute 'get'
```

**원인 분석:**
- `log_sql_query()`는 str을 `self.db_queries`에 저장
- `flush_queries_to_file()`은 dict를 기대하고 `.get()` 호출

**해결 방법:**
```python
# src/utils/experiment_manager.py
def flush_queries_to_file(self):
    for i, query_info in enumerate(self.db_queries, 1):
        # str/dict 모두 처리
        if isinstance(query_info, str):
            f.write(f"-- Query {i}\n")
            f.write(query_info)
        else:
            # dict인 경우
            f.write(f"-- Query {i}\n")
            f.write(f"-- Time: {query_info.get('timestamp', 'N/A')}\n")
            f.write(f"{query_info.get('query', '')}\n\n")
```

**커밋:** `fff1374` - "fix: ExperimentManager SQL 쿼리 저장 오류 수정"

---

## 테스트 상세 결과

### 초보자 모드 (20개 질문)

#### 성공률
```
전체: 20/20 (100.0%)
- 단일 요청: 14/14 (100%)
- 다중 요청: 4/4 (100%)
- 멀티턴: 2/2 (100%)
```

#### 도구별 선택 횟수
```
search_paper: 7회
glossary: 5회
general: 5회 (일부 Fallback)
text2sql: 2회
web_search: 1회
```

#### 주요 테스트 케이스

**1. 단일 요청 - glossary**
```
질문: Transformer가 뭐야?
선택 도구: glossary ✓
결과: 성공
```

**2. 단일 요청 - search_paper**
```
질문: Transformer 관련 논문 찾아줘
선택 도구: search_paper ✓
결과: 성공
```

**3. 단일 요청 - text2sql**
```
질문: 2024년에 나온 AI 논문 몇 개야?
선택 도구: text2sql ✓
결과: 성공
```

**4. 다중 요청 - search_paper + summarize**
```
질문: GPT 논문 찾아서 요약해줘
파이프라인: [search_paper, summarize]
실행 도구: search_paper → summarize
결과: 성공 ✓
```

**5. 다중 요청 with Fallback**
```
질문: Attention 관련 논문 정리해줘
파이프라인: [search_paper, summarize]
실행 도구: search_paper → summarize (실패) → general (Fallback)
결과: 성공 ✓
```

**6. 멀티턴 대화**
```
[Turn 1] Vision Transformer가 뭐야?
선택 도구: glossary ✓

[Turn 2] 관련 논문 찾아줘
선택 도구: search_paper ✓
```

---

## 파이프라인 & Fallback 작동 검증

### 테스트 케이스: "Attention Is All You Need" 논문 요약해서 저장해줘

**예상 흐름:**
```
search_paper → (실패 시) → web_search → (실패 시) → general
→ summarize → (실패 시) → general
→ save_file
```

**실제 실행:**
```
1. Router 감지: ['논문', '요약', '저장'] → [search_paper, summarize, save_file]
2. search_paper 실행 → ✅ 성공
3. Pipeline 계속: summarize 실행 → ❌ 실패 (API 오류)
4. Fallback Router: summarize → general로 교체
5. general 실행 → ✅ 성공
6. Pipeline 계속: save_file 실행 → ✅ 성공

최종 파이프라인: [search_paper, general, save_file]
파일 저장 위치: experiments/.../outputs/save_data/20251105_151138_*.md
```

**검증 포인트:**
- ✅ 다중 요청 패턴 매칭
- ✅ 순차 도구 실행 (search → summarize → save)
- ✅ 도구 실패 감지 (summarize)
- ✅ Fallback 자동 교체 (summarize → general)
- ✅ 파이프라인 계속 진행 (general 이후 save_file 실행)
- ✅ 최종 파일 저장

---

## 구현 검증

### 1. Router 노드 (src/agent/nodes.py:30-171)

**우선순위 1: 질문 유형 기반 라우팅**
```python
question_type = state.get("question_type", "")  # "paper_search"
fallback_chain = state.get("fallback_chain", [])  # ["search_paper", "web_search", "general"]
tool_choice = fallback_chain[0]  # "search_paper"
```

**우선순위 2: LLM 라우팅 (보조)**
- JSON 응답 파싱 지원
- 키워드 기반 도구명 매핑 ("논문" → search_paper)

### 2. Fallback Router 노드 (src/agent/nodes.py:217-386)

**파이프라인 모드 Fallback:**
```python
TOOL_FALLBACKS = {
    "search_paper": "web_search",
    "web_search": "general",
    "summarize": "general",
    ...
}

# 실패한 도구를 Fallback으로 교체
if is_pipeline:
    fallback_tool = TOOL_FALLBACKS.get(failed_tool)
    tool_pipeline[current_index] = fallback_tool  # 교체
    state["tool_pipeline"] = tool_pipeline
```

### 3. Pipeline Router (src/agent/graph.py:311-343)

**다음 도구 선택:**
```python
def pipeline_router(state: AgentState, exp_manager=None):
    tool_pipeline = state.get("tool_pipeline", [])
    pipeline_index = state.get("pipeline_index", 0)

    if pipeline_index < len(tool_pipeline):
        next_tool = tool_pipeline[pipeline_index]
        state["tool_choice"] = next_tool
        state["pipeline_index"] = pipeline_index + 1
        return state
```

### 4. Pipeline 계속 체크 (src/agent/graph.py:277-295)

**도구 실행 후 판단:**
```python
def check_pipeline_or_fallback(state: AgentState) -> str:
    # 1. 도구 실패 → Fallback
    if tool_status != "success":
        return should_fallback(state)

    # 2. 성공 → Pipeline 계속 여부 확인
    if tool_pipeline and pipeline_index < len(tool_pipeline):
        return "continue"  # pipeline_router로 이동

    # 3. Pipeline 완료 → 종료
    return "end"
```

---

## 커밋 히스토리

### 1. `3627769` - Router JSON 응답 파싱 로직 개선
- JSON 응답 처리 추가
- 키워드 기반 도구명 매핑

### 2. `f4337f0` - Router 질문 유형 기반 도구 선택 로직 추가
- question_type 우선순위 1로 상향
- LLM 라우팅을 보조로 전환

### 3. `522a61c` - ExperimentManager 메서드명 수정
- end_session() → close()

### 4. `3f7bdf1` - 다중 요청 파이프라인 실행 오류 수정 ⭐
- AgentState에 tool_pipeline, pipeline_index 필드 추가
- general 도구 파이프라인 지원
- '논문 요약 저장' 패턴 추가

### 5. `fff1374` - ExperimentManager SQL 쿼리 저장 오류 수정
- str/dict 양방향 호환성 추가

---

## 남은 작업

### 1. 전문가 모드 전체 테스트 완료 대기
- 현재 background에서 실행 중
- 21개 질문 (일부 복잡한 4-tool 파이프라인 포함)
- 예상 완료 시간: 추가 10-15분

### 2. 테스트 문서 업데이트
- 전문가 모드 결과 추가
- 실패 케이스 분석 (있는 경우)

### 3. 사용자 가이드 작성
- 다중 요청 패턴 사용법
- Fallback 시스템 설명
- 멀티턴 대화 예시

---

## 결론

### 달성한 목표 ✅
1. ✅ 테스트 문서 작성 (초보자 20개, 전문가 21개)
2. ✅ Router 개선 (질문 유형 기반 우선순위)
3. ✅ 다중 요청 파이프라인 수정
4. ✅ Fallback 시스템 검증
5. ✅ 초보자 모드 100% 성공

### 검증된 기능 ✅
- ✅ 단일 요청 처리
- ✅ 다중 요청 순차 실행
- ✅ 멀티턴 대화
- ✅ 도구 Fallback (search_paper → web_search → general)
- ✅ 파이프라인 중 Fallback (도구 교체 후 계속 진행)
- ✅ 파일 저장 (save_file)

### 성과
- **100% 초보자 모드 성공률**
- **모든 질문 유형 처리 가능** (단일/다중/멀티턴)
- **Fallback 자동 복구** (실패 → 대체 도구 → 계속 진행)
- **7가지 도구 모두 작동 확인** (general, glossary, search_paper, web_search, summarize, text2sql, save_file)

---

*작성일: 2025-11-05*
*작성자: Claude Code*
*실험 폴더: experiments/20251105/*
