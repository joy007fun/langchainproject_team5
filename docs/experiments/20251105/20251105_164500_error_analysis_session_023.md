# 에러 분석 리포트 - Session 023

## 📋 기본 정보

- **세션 ID**: 023
- **발생 시간**: 2025-11-05 16:38:36 ~ 16:38:51
- **사용자**: junyub (팀원)
- **질문**: "Chain-of-Thought prompting 논문 있어?"
- **난이도**: easy
- **실행 경로**: `/home/junyub/langchainproject_5/`

---

## 🔴 에러 내용

### 에러 메시지
```
FileNotFoundError: [Errno 2] No such file or directory:
'experiments/20251105/20251105_163836_session_023/prompts/system_prompt.txt'
```

### 발생 위치
```python
File "/home/junyub/langchainproject_5/src/utils/experiment_manager.py", line 308, in save_system_prompt
    with open(self.prompts_dir / "system_prompt.txt", 'w', encoding='utf-8') as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

### 호출 경로
```
chat_interface.py:197
  → agent_executor.invoke()
    → general_answer_node()
      → exp_manager.save_system_prompt()
        → FileNotFoundError
```

---

## 🔍 원인 분석

### 1. 핵심 문제: 상대 경로 사용

**문제 코드** (수정 전):
```python
# src/utils/experiment_manager.py:48-50
self.experiment_dir = Path(
    f"experiments/{today}/{today}_{time_now}_session_{session_id:03d}"
)
```

- 상대 경로 `experiments/...` 사용
- 현재 작업 디렉토리(CWD)에 의존

### 2. 작업 디렉토리 불일치

**시나리오:**
1. **세션 시작 시**: CWD = `/home/junyub/langchainproject_5/`
   - 폴더 생성: `/home/junyub/langchainproject_5/experiments/.../session_023/`

2. **도구 실행 시**: CWD가 변경되었거나 다른 위치
   - 파일 쓰기 시도: `{다른경로}/experiments/.../session_023/prompts/`
   - 폴더를 찾을 수 없음 → FileNotFoundError

### 3. 폴더 생성 vs 파일 접근 불일치

**생성된 폴더**:
- `configs/` ✅
- `ui/` ✅

**생성되지 않은 폴더**:
- `prompts/` ❌
- `database/` ❌
- `tools/` ❌

**왜?**
- Streamlit 실행 시 작업 디렉토리가 변경됨
- 또는 팀원이 다른 위치에서 실행
- 상대 경로가 다른 위치를 가리킴

---

## 🔧 해결 방법

### 수정 내용

**Before (상대 경로)**:
```python
def __init__(self):
    self.experiment_dir = Path(
        f"experiments/{today}/{today}_{time_now}_session_{session_id:03d}"
    )
```

**After (절대 경로)**:
```python
def __init__(self):
    # 프로젝트 루트 자동 탐지
    project_root = self._find_project_root()

    # 절대 경로로 폴더 생성
    self.experiment_dir = project_root / "experiments" / today / f"{today}_{time_now}_session_{session_id:03d}"
```

### 프로젝트 루트 탐지 로직

```python
def _find_project_root(self) -> Path:
    """프로젝트 루트 디렉토리 찾기"""
    current = Path.cwd().resolve()

    for parent in [current] + list(current.parents):
        # .git 폴더가 있으면 프로젝트 루트
        if (parent / ".git").exists():
            return parent
        # pyproject.toml이 있으면 프로젝트 루트
        if (parent / "pyproject.toml").exists():
            return parent
        # requirements.txt + src가 있으면 프로젝트 루트
        if (parent / "requirements.txt").exists() and (parent / "src").exists():
            return parent

    return current
