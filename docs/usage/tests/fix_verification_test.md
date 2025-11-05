# 시스템 수정 사항 검증 테스트

## 개요
experiments/20251105/20251105_124240_session_006에서 발생한 에러들을 분석하고 수정했습니다.

## 수정된 사항 (4개)

### 1. Router JSON 파싱 오류 수정 ✅
**파일**: `src/agent/nodes.py:88-106`

**문제**:
- LLM이 \```json 형식으로 응답하여 `KeyError: '```json'` 발생
- 약 10+ 건의 쿼리가 실패

**해결**:
```python
# 마크다운 코드 펜스 제거
if "```" in cleaned_response:
    lines = cleaned_response.split("\n")
    lines = [line for line in lines if not line.strip().startswith("```")]
    cleaned_response = "\n".join(lines).strip()

# 유효하지 않은 도구명 검증
valid_tools = ["general", "glossary", "search_paper", "web_search", "summarize", "text2sql", "save_file"]
if tool_choice not in valid_tools:
    tool_choice = "general"  # 폴백
```

**검증**:
```bash
python scripts/tests/integration/test_router_fix.py
```
결과: ✅ 모든 테스트 통과 (4/4)

---

### 2. SQL WHERE 절 AND/OR 우선순위 오류 수정 ✅
**파일**: `src/tools/text2sql.py:91-103`

**문제**:
- "2022년 이후 Attention 논문" 쿼리가 2021, 2017년 결과 반환
- SQL: `WHERE publish_date >= '2022-01-01' AND abstract ILIKE '%attention%' OR title ILIKE '%attention%'`
- OR 우선순위가 낮아서 `(date >= 2022 AND abstract LIKE) OR (title LIKE)` 로 해석됨

**해결**:
```
프롬프트에 규칙 추가:
"When combining AND/OR in WHERE clause, use parentheses to group OR conditions.
Example: WHERE date >= '2022-01-01' AND (field1 ILIKE '%keyword%' OR field2 ILIKE '%keyword%')"
```

**검증**:
Streamlit UI에서 테스트 필요:
```
질문: "2022년 이후 Attention 메커니즘 관련 논문을 연도별로 보여줘"
예상: 2022년 이후 논문만 반환
```

---

### 3. save_file 도구 개선 ✅
**파일**:
- `src/tools/save_file.py:34-74`
- `src/utils/experiment_manager.py:449-465`

**문제**:
- "저장 해줘" 요청 시 파일에 "저장할 내용이 없습니다." 저장됨
- 파일명에 질문 포함 안됨

**해결**:
```python
# 전체 대화 히스토리를 마크다운 형식으로 저장
messages = state.get("messages", [])
if messages:
    content_lines = ["# 대화 내용\n"]
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "user":
            header = f"## [{i}] 🙋 사용자"
        elif role == "assistant":
            header = f"## [{i}] 🤖 AI"
        content_lines.append(f"{header}\n\n{content}\n")
    content_to_save = "\n".join(content_lines)

# 파일명에 질문 포함
filename = f"{timestamp}_{safe_question}.md"

# outputs/save_data/ 하위 폴더에 저장
save_data_dir = self.outputs_dir / "save_data"
```

**검증**:
Streamlit UI에서 테스트 필요:
```
1. 여러 질문-답변 주고받기
2. "저장 해줘" 입력
3. outputs/save_data/ 폴더 확인
4. 파일명 형식: 날짜_시간_질문문장.md
5. 내용: 전체 대화 히스토리가 마크다운 형식으로 저장
```

---

### 4. 파이프라인 Fallback 로직 추가 ✅
**파일**: `src/agent/nodes.py:162-333`

**문제**:
- "BERT와 GPT 논문 비교해서 분석하고 저장해줘" 질문
- 파이프라인: `search_paper → summarize → general → save_file`
- search_paper 실패 시 바로 general로 이동 (web_search 건너뜀)

**해결**:
```python
# 도구별 Fallback 매핑
TOOL_FALLBACKS = {
    "search_paper": "web_search",    # 논문 검색 실패 → 웹 검색
    "web_search": "general",         # 웹 검색 실패 → 일반 답변
    "summarize": "general",          # 요약 실패 → 일반 답변
    "glossary": "general",           # 용어 검색 실패 → 일반 답변
    "text2sql": "general",           # SQL 실패 → 일반 답변
}

