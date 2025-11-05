# test_multi_requests.py 사용법

## 개요

다중 요청 패턴 매칭 시스템의 통합 테스트 스크립트입니다.

**목적**: 2-Tool, 3-Tool, 4-Tool 패턴이 올바르게 매칭되고 실행되는지 검증합니다.

**위치**: `scripts/tests/integration/test_multi_requests.py`

---

## 실행 방법

### 1. 기본 실행

```bash
python scripts/tests/integration/test_multi_requests.py
```

### 2. 프로젝트 루트에서 실행 (권장)

```bash
# 프로젝트 루트 디렉토리에서
python scripts/tests/integration/test_multi_requests.py
```

---

## 테스트 시나리오

### 1. 2-Tool 패턴 (3개 테스트)

#### 1-1. 논문 검색 + 요약
- **질문**: "Attention 논문 찾아서 요약해줘"
- **난이도**: easy
- **예상 도구**: `search_paper` → `summarize`

#### 1-2. 통계 + 논문 검색
- **질문**: "2024년 상위 인용 논문 통계"
- **난이도**: easy
- **예상 도구**: `text2sql` → `search_paper`

#### 1-3. 웹 검색 + 요약
- **질문**: "최신 AI 트렌드 정리해줘"
- **난이도**: easy
- **예상 도구**: `web_search` → `summarize`

### 2. 3-Tool 패턴 (3개 테스트)

#### 2-1. 검색 + 요약 + 저장
- **질문**: "Transformer 논문 검색해서 요약하고 저장해줘"
- **난이도**: easy
- **예상 도구**: `search_paper` → `summarize` → `save_file`

#### 2-2. 통계 + 검색 + 요약
- **질문**: "인용 많은 AI 논문 통계 조회하고 요약해줘"
- **난이도**: hard
- **예상 도구**: `text2sql` → `search_paper` → `summarize`

#### 2-3. 용어 + 검색 + 요약
- **질문**: "Transformer 설명하고 관련 논문 찾아서 요약해줘"
- **난이도**: easy
- **예상 도구**: `glossary` → `search_paper` → `summarize`

### 3. 4-Tool 패턴 (3개 테스트)

#### 3-1. 용어 + 검색 + 요약 + 저장
- **질문**: "Attention 개념 설명하고 관련 논문 정리해서 저장해줘"
- **난이도**: hard
- **예상 도구**: `glossary` → `search_paper` → `summarize` → `save_file`

#### 3-2. 통계 + 검색 + 요약 + 저장
- **질문**: "2024년 상위 인용 논문 통계 보고 찾아서 요약하고 저장해줘"
- **난이도**: hard
- **예상 도구**: `text2sql` → `search_paper` → `summarize` → `save_file`

#### 3-3. 웹 + 요약 + 분석 + 저장
- **질문**: "최신 AI 기술 찾아서 정리하고 분석해서 저장해줘"
- **난이도**: hard
- **예상 도구**: `web_search` → `summarize` → `general` → `save_file`

### 4. 단일 요청 (2개 테스트)

#### 4-1. 용어 검색
- **질문**: "Transformer가 뭐야?"
- **난이도**: easy
- **예상 도구**: `glossary`

#### 4-2. 논문 검색
- **질문**: "BERT 논문 검색해줘"
- **난이도**: hard
- **예상 도구**: `search_paper`

---

## 검증 항목

각 테스트에서 다음을 검증합니다:

1. **도구 파이프라인 매칭**:
   - `tool_pipeline`이 예상 도구 리스트와 정확히 일치하는지 확인
   - 예: `["search_paper", "summarize"]`

2. **답변 생성**:
   - `final_answers`가 비어있지 않은지 확인
   - 생성된 답변 글자 수 확인

3. **실행 성공**:
   - Agent 실행 중 오류가 발생하지 않았는지 확인

---

## 예상 결과

### 성공 시

```bash
$ python scripts/tests/integration/test_multi_requests.py

================================================================================
                     다중 요청 패턴 종합 테스트
================================================================================

실험 매니저 초기화 중...
실험 폴더: experiments/20251105/20251105_140000_session_001


################################################################################
#                          2-Tool 패턴 시작                                    #
################################################################################

================================================================================
[2-Tool 패턴] 테스트 #1: 2-Tool: 논문 검색 + 요약
================================================================================
난이도: easy
질문: Attention 논문 찾아서 요약해줘
예상 도구: search_paper → summarize
--------------------------------------------------------------------------------
Agent 실행 중...

선택된 도구 파이프라인: ['search_paper', 'summarize']
실제 실행된 도구: search_paper
✅ 도구 선택 정확!

생성된 답변 수: 2개
  - elementary: 150 글자
  - beginner: 300 글자


================================================================================
                              테스트 결과
================================================================================
총 테스트: 11개
성공: 11개 (100.0%)
실패: 0개 (0.0%)

================================================================================
```

### 실패 시

```bash
❌ 도구 선택 오류!
   예상: ['search_paper', 'summarize']
   실제: ['search_paper']
```

---

## 주의 사항

1. **실험 폴더**:
   - 테스트 실행 시마다 새로운 실험 폴더가 생성됨
   - `experiments/날짜/시간_session_XXX/` 형식

2. **의존성**:
   - ExperimentManager 필요
   - Agent 그래프 시스템 필요
   - `configs/multi_request_patterns.yaml` 필요

3. **실행 위치**:
   - 프로젝트 루트 디렉토리에서 실행 권장
   - PYTHONPATH 설정 필요 시: `export PYTHONPATH=$PWD`

4. **테스트 시간**:
   - 전체 테스트 실행 시 약 5-10분 소요 (LLM 호출 포함)
   - 각 테스트는 독립적으로 실행됨

---

## 관련 파일

- `configs/multi_request_patterns.yaml`: 다중 요청 패턴 정의
- `src/agent/graph.py`: Agent 그래프 시스템
- `src/agent/router.py`: 패턴 매칭 로직
- `src/utils/experiment_manager.py`: 실험 관리 시스템
- `docs/scenarios/00_통합_시나리오_예상_질문.md`: 시나리오 예시

---

## 트러블슈팅

### 1. 패턴 매칭 실패

**문제**: 예상 도구와 다른 도구가 선택됨

**원인**:
- `multi_request_patterns.yaml`의 키워드가 질문과 일치하지 않음
- 우선순위 설정이 잘못됨 (2-Tool 패턴이 3-Tool보다 먼저 매칭)

**해결**:
```bash
# 우선순위 수정 스크립트 실행
python scripts/data/fix_priorities.py
```

### 2. Import Error

**문제**: `ModuleNotFoundError: No module named 'src'`

**해결**:
```bash
# 프로젝트 루트에서 실행
export PYTHONPATH=$PWD
python scripts/tests/integration/test_multi_requests.py
```

### 3. ExperimentManager 오류

**문제**: 실험 폴더 생성 실패

**해결**:
```bash
# experiments 폴더 확인
mkdir -p experiments
chmod 755 experiments
```