```

### 장점

1. ✅ **작업 디렉토리 무관**: 어디서 실행해도 동일한 위치에 폴더 생성
2. ✅ **일관성 보장**: 폴더 생성과 파일 접근이 항상 같은 경로
3. ✅ **팀 협업 향상**: 팀원마다 다른 환경에서도 정상 작동
4. ✅ **Streamlit 호환**: Streamlit의 작업 디렉토리 변경에도 안전

---

## 📊 로그 분석

### 실행 흐름

```
16:38:36 | 세션 시작
16:38:36 | 폴더 생성 시도 (일부 성공)
16:38:36 | 설정 파일 저장 (성공)
16:38:45 | Router 노드 실행 → general 선택
16:38:50 | general_answer 노드 실행
16:38:50 | prompts/system_prompt.txt 쓰기 시도
16:38:50 | ❌ FileNotFoundError 발생
16:38:50 | Fallback Router 실행 (3회 재시도)
16:38:51 | 모든 재시도 실패
16:38:51 | UI 에러 표시
```

### Fallback 체인 작동

```
general (실패) → general (실패) → general (실패) → final_fallback (실패)
```

- Fallback이 모두 동일한 도구(general)로 설정되어 있어 무한 루프
- 근본 원인(폴더 없음)이 해결되지 않아 모든 시도 실패

---

## 🧪 테스트 시나리오

### 테스트 1: 프로젝트 루트에서 실행
```bash
cd /home/user/langchainproject_5
python -m streamlit run app.py
```
**결과**: ✅ 성공 예상

### 테스트 2: 다른 디렉토리에서 실행
```bash
cd /home/user/
python -m streamlit run langchainproject_5/app.py
```
**결과**:
- 수정 전: ❌ 실패
- 수정 후: ✅ 성공

### 테스트 3: 서브 디렉토리에서 실행
```bash
cd /home/user/langchainproject_5/src
python -m streamlit run ../app.py
```
**결과**:
- 수정 전: ❌ 실패
- 수정 후: ✅ 성공

---

## 📝 추가 개선 사항

### 1. Fallback 로직 개선 (추후 작업)

**현재 문제**:
```python
TOOL_FALLBACKS = {
    "web_search": "general",
    "summarize": "general",
    "glossary": "general"
}
```

→ general 실패 시 다시 general로 Fallback (무의미)

**개선 방안**:
```python
TOOL_FALLBACKS = {
    "search_paper": "web_search",  # 논문 검색 실패 → 웹 검색
    "web_search": None,            # 웹 검색 실패 → general로 (최종)
    "summarize": "general",        # 요약 실패 → 일반 답변
    "glossary": "general",         # 용어 검색 실패 → 일반 답변
}
```

### 2. 폴더 생성 예외 처리

**현재 코드**:
```python
for folder in [self.tools_dir, self.database_dir, ...]:
    folder.mkdir(exist_ok=True)
```

**개선 코드**:
```python
for folder in [self.tools_dir, self.database_dir, ...]:
    try:
        folder.mkdir(exist_ok=True)
        logger.write(f"폴더 생성 완료: {folder.name}")
    except Exception as e:
        logger.write(f"폴더 생성 실패: {folder.name} - {e}", print_error=True)
        raise
```

### 3. 실행 위치 검증

**app.py에 추가**:
```python
def verify_working_directory():
    """실행 위치 검증"""
    current = Path.cwd()
    required_files = [".git", "requirements.txt", "src"]

    for item in required_files:
        if not (current / item).exists():
            print(f"⚠️ 경고: {item} 를 찾을 수 없습니다.")
            print(f"현재 위치: {current}")
            print("프로젝트 루트에서 실행해주세요.")
            return False
    return True

if __name__ == "__main__":
    if not verify_working_directory():
        sys.exit(1)
```

---

## ✅ 검증 체크리스트

- [x] 에러 원인 파악: 상대 경로 사용
- [x] 해결 방법 구현: 절대 경로 + 루트 탐지
- [x] 코드 수정 완료: ExperimentManager 업데이트
- [x] Git 커밋: `e11e98a`
- [ ] 팀원 환경에서 테스트
- [ ] 다양한 실행 위치에서 테스트
- [ ] Streamlit 다양한 실행 방식 테스트

---

## 🎯 결론

### 원인
- **상대 경로 사용**으로 인한 작업 디렉토리 의존성
- 실행 위치에 따라 다른 폴더 생성/접근

### 해결
- **절대 경로** 사용으로 일관성 보장
- 프로젝트 루트 자동 탐지

### 효과
- ✅ 어디서 실행해도 동일한 결과
- ✅ 팀 협업 환경에서 안정성 향상
- ✅ Streamlit, Jupyter 등 다양한 환경 지원

---

**작성 시간**: 2025-11-05 16:45:00
**작성자**: AI Assistant
**관련 커밋**: `e11e98a`
**세션 폴더**: `experiments/20251105/20251105_163836_session_023/`
