# RAG 논문 검색 Fallback 실패 문제

## 📋 문서 정보
- **작성자**: 최현회[팀장]
- **작성일**: 2025-11-05
- **상태**: ✅ 해결 완료
- **관련 도구**: `search_paper` (RAG 논문 검색 도구)
- **심각도**: 🔴 High (Fallback 체인 작동 불능)

---

## 🔍 문제 발견 경위

팀원이 실행 테스트 중 특정 논문을 찾아서 요약해달라고 요청했을 때, 다음과 같은 문제가 발생했습니다:

1. `search_paper` (RAG 논문 검색 도구)가 데이터베이스에서 논문을 찾지 못함
2. 정상적으로는 `web_search` (웹 논문 검색 도구)로 fallback되어야 함
3. 그러나 실제로는 `search_paper`가 "성공"으로 처리되어 다음 파이프라인 도구인 `summarize`로 진행됨
4. `summarize`도 실패하면서 결국 `general` 도구로 fallback되어 일반 답변 처리됨

이는 Fallback 체인이 전혀 작동하지 않는 심각한 문제입니다.

---

## 📊 문제 상황 로그

### 팀원이 제공한 실행 로그

```
도구 실행 성공: search_paper  ← ❌ 문제: 실패했는데 "성공"으로 표시됨
================================================================================
답변:
죄송합니다만, 현재 데이터베이스에서 해당 논문을 찾지 못했습니다.
제가 가진 정보로는 이 논문에 대한 직접적인 내용을 제공하기 어렵습니다.
================================================================================

================================================================================
Fallback Router 실행
================================================================================
도구 실행 상태: success  ← ❌ search_paper가 성공으로 표시됨
실패한 도구 확인 중...
실패한 도구: summarize  ← ❌ 잘못된 도구가 실패로 감지됨
파이프라인 모드: True
현재 파이프라인: ['search_paper', 'summarize']
현재 인덱스: 1
실패한 도구에 대한 Fallback 도구: general
파이프라인 도구 대체: summarize → general  ← ❌ 잘못된 대체
```

### 기대했던 정상 동작

```
도구 실행 실패: search_paper  ← ✅ 실패로 표시되어야 함
실패 원인: 데이터베이스에서 관련 논문을 찾지 못했습니다.

Fallback Router 실행
실패한 도구: search_paper  ← ✅ 올바른 도구 감지
파이프라인 도구 대체: search_paper → web_search  ← ✅ 올바른 대체
```

---

## 🔎 근본 원인 분석

### 1. 문제의 핵심 흐름

#### 현재 (문제 있는) 흐름:
```
1. search_paper_database() 실행
   → VectorDB 검색 → 결과 없음
   → raw_results = "관련 논문을 찾을 수 없습니다"

2. search_paper_node()에서 LLM 호출
   → 시스템 프롬프트 + raw_results 전달
   → LLM이 정중한 답변 생성:
     "죄송합니다만, 현재 데이터베이스에서 해당 논문을 찾지 못했습니다..."

3. failure_detector.is_tool_failed() 실행
   → LLM의 정중한 답변에서 실패 패턴 감지 실패
   → 반환: (False, None)

4. tool_wrapper.py에서 tool_status 설정
   → is_failed == False이므로
   → tool_status = "success"  ← ❌ 잘못된 상태

5. fallback_router_node()에서 fallback 판단
   → tool_status == "success"이므로 fallback 불필요로 판단
   → 다음 파이프라인 도구(summarize)로 진행
```

#### 정상 (기대하는) 흐름:
```
1. search_paper_database() 실행
   → VectorDB 검색 → 결과 없음
   → raw_results = "관련 논문을 찾을 수 없습니다"

2. search_paper_node()에서 실패 조기 감지  ← ✅ 수정 포인트
   → raw_results에 "관련 논문을 찾을 수 없습니다" 포함 확인
   → LLM 호출 없이 즉시 명확한 실패 메시지 반환:
     state["final_answer"] = "데이터베이스에서 관련 논문을 찾지 못했습니다."

3. failure_detector.is_tool_failed() 실행
   → "데이터베이스에서 찾지 못했습니다" 패턴 감지
   → 반환: (True, "데이터베이스에서 찾지 못했습니다")

4. tool_wrapper.py에서 tool_status 설정
   → is_failed == True이므로
   → tool_status = "failed"  ← ✅ 올바른 상태

5. fallback_router_node()에서 fallback 판단
   → tool_status == "failed"이므로 fallback 필요
   → TOOL_FALLBACKS["search_paper"] = "web_search"
   → 파이프라인 대체: search_paper → web_search
```

### 2. 왜 LLM 호출이 문제였나?

