# test_pipeline.py 사용법

## 개요

Agent 다중 요청 파이프라인 처리 시스템의 통합 테스트 스크립트입니다.

**목적**: 다중 요청 질문이 파이프라인으로 처리되고, 각 도구가 순차적으로 실행되는지 검증합니다.

**위치**: `scripts/tests/integration/test_pipeline.py`

---

## 실행 방법

### 1. 기본 실행

```bash
python scripts/tests/integration/test_pipeline.py
```

### 2. 프로젝트 루트에서 실행 (권장)

```bash
# 프로젝트 루트 디렉토리에서
python scripts/tests/integration/test_pipeline.py
```

---

## 테스트 시나리오

### 기본 테스트: 논문 검색 + 요약

- **질문**: "Attention Mechanism 논문을 찾아서 요약해줘"
- **난이도**: easy
- **예상 파이프라인**: `search_paper` → `summarize`

### 검증 항목

1. **도구 선택 확인**:
   - Router가 올바른 도구를 선택했는지 확인
   - `tool_choice` 필드 검증

2. **파이프라인 실행**:
   - `tool_pipeline`에 2개 도구가 포함되어 있는지 확인
   - `pipeline_index`가 올바르게 증가하는지 확인

3. **도구 상태**:
   - 각 도구 실행 후 `tool_status`가 "success"인지 확인
   - 실패 시 `failure_reason` 확인

4. **실행 타임라인**:
   - `tool_timeline`에 모든 이벤트가 기록되었는지 확인
   - 이벤트 순서: tool_selected → tool_executing → tool_completed

5. **최종 답변**:
   - `final_answer`가 생성되었는지 확인
   - 답변 내용이 비어있지 않은지 확인

---

## 출력 형식

### 실행 시작

```bash
$ python scripts/tests/integration/test_pipeline.py

================================================================================
다중 요청 파이프라인 테스트 시작
질문: Attention Mechanism 논문을 찾아서 요약해줘
난이도: easy
================================================================================
```

### 실행 결과

```bash
================================================================================
실행 결과:
================================================================================
도구 선택: search_paper
도구 상태: success
파이프라인: ['search_paper', 'summarize']
파이프라인 인덱스: 2

실행 타임라인 (6개 이벤트):
  - tool_selected: search_paper (status: N/A)
  - tool_executing: search_paper (status: N/A)
  - tool_completed: search_paper (status: success)
  - tool_selected: summarize (status: N/A)
  - tool_executing: summarize (status: N/A)
  - tool_completed: summarize (status: success)

최종 답변 (200자까지):
Attention Mechanism은 2017년 Vaswani et al.이 제안한 Transformer 모델의 핵심 구성 요소입니다.
이 메커니즘은 입력 시퀀스의 각 위치에서 다른 모든 위치와의 관련성을 계산하여...

================================================================================
테스트 완료
================================================================================
```

### 오류 발생 시

```bash
오류 발생: Router returned invalid tool choice: None
Traceback (most recent call last):
  ...
```

---

## 생성되는 로그 파일

테스트 실행 시 다음 파일들이 생성됩니다:

- `experiments/날짜/시간_session_XXX/chatbot.log`: 전체 실행 로그
- `experiments/날짜/시간_session_XXX/tools/search_paper.log`: 논문 검색 도구 로그
- `experiments/날짜/시간_session_XXX/tools/summarize.log`: 요약 도구 로그
- `experiments/날짜/시간_session_XXX/metadata.json`: 실험 메타데이터

---

## 주의 사항

1. **실험 폴더**:
   - 매 실행마다 새로운 실험 폴더가 생성됨
   - `experiments/날짜/` 디렉토리에 저장

2. **의존성**:
   - ExperimentManager 필요
   - Logger 시스템 필요
   - Agent 그래프 시스템 필요
   - Fallback Chain 시스템 필요

3. **실행 위치**:
   - 프로젝트 루트 디렉토리에서 실행 권장
   - PYTHONPATH 설정 필요 시: `export PYTHONPATH=$PWD`

4. **실행 시간**:
   - 약 1-2분 소요 (LLM 호출 2회 포함)
   - 네트워크 상태에 따라 달라질 수 있음

---

## 디버깅 팁

### 1. 파이프라인이 실행되지 않을 때

로그 파일에서 다음 확인:
```bash
# Router 선택 결과 확인
grep "Router 선택" experiments/날짜/최근폴더/chatbot.log

# 패턴 매칭 결과 확인
grep "패턴 매칭" experiments/날짜/최근폴더/chatbot.log
```

### 2. 도구 실행이 실패할 때

타임라인에서 실패 지점 확인:
```python
timeline = result.get("tool_timeline", [])
for event in timeline:
    if event.get('status') == 'failed':
        print(f"실패: {event}")
```

### 3. 답변이 생성되지 않을 때

상태 확인:
```python
print("tool_status:", result.get("tool_status"))
print("failure_reason:", result.get("failure_reason"))
print("final_answer:", result.get("final_answer"))
```

---

## 관련 파일

- `src/agent/graph.py`: Agent 그래프 및 파이프라인 처리 로직
- `src/agent/router.py`: 다중 요청 패턴 매칭
- `src/agent/state.py`: Agent 상태 정의
- `src/utils/experiment_manager.py`: 실험 관리
- `src/utils/logger.py`: 로깅 시스템
- `configs/multi_request_patterns.yaml`: 패턴 정의

---

## 확장 방법

### 다른 패턴 테스트

스크립트를 수정하여 다른 패턴 테스트:

```python
# 3-Tool 패턴 테스트
question = "Transformer 논문 검색해서 요약하고 저장해줘"
# 예상: ['search_paper', 'summarize', 'save_file']

# 4-Tool 패턴 테스트
question = "Attention 개념 설명하고 관련 논문 정리해서 저장해줘"
# 예상: ['glossary', 'search_paper', 'summarize', 'save_file']
```

### 여러 질문 일괄 테스트

```python
questions = [
    "Attention 논문 찾아서 요약해줘",
    "Transformer 설명하고 논문 찾아줘",
    "최신 AI 트렌드 정리해서 저장해줘"
]

for q in questions:
    test_multi_request(q)
```

---

## 트러블슈팅

### 1. "No module named 'src'" 오류

**해결**:
```bash
export PYTHONPATH=$PWD
python scripts/tests/integration/test_pipeline.py
```

### 2. "ExperimentManager 초기화 실패" 오류

**원인**: experiments 폴더 권한 문제

**해결**:
```bash
mkdir -p experiments
chmod 755 experiments
```

### 3. "Router returned invalid tool choice" 오류

**원인**: 패턴 매칭 실패 또는 Router LLM 호출 오류

**해결**:
```bash
# 패턴 파일 확인
cat configs/multi_request_patterns.yaml

# API 키 확인
echo $OPENAI_API_KEY
```
