# quick_test.py 사용법

## 개요

다중 요청 패턴 매칭의 빠른 검증 테스트 스크립트입니다.

**목적**: 2-Tool, 3-Tool, 4-Tool 패턴이 올바르게 매칭되는지 빠르게 확인합니다.

**특징**:
- 간단한 출력 형식
- 3개 대표 시나리오만 테스트
- 빠른 실행 (전체 테스트보다 짧음)

**위치**: `scripts/tests/integration/quick_test.py`

---

## 실행 방법

### 1. 기본 실행

```bash
python scripts/tests/integration/quick_test.py
```

### 2. 프로젝트 루트에서 실행 (권장)

```bash
# 프로젝트 루트 디렉토리에서
python scripts/tests/integration/quick_test.py
```

---

## 테스트 시나리오

### 1. 2-Tool 패턴

- **이름**: 논문 검색 + 요약
- **질문**: "Attention 논문 찾아서 요약해줘"
- **난이도**: easy
- **예상 도구**: `search_paper` → `summarize`

### 2. 3-Tool 패턴

- **이름**: 검색 + 요약 + 저장
- **질문**: "Transformer 논문 검색해서 요약하고 저장해줘"
- **난이도**: easy
- **예상 도구**: `search_paper` → `summarize` → `save_file`

### 3. 4-Tool 패턴

- **이름**: 용어 + 검색 + 요약 + 저장
- **질문**: "Attention 개념 설명하고 관련 논문 정리해서 저장해줘"
- **난이도**: hard
- **예상 도구**: `glossary` → `search_paper` → `summarize` → `save_file`

---

## 출력 형식

### 실행 시작

```bash
$ python scripts/tests/integration/quick_test.py

실험 매니저 초기화...
실험 폴더: experiments/20251105/20251105_140000_session_001
Agent 그래프 생성...

총 3개 테스트 실행
```

### 각 테스트 출력

```bash
================================================================================
테스트 #1: 2-Tool: 논문 검색 + 요약
================================================================================
질문: Attention 논문 찾아서 요약해줘
난이도: easy
예상 도구: search_paper → summarize
--------------------------------------------------------------------------------
Agent 실행 중...

실제 도구: search_paper → summarize
✅ 성공!
```

### 전체 완료

```bash
================================================================================
테스트 #3: 4-Tool: 용어 + 검색 + 요약 + 저장
================================================================================
질문: Attention 개념 설명하고 관련 논문 정리해서 저장해줘
난이도: hard
예상 도구: glossary → search_paper → summarize → save_file
--------------------------------------------------------------------------------
Agent 실행 중...

실제 도구: glossary → search_paper → summarize → save_file
✅ 성공!

테스트 완료
```

### 실패 시

```bash
실제 도구: search_paper → summarize
❌ 실패! (예상: ['search_paper', 'summarize', 'save_file'])
```

### 오류 시

```bash
❌ 오류: Router returned None
Traceback (most recent call last):
  ...
```

---

## test_multi_requests.py와의 차이점

| 항목 | quick_test.py | test_multi_requests.py |
|------|---------------|------------------------|
| 테스트 개수 | 3개 (대표 시나리오) | 11개 (전체 시나리오) |
| 출력 형식 | 간단 (성공/실패만) | 상세 (답변 글자수, 카테고리별) |
| 실행 시간 | 약 2-3분 | 약 5-10분 |
| 용도 | 빠른 검증, 디버깅 | 종합 테스트 |
| 통계 | 없음 | 성공률 통계 제공 |

---

## 사용 시나리오

### 1. 패턴 파일 수정 후 빠른 검증

```bash
# multi_request_patterns.yaml 수정 후
vim configs/multi_request_patterns.yaml

# 빠른 검증
python scripts/tests/integration/quick_test.py
```

### 2. 우선순위 수정 후 확인

```bash
# 우선순위 수정
python scripts/data/fix_priorities.py

# 검증
python scripts/tests/integration/quick_test.py
```