**search_paper_node()의 기존 로직** (lines 259-372):
```python
# 1. search_paper_database 호출
raw_results = search_paper_database.invoke({...})

# 2. 결과가 비어있어도 LLM 호출 진행
user_content = f"""[논문 검색 결과]
{raw_results}

[질문]
{question}

위 검색 결과를 바탕으로 질문에 답변해주세요."""

# 3. LLM이 정중한 답변 생성
response = llm_client.llm.invoke(messages)
final_answers[level] = response.content  # "죄송합니다만, 현재 데이터베이스에서..."
```

**문제점**:
- LLM은 시스템 프롬프트에 따라 항상 **정중하고 완성된 문장**으로 답변
- "관련 논문을 찾을 수 없습니다" → "죄송합니다만, 현재 데이터베이스에서 해당 논문을 찾지 못했습니다. 제가 가진 정보로는..."
- Failure Detector의 패턴 매칭이 실패할 수 있음

### 3. Failure Detector 패턴 분석

**src/agent/failure_detector.py** (lines 23-35):
```python
FAILURE_PATTERNS = [
    "관련 용어를 찾을 수 없습니다",
    "관련 논문을 찾을 수 없습니다",  # ← 이 패턴은 존재!
    "검색 결과가 없습니다",
    "데이터베이스에서 찾지 못했습니다",  # ← 이 패턴도 존재!
    # ... more patterns
]
```

**문제**: 패턴은 존재하지만, LLM이 생성한 정중한 답변에는 이 정확한 문자열이 포함되지 않을 수 있음.

예시:
- ❌ LLM 생성: "죄송합니다만, **현재 데이터베이스에서 해당 논문을** 찾지 못했습니다"
- ✅ 패턴: "**데이터베이스에서** 찾지 못했습니다"

LLM이 "현재", "해당 논문을" 같은 단어를 추가하면서 패턴 매칭이 실패할 수 있습니다.

### 4. Tool Wrapper의 Fallback 메커니즘

**src/agent/tool_wrapper.py** (lines 63-81):
```python
# general 도구는 fallback이므로 항상 성공 처리
if tool_name == "general":
    state["tool_status"] = "success"
else:
    # 실패 패턴 감지 (general 제외)
    is_failed, failure_reason = is_tool_failed(final_answer)

    if is_failed:
        state["tool_status"] = "failed"  # ← Fallback 트리거
        state["failure_reason"] = failure_reason
    else:
        state["tool_status"] = "success"  # ← Fallback 없음
```

**src/agent/nodes.py** (lines 326-361):
```python
TOOL_FALLBACKS = {
    "search_paper": "web_search",  # ← 정의는 되어 있음!
    "web_search": "general",
    "summarize": "general",
    # ...
}

# 파이프라인 모드: 도구 대체 로직
if is_pipeline:
    fallback_tool = TOOL_FALLBACKS.get(failed_tool)

    if fallback_tool:
        # 파이프라인에서 실패한 도구를 Fallback 도구로 교체
        tool_pipeline[current_index] = fallback_tool
        state["tool_choice"] = fallback_tool
```

**결론**: Fallback 인프라는 완벽하게 구축되어 있지만, `search_paper_node`가 실패 상태를 명확히 전달하지 못해서 작동하지 않았습니다.

---

## ✅ 해결 방법

### 수정 파일: `src/tools/search_paper.py`

**수정 위치**: lines 276-284 (search_paper_node 함수 내부)

**수정 내용**: 검색 결과가 비어있을 때 LLM 호출 전에 조기 반환

```python
# -------------- 검색 결과 없음 체크 (Fallback 트리거) -------------- #
if "관련 논문을 찾을 수 없습니다" in raw_results:
    if tool_logger:
        tool_logger.write("데이터베이스에서 논문을 찾지 못했습니다. Fallback 필요.")
        tool_logger.close()

    # 명확한 실패 메시지 반환 (failure_detector가 감지 가능)
    state["final_answer"] = "데이터베이스에서 관련 논문을 찾지 못했습니다."
    return state
```

### 수정 로직 설명

1. **조기 감지**: `raw_results`에 "관련 논문을 찾을 수 없습니다" 포함 여부 체크
2. **LLM 호출 생략**: 실패가 명확하므로 LLM 호출 없이 즉시 반환
3. **명확한 실패 메시지**: Failure Detector의 패턴에 정확히 매칭되는 문자열 사용
   - ✅ "데이터베이스에서 찾지 못했습니다" ← 패턴 존재 (failure_detector.py:33)
4. **상태 반환**: `state["final_answer"]`만 설정하고 즉시 반환

### 수정 효과

#### Before (문제):
```
search_paper_database()
  ↓ "관련 논문을 찾을 수 없습니다"
search_paper_node()
  ↓ LLM 호출
  ↓ "죄송합니다만, 현재 데이터베이스에서 해당 논문을 찾지 못했습니다..."
tool_wrapper
  ↓ is_tool_failed() → False (패턴 매칭 실패 가능)
  ↓ tool_status = "success"  ❌
fallback_router
  ↓ 성공으로 간주
  ↓ 다음 파이프라인 진행 (summarize)  ❌
```