# 파이프라인 모드 감지
is_pipeline = len(tool_pipeline) > 1

if is_pipeline:
    # 실패한 도구를 Fallback 도구로 교체
    fallback_tool = TOOL_FALLBACKS.get(failed_tool)
    if fallback_tool:
        tool_pipeline[current_index] = fallback_tool
        # 파이프라인 계속 진행
```

**검증**:
Streamlit UI에서 테스트 필요:
```
질문: "BERT와 GPT 논문 비교해서 분석하고 저장해줘"
예상 동작:
1. search_paper 시도 (BERT 검색)
2. 실패 시 web_search로 자동 대체
3. 성공하면 summarize 실행
4. general로 비교 분석
5. save_file로 저장
```

---

## Streamlit UI 전체 테스트 계획

### 준비
```bash
python main.py
```
브라우저에서 http://localhost:8501 접속

### 테스트 케이스

#### 1. Router JSON 파싱 에러 해결 확인
**초보자 모드**:
- [x] "LangGraph가 뭐야? langchain과 langgraph 차이를 알려줘"
- [x] "Few-shot learning을 개선한 연구는 어떤게 있어?"
- [x] "LLM의 효율적인 Fine-tuning 기법 논문 찾아줘"
- [x] "Attention이 왜 필요해?"

**예상**: KeyError 없이 정상 응답

#### 2. SQL WHERE 절 수정 확인
**전문가 모드**:
- [ ] "2022년 이후 Attention 메커니즘 관련 논문을 연도별로 보여줘"

**예상**: 2022년 이후 논문만 반환 (2021, 2017년 결과 없음)

#### 3. save_file 개선 확인
**초보자 모드**:
- [ ] "BERT가 뭐야?"
- [ ] "GPT는 뭐야?"
- [ ] "저장 해줘"

**예상**:
- `outputs/save_data/날짜_시간_저장_해줘.md` 파일 생성
- 파일 내용: 전체 대화 히스토리 (사용자와 AI 구분, 마크다운 형식)

#### 4. 파이프라인 Fallback 확인
**전문가 모드**:
- [ ] "BERT와 GPT 논문 비교해서 분석하고 저장해줘"

**예상**:
- search_paper 실패 시 web_search로 자동 대체
- 웹에서 정보 수집하여 비교 분석 제공
- 분석 결과가 파일로 저장됨

#### 5. 멀티턴 대화 테스트
**초보자 모드**:
- [ ] "Transformer가 뭐야?"
- [ ] "그게 왜 중요해?" (이전 대화 컨텍스트 유지 확인)
- [ ] "관련 논문 찾아줘" (이전 대화 컨텍스트 유지 확인)
- [ ] "저장해줘" (전체 대화 저장 확인)

**예상**: 문맥을 유지하며 자연스러운 대화

---

## 커밋 내역

```bash
git log --oneline -5
```

```
7649c72 test: Router JSON 파싱 수정 검증 테스트 추가
790dbf7 feat: 파이프라인 내 도구 실패 시 대체 도구 자동 전환
8826598 fix: Router JSON 파싱 시 마크다운 코드 펜스 제거
f0398e8 feat: save_file 도구 파일명 형식 개선
3bf1bec fix: SQL WHERE 절 AND/OR 우선순위 오류 수정
```

---

## 자동 테스트 실행

### Router 수정 검증
```bash
python scripts/tests/integration/test_router_fix.py
```

**결과**:
```
성공: 4/4
실패: 0/4

✅ 테스트 1: LangGraph가 뭐야? langchain과 langgraph 차이를 알려줘
✅ 테스트 2: Few-shot learning을 개선한 연구는 어떤게 있어?
✅ 테스트 3: LLM의 효율적인 Fine-tuning 기법 논문 찾아줘
✅ 테스트 4: Attention이 왜 필요해?
```

---

## 다음 단계

1. **Streamlit UI 테스트** (수동):
   - main.py 실행
   - 위의 테스트 케이스 실행
   - 로그 및 결과 확인

2. **평가 점수 개선 확인**:
   - 이전 session_006의 평가 점수와 비교
   - evaluation/*.json 파일의 코멘트 피드백 반영 확인

3. **문서화**:
   - 테스트 결과 기록
   - 필요 시 추가 수정 사항 문서화