### 3. Agent 그래프 수정 후 테스트

```bash
# graph.py 수정 후
vim src/agent/graph.py

# 동작 확인
python scripts/tests/integration/quick_test.py
```

---

## 주의 사항

1. **실험 폴더**:
   - 테스트 실행 시마다 새로운 실험 폴더 생성
   - `exp_manager.close()`로 자동 정리

2. **의존성**:
   - ExperimentManager 필요
   - Agent 그래프 시스템 필요
   - `configs/multi_request_patterns.yaml` 필요

3. **실행 위치**:
   - 프로젝트 루트 디렉토리에서 실행 권장
   - PYTHONPATH 설정: `export PYTHONPATH=$PWD`

4. **실행 시간**:
   - 약 2-3분 소요 (LLM 호출 6회)
   - 네트워크 속도에 따라 달라질 수 있음

---

## 커스터마이징

### 다른 질문으로 테스트

스크립트 수정:

```python
tests = [
    {
        "name": "커스텀 2-Tool",
        "question": "BERT 논문 찾아서 설명해줘",
        "difficulty": "beginner",
        "expected": ["search_paper", "summarize"]
    },
    # ... 추가 테스트
]
```

### 더 많은 시나리오 추가

```python
tests.append({
    "name": "웹 검색 + 요약",
    "question": "최신 AI 트렌드 정리해줘",
    "difficulty": "easy",
    "expected": ["web_search", "summarize"]
})
```

---

## 디버깅 팁

### 1. 특정 패턴만 테스트

```python
# 스크립트에서 특정 테스트만 실행
tests = [tests[0]]  # 첫 번째 테스트만
```

### 2. 상세 로그 확인

```python
# 결과 상세 출력
print("전체 결과:", result)
print("타임라인:", result.get("tool_timeline"))
```

### 3. 실험 폴더 유지

```python
# exp_manager.close() 주석 처리
# exp_manager.close()
```

---

## 관련 파일

- `scripts/tests/integration/test_multi_requests.py`: 전체 테스트 스크립트
- `scripts/tests/integration/test_pipeline.py`: 파이프라인 상세 테스트
- `configs/multi_request_patterns.yaml`: 패턴 정의
- `src/agent/graph.py`: Agent 그래프 시스템
- `src/agent/router.py`: 패턴 매칭 로직

---

## 트러블슈팅

### 1. "No module named 'src'" 오류

**해결**:
```bash
export PYTHONPATH=$PWD
python scripts/tests/integration/quick_test.py
```

### 2. 모든 테스트 실패

**원인**: 패턴 파일 문제 또는 Router 오류

**확인**:
```bash
# 패턴 파일 존재 확인
ls -l configs/multi_request_patterns.yaml

# 패턴 파일 문법 확인
python -c "import yaml; yaml.safe_load(open('configs/multi_request_patterns.yaml'))"
```

### 3. 특정 패턴만 실패

**원인**: 우선순위 문제 또는 키워드 미매칭

**해결**:
```bash
# 우선순위 재조정
python scripts/data/fix_priorities.py

# 재테스트
python scripts/tests/integration/quick_test.py
```

### 4. LLM 호출 오류

**원인**: API 키 문제

**확인**:
```bash
# API 키 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env | grep OPENAI_API_KEY
```

---

## 성능 비교

### 실행 시간

- **quick_test.py**: 2-3분 (3개 시나리오)
- **test_multi_requests.py**: 5-10분 (11개 시나리오)
- **test_pipeline.py**: 1-2분 (1개 시나리오, 상세 로그)

### 권장 사용법

| 상황 | 추천 스크립트 |
|------|---------------|
| 빠른 검증 | quick_test.py |
| 종합 테스트 | test_multi_requests.py |
| 파이프라인 디버깅 | test_pipeline.py |
| CI/CD | test_multi_requests.py |
| 개발 중 | quick_test.py |