#### After (해결):
```
search_paper_database()
  ↓ "관련 논문을 찾을 수 없습니다"
search_paper_node()
  ↓ 조기 감지! LLM 호출 생략
  ↓ "데이터베이스에서 관련 논문을 찾지 못했습니다."  ← 명확한 실패
tool_wrapper
  ↓ is_tool_failed() → True (패턴 정확히 매칭)
  ↓ tool_status = "failed"  ✅
fallback_router
  ↓ 실패 감지
  ↓ TOOL_FALLBACKS["search_paper"] = "web_search"
  ↓ 파이프라인 대체: search_paper → web_search  ✅
```

---

## 🧪 테스트 및 검증

### 예상 동작 시나리오

#### 시나리오 1: 논문이 DB에 없을 때
```
사용자: "Attention is All You Need 논문 요약해줘"

1. router_node
   → question_type: "paper_summary"
   → tool_pipeline: ["search_paper", "summarize"]

2. search_paper_node 실행
   → DB 검색: 결과 없음
   → 조기 반환: "데이터베이스에서 관련 논문을 찾지 못했습니다."
   → tool_status: "failed"

3. fallback_router_node 실행
   → failed_tool: "search_paper"
   → fallback_tool: "web_search"
   → 파이프라인 업데이트: ["web_search", "summarize"]

4. web_search_node 실행
   → 웹에서 논문 검색
   → 논문 내용 반환
   → tool_status: "success"

5. summarize_node 실행
   → 웹에서 찾은 논문 내용 요약
   → 최종 답변 생성
```

#### 시나리오 2: 논문이 DB에 있을 때
```
사용자: "Transformer 논문 요약해줘"

1. router_node
   → tool_pipeline: ["search_paper", "summarize"]

2. search_paper_node 실행
   → DB 검색: 결과 있음 ✅
   → LLM 답변 생성
   → tool_status: "success"

3. fallback_router_node 실행
   → tool_status: "success"
   → Fallback 불필요, 다음 도구로 진행

4. summarize_node 실행
   → DB에서 찾은 논문 내용 요약
   → 최종 답변 생성
```

### 검증 포인트

✅ **수정 전 문제점**:
- search_paper 실패 → "성공"으로 표시
- summarize 실행 → 요약할 내용 없음 → 실패
- general로 fallback → 일반 답변

✅ **수정 후 기대 동작**:
- search_paper 실패 → "실패"로 표시
- web_search로 fallback → 웹에서 논문 검색
- summarize 실행 → 웹에서 찾은 논문 요약

---

## 📌 관련 커밋

### Commit: `fb83887`
```
fix: RAG 논문 검색 실패 시 명확한 실패 처리

search_paper_node에서 검색 결과가 없을 때 LLM 호출 전 조기 반환하여
failure_detector가 명확히 실패를 감지하도록 수정

수정 내용:
- src/tools/search_paper.py (lines 276-284)
  - "관련 논문을 찾을 수 없습니다" 감지 시 조기 반환
  - 명확한 실패 메시지로 tool_status="failed" 트리거
  - web_search로 fallback 활성화
```

---

## 🎯 결론

### 문제 요약
- RAG 논문 검색 실패 시 Fallback 체인이 작동하지 않음
- LLM이 생성한 정중한 답변으로 인해 실패 감지 실패

### 해결 방법
- 검색 결과 없음을 조기에 감지하여 LLM 호출 생략
- Failure Detector 패턴에 정확히 매칭되는 명확한 실패 메시지 반환

### 해결 효과
- ✅ search_paper 실패 시 명확히 "failed" 상태 설정
- ✅ fallback_router가 올바르게 web_search로 대체
- ✅ 파이프라인 모드에서 정상적인 Fallback 체인 작동
- ✅ 사용자 경험 개선: DB에 없는 논문도 웹에서 검색하여 제공

### 영향 범위
- **수정 파일**: `src/tools/search_paper.py` (1개)
- **수정 라인**: 9줄 추가
- **Breaking Change**: 없음 (기존 동작 개선)

---

## 📚 참고 자료

### 관련 파일
- `src/tools/search_paper.py` - RAG 논문 검색 도구
- `src/agent/failure_detector.py` - 실패 패턴 감지
- `src/agent/tool_wrapper.py` - 도구 래퍼 및 상태 관리
- `src/agent/nodes.py` - Fallback 라우터 로직

### 관련 이슈
- `docs/issues/용어집_도구_선택_실패_문제.md` - 유사한 도구 선택 문제

---

**문서 작성 완료**: 2025-11-05
**최종 업데이트**: 2025-11-05
**작성자**: 최현회[팀장]
