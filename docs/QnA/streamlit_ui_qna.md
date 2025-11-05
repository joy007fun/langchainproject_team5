# Streamlit UI Q&A

## 문서 정보
- **작성일**: 2025-11-04
- **작성자**: 최현화[팀장]
- **목적**: Streamlit UI 시스템 관련 자주 묻는 질문 및 답변

---

## 목차
1. [기본 개념](#1-기본-개념)
2. [채팅 관리](#2-채팅-관리)
3. [난이도 시스템](#3-난이도-시스템)
4. [메시지 처리](#4-메시지-처리)
5. [세션 상태](#5-세션-상태)
6. [파일 저장](#6-파일-저장)
7. [트러블슈팅](#7-트러블슈팅)
8. [고급 활용](#8-고급-활용)

---

## 1. 기본 개념

### Q1-1. Streamlit UI 시스템이란?

**A:** **논문 리뷰 챗봇의 웹 인터페이스를 제공하는 시스템**입니다.

**주요 기능:**
1. **다중 채팅 세션**: 여러 대화를 동시에 관리
2. **난이도 선택**: Easy (초급) / Hard (전문가) 모드
3. **ChatGPT 스타일 UI**: 날짜별 그룹화된 채팅 목록
4. **메시지 복사**: 각 AI 답변마다 복사 버튼
5. **채팅 저장/내보내기**: Markdown 형식으로 대화 기록 저장
6. **Agent 통합**: LangGraph AI Agent와 실시간 연동

**파일 구조:**
```
ui/
├── app.py                      # 메인 애플리케이션
└── components/
    ├── sidebar.py              # 사이드바 (난이도, 채팅 목록)
    ├── chat_interface.py       # 채팅 UI (메시지 입출력)
    ├── chat_manager.py         # 채팅 세션 관리
    ├── storage.py              # 로컬 저장소
    └── file_download.py        # 파일 다운로드
```

---

### Q1-2. Streamlit과 다른 프레임워크의 차이는?

**A:**

| 프레임워크 | 장점 | 단점 | 사용 시나리오 |
|-----------|------|------|--------------|
| **Streamlit** | 빠른 개발, Python만 사용 | 제한적 커스터마이징 | 프로토타입, 내부 도구 |
| **Flask/FastAPI** | 유연성, REST API | HTML/CSS/JS 필요 | 프로덕션 API |
| **React** | 완전한 제어 | 프론트/백 분리, 복잡 | 대규모 웹 앱 |
| **Gradio** | 매우 빠른 개발 | UI 디자인 제한 | ML 데모 |

**본 프로젝트에서 Streamlit 선택 이유:**
- Python만으로 전체 UI 구현 가능
- AI Agent 통합이 간편
- 빠른 프로토타이핑
- ChatGPT 스타일 UI 구현 용이

---

### Q1-3. Streamlit 실행 방법은?

**A:**

**기본 실행:**
```bash
# 메인 앱 실행
streamlit run ui/app.py

# 자동으로 브라우저 열림
# http://localhost:8501
```

**포트 변경:**
```bash
streamlit run ui/app.py --server.port 8080
```

**헤드리스 모드 (서버에서):**
```bash
streamlit run ui/app.py --server.headless true
```

**환경변수 설정 후 실행:**
```bash
export OPENAI_API_KEY="sk-..."
export SOLAR_API_KEY="..."
export DATABASE_URL="postgresql://..."

streamlit run ui/app.py
```

---

### Q1-4. UI 폴더 구조는 어떻게 되나요?

**A:**

```
ui/
├── app.py                          # 메인 애플리케이션
│   ├── 페이지 설정
│   ├── 세션 상태 초기화
│   └── 사이드바 + 채팅 UI 렌더링
│
└── components/
    ├── sidebar.py                  # 사이드바 컴포넌트
    │   ├── 난이도 선택
    │   ├── 새 채팅 버튼
    │   ├── 채팅 목록 (날짜별 그룹화)
    │   └── 저장/삭제 버튼
    │
    ├── chat_interface.py           # 채팅 인터페이스
    │   ├── 메시지 표시 (사용자/AI)
    │   ├── 입력 처리
    │   ├── Agent 호출
    │   ├── 복사 버튼
    │   └── 용어 자동 추출
    │
    ├── chat_manager.py             # 채팅 관리
    │   ├── 새 채팅 생성
    │   ├── 채팅 전환
    │   ├── 메시지 추가
    │   ├── 채팅 삭제
    │   └── Markdown 내보내기
    │
    ├── storage.py                  # 로컬 저장소
    │   ├── 채팅 로컬 저장
    │   ├── 채팅 로드
    │   └── 저장소 정리
    │
    └── file_download.py            # 파일 다운로드
        └── Markdown 다운로드 버튼
```

---

## 2. 채팅 관리

### Q2-1. 새 채팅은 어떻게 생성되나요?

**A:** **"새 채팅" 버튼을 클릭하면 선택된 난이도로 채팅이 생성**됩니다.

**생성 과정:**
```python
# 1. 고유 ID 생성
chat_id = f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}"

# 2. 채팅 데이터 구조 생성
new_chat = {
    "id": chat_id,
    "title": "새 채팅",
    "created_at": "2025-11-04 10:30:15",
    "difficulty": "easy",  # 사이드바에서 선택한 난이도
    "messages": [],
    "experiment_dir": None
}

# 3. session_state에 저장
st.session_state.chats[chat_id] = new_chat
st.session_state.current_chat_id = chat_id
```

**제목 자동 생성:**
- 첫 메시지 입력 시 자동으로 제목 업데이트
- 예: "새 채팅" → "Transformer 논문 설명해줘"

---

### Q2-2. 채팅 목록은 어떻게 그룹화되나요?

**A:** **ChatGPT 스타일로 날짜별로 그룹화**됩니다.

**그룹 분류:**
1. **오늘**: 오늘 생성된 채팅
2. **어제**: 어제 생성된 채팅
3. **지난 7일**: 7일 이내 생성된 채팅
4. **그 이전**: 7일 이전 생성된 채팅

**코드:**
```python
def group_chats_by_date(chat_list):
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_ago = today_start - timedelta(days=7)

    groups = {
        "오늘": [],
        "어제": [],
        "지난 7일": [],
        "그 이전": []
    }

    for chat in chat_list:
        created_at = datetime.strptime(chat["created_at"], "%Y-%m-%d %H:%M:%S")

        if created_at >= today_start:
            groups["오늘"].append(chat)
        elif created_at >= yesterday_start:
            groups["어제"].append(chat)
        elif created_at >= week_ago:
            groups["지난 7일"].append(chat)
        else:
            groups["그 이전"].append(chat)

    return {k: v for k, v in groups.items() if v}
```

**UI 표시:**
```
사이드바:
  📁 오늘
    • Transformer 논문 설명해줘
    • RAG 시스템 구조
  📁 어제
    • GAN 설명
  📁 지난 7일
    • BERT vs GPT
    • Attention 메커니즘
```

---

### Q2-3. 채팅을 삭제하면 어떻게 되나요?

**A:** **채팅 데이터가 session_state에서 삭제**됩니다.

**삭제 과정:**
```python
def delete_chat(chat_id):
    # 1. session_state에서 채팅 삭제
    if chat_id in st.session_state.chats:
        del st.session_state.chats[chat_id]

    # 2. 현재 채팅이었다면 다른 채팅으로 전환
    if st.session_state.current_chat_id == chat_id:
        remaining_chats = list(st.session_state.chats.keys())
        if remaining_chats:
            st.session_state.current_chat_id = remaining_chats[0]
        else:
            # 채팅이 없으면 새 채팅 생성
            create_new_chat(difficulty="easy")
```

**주의:**
- 삭제된 채팅은 복구 불가능
- `experiments/` 폴더의 실험 데이터는 삭제되지 않음 (별도 관리)

---

### Q2-4. 채팅을 Markdown으로 내보내려면?

**A:** **"💾 저장" 버튼을 클릭하면 Markdown 파일로 다운로드**됩니다.

**Markdown 형식:**
```markdown
# Transformer 논문 설명해줘

**생성일**: 2025-11-04 10:30:15
**난이도**: Easy 모드 (초급)

---

## 대화 1

**나**: Transformer 논문 설명해줘

**AI**:
Transformer는 2017년 Google에서 발표한...
(전체 답변 내용)

---

## 대화 2

**나**: Self-Attention은 뭐야?

**AI**:
Self-Attention은...

---

**총 대화 수**: 2개
```

**코드:**
```python
def export_chat(chat_id):
    chat = st.session_state.chats[chat_id]

    markdown = f"# {chat['title']}\n\n"
    markdown += f"**생성일**: {chat['created_at']}\n"
    markdown += f"**난이도**: {chat['difficulty']}\n\n"
    markdown += "---\n\n"

    for i, msg in enumerate(chat['messages'], 1):
        role = "나" if msg["role"] == "user" else "AI"
        markdown += f"## 대화 {i}\n\n"
        markdown += f"**{role}**: {msg['content']}\n\n"
        markdown += "---\n\n"

    markdown += f"**총 대화 수**: {len(chat['messages']) // 2}개"

    return markdown
```

---

## 3. 난이도 시스템

### Q3-1. Easy와 Hard 모드의 차이는?

**A:** 각 모드는 **두 가지 수준의 답변을 동시에 생성**하며, UI에서 탭으로 표시됩니다.

| 모드 | 생성되는 수준 | LLM | 대상 | UI 표시 |
|------|-------------|-----|------|---------|
| **Easy 모드** | Elementary (초등학생용 8-13세) + Beginner (초급자용 14-22세) | Solar Pro2 | 학생 및 초심자 | 2개 탭 |
| **Hard 모드** | Intermediate (중급자용 23-30세) + Advanced (고급자용 30세 이상) | GPT-5 | 전문가 및 연구자 | 2개 탭 |

**각 수준별 특징:**

| 수준 | 대상 | 용어 | 수식 | 설명 방식 | 비용 |
|------|------|------|------|----------|------|
| **Elementary** | 초등학생 (8-13세) | 초등학생도 이해 가능 | 없음 | 일상 비유 | 저렴 |
| **Beginner** | 초급자 (14-22세) | 쉬운 말 풀어쓰기 | 최소화 | 비유/예시 | 저렴 |
| **Intermediate** | 중급자 (23-30세) | 전문 용어 일부 | 기본 수식 | 기술적 설명 | 높음 |
| **Advanced** | 고급자 (30세 이상) | 전문 용어 자유 | 수식 포함 | 구현 세부사항 | 높음 |

**예시 비교 (Easy 모드):**

**질문:** "Attention 메커니즘 설명해줘"

**탭 1: 초등학생용 (8-13세)**
```
Attention은 '주의를 기울인다'는 뜻이에요.

만화책을 읽을 때를 생각해볼까요?
중요한 장면은 크게 그려져 있고, 배경은 작게 그려져 있죠?
Attention도 똑같아요. 중요한 단어를 크게 보고, 덜 중요한 단어는 작게 봐요.

예: "나는 학교에 간다"
→ "간다"를 이해하려면 "나는"과 "학교에"를 같이 봐야 해요!
```

**탭 2: 초급자용 (14-22세)**
```
Attention은 문장에서 어떤 단어가 중요한지 자동으로 찾아내는 기술입니다.

번역 예시로 설명하면:
- 영문: "I love you"
- "love"를 번역할 때 "I"(누가)와 "you"(누구를) 집중해서 봄
- 결과: "사랑해"

즉, 문맥을 파악하기 위해 관련된 단어들에 집중하는 것이죠.
```

**예시 비교 (Hard 모드 - 첫 번째 탭만 표시):**

**탭 1: 중급자용 (23-30세)**
```
Attention Mechanism은 입력 시퀀스에서 관련성 높은 정보를 선택적으로 가중합하는 메커니즘입니다.

핵심 구성요소:
- Query: 현재 처리 중인 토큰의 표현
- Key: 참조할 수 있는 모든 토큰의 표현
- Value: 실제 정보를 담고 있는 토큰의 표현

간단한 수식: Attention(Q,K,V) = softmax(QK^T) × V
```

---

### Q3-2. 난이도는 언제 선택하나요?

**A:** **사이드바에서 선택하며, 새 채팅 생성 시 적용**됩니다.

**선택 UI:**
```
사이드바:
  ⚙️ 설정

  📚 답변 난이도 선택
  ○ Easy 모드 (초급) - 쉬운 설명, 비유 중심
  ● Hard 모드 (전문가) - 기술적 세부사항, 수식 포함

  [+ 새 채팅] 버튼  ← 선택된 난이도로 채팅 생성
```

**동작:**
1. **난이도 선택**: Easy 또는 Hard 선택
2. **새 채팅 클릭**: 선택된 난이도로 채팅 생성
3. **채팅마다 고정**: 각 채팅은 생성 시 난이도로 고정
4. **변경 방법**: 새 채팅 생성 (기존 채팅 난이도는 변경 불가)

---

### Q3-3. 채팅마다 다른 난이도를 사용할 수 있나요?

**A:** 네, **각 채팅은 독립적인 난이도를 가집니다.**

**예시:**
```
📁 오늘
  • [Easy] Transformer 설명 ← Easy 모드 채팅
  • [Hard] BERT 구조 분석 ← Hard 모드 채팅

📁 어제
  • [Easy] GAN 기본 개념 ← Easy 모드 채팅
```

**코드:**
```python
# 채팅 데이터 구조
chat = {
    "id": "chat_20251104103015",
    "title": "Transformer 설명",
    "difficulty": "easy",  # 이 채팅은 Easy 모드로 고정
    "messages": [...]
}
```

**실전 활용:**
- 기본 개념: Easy 모드 채팅
- 심화 학습: Hard 모드 채팅
- 빠른 질문: Easy 모드 (응답 시간 단축)
- 논문 리뷰: Hard 모드 (기술적 세부사항)

---

## 4. 메시지 처리

### Q4-1. 사용자 메시지 입력 과정은?

**A:**

```
1. 사용자가 텍스트 입력 (st.chat_input)
    ↓
2. 메시지 추가 (chat_manager.add_message)
    ↓
3. UI에 사용자 메시지 표시
    ↓
4. ExperimentManager 초기화
    ↓
5. AI Agent 호출 (agent_executor.invoke)
    ↓
6. Agent가 도구 선택 및 실행
    ↓
7. 최종 답변 생성
    ↓
8. AI 메시지 추가 (chat_manager.add_message)
    ↓
9. UI에 AI 답변 표시
    ↓
10. 용어 자동 추출 및 저장 (선택적)
```

**코드 (chat_interface.py):**
```python
# 사용자 입력
if user_input := st.chat_input("질문을 입력하세요"):
    # 1. 사용자 메시지 추가
    add_message("user", user_input)

    # 2. UI 표시
    with st.chat_message("user"):
        st.markdown(user_input)

    # 3. Agent 호출
    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            # Agent 실행
            result = agent_executor.invoke({
                "question": user_input,
                "difficulty": difficulty
            })

            answer = result["final_answer"]

            # 4. AI 메시지 추가
            add_message("assistant", answer)

            # 5. UI 표시
            st.markdown(answer)
```

---

### Q4-2. 메시지 복사 기능은 어떻게 동작하나요?

**A:** **각 AI 답변마다 복사 버튼이 제공**됩니다.

**UI:**
```
AI: Transformer는 2017년 Google에서 발표한...

[📋 복사] 버튼
```

**코드:**
```python
# 복사 버튼 (JavaScript 사용)
copy_button = f"""
<button onclick="navigator.clipboard.writeText(`{answer.replace('`', '\\`')}`)">
    📋 복사
</button>
"""

st.markdown(copy_button, unsafe_allow_html=True)
```

**작동 방식:**
1. 사용자가 "📋 복사" 버튼 클릭
2. JavaScript `navigator.clipboard.writeText()` 실행
3. AI 답변이 클립보드에 복사됨
4. 사용자가 다른 곳에 붙여넣기 (Ctrl+V)

---

### Q4-3. 메시지는 어디에 저장되나요?

**A:** **Streamlit session_state와 로컬 파일 시스템 두 곳에 저장**됩니다.

**1. session_state (메모리):**
```python
st.session_state.chats = {
    "chat_20251104103015": {
        "id": "chat_20251104103015",
        "title": "Transformer 설명",
        "messages": [
            {"role": "user", "content": "Transformer 설명해줘"},
            {"role": "assistant", "content": "Transformer는..."}
        ]
    }
}
```

**2. 로컬 파일 (영구 저장, 선택):**
```
.streamlit/
└── chat_storage.json
```

**저장 시점:**
- **session_state**: 즉시 저장 (실시간)
- **로컬 파일**: "💾 저장" 버튼 클릭 시 (수동)

**제한:**
- session_state는 브라우저 새로고침 시 초기화됨
- 로컬 파일 저장으로 영구 보존 가능

---

### Q4-4. 긴 답변은 어떻게 표시되나요?

**A:** **Streamlit의 Markdown 렌더링으로 자동 포맷팅**됩니다.

**지원 형식:**
- **헤더**: `# 제목`, `## 소제목`
- **리스트**: `- 항목`, `1. 번호`
- **코드 블록**: ` ```python ... ``` `
- **수식**: `$E=mc^2$` (LaTeX)
- **표**: `| 항목 | 값 |`

**예시:**
```markdown
## Transformer 구조

Transformer는 다음 구성 요소로 이루어져 있습니다:

1. **Encoder**
   - Self-Attention
   - Feed-Forward Network

2. **Decoder**
   - Masked Self-Attention
   - Cross-Attention

```python
class Transformer(nn.Module):
    def __init__(self):
        self.encoder = Encoder()
        self.decoder = Decoder()
```

**수식:**
$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$
```

**렌더링:**
- 헤더, 리스트, 코드 블록이 모두 정상 표시
- 수식도 LaTeX 렌더링 (Streamlit 지원)

---

### Q4-5. 답변 품질 평가는 어떻게 이루어지나요?

**A:** **모든 답변은 자동으로 LLM-as-a-Judge 방식으로 실시간 평가**됩니다.

**평가 시점:**
- Agent가 답변 생성 완료 후 자동 실행
- 백그라운드에서 처리 (사용자 경험에 영향 최소화)

**평가 기준 (4가지):**

| 기준 | 만점 | 설명 |
|------|------|------|
| **정확도 (Accuracy)** | 10점 | 참고 문서와의 일치도, 사실 관계 정확성 |
| **관련성 (Relevance)** | 10점 | 질문과 답변의 관련도, 핵심 내용 포함 여부 |
| **난이도 적합성 (Difficulty)** | 10점 | Easy/Hard 모드에 맞는 설명 수준 |
| **출처 명시 (Citation)** | 10점 | 논문 제목, 저자, 연도 명시 여부 |
| **총점 (Total)** | 40점 | 4가지 기준의 합계 |

**평가 결과 저장:**
1. **PostgreSQL DB**: `evaluation_results` 테이블에 저장
2. **experiments/ 폴더**: `evaluation/evaluation_{timestamp}.json` 파일로 저장
3. **UI 표시**: 답변 하단에 expander로 표시

**UI 표시 예시:**
```
📊 답변 품질 평가 결과 (접힌 상태)
  ┌─────────────────────────┐
  │ 정확도: 9/10            │
  │ 관련성: 10/10           │
  │ 난이도 적합성: 8/10     │
  │ 출처 명시: 7/10         │
  │ ─────────────────────   │
  │ 총점: 34/40             │
  │                         │
  │ 💬 평가 코멘트:          │
  │ 답변이 정확하고 관련성   │
  │ 이 높음. 출처 명시가     │
  │ 일부 부족함.            │
  └─────────────────────────┘
```

**평가 프로세스:**
1. 사용자 질문 → Agent 답변 생성
2. 답변 표시 → "📊 답변 품질 평가 중..." 스피너 표시
3. `AnswerEvaluator` 클래스가 GPT-5로 평가 수행
   - `configs/model_config.yaml`의 `llm.production.model` 설정을 최우선시
   - 기본값: `gpt-5`
   - 재시도: `llm.production.max_retries` 설정값 사용 (기본값: 3번)
4. 평가 결과 DB 저장 + evaluation 폴더 저장
5. UI에 토스트 메시지 표시: "✅ 답변 평가 완료: 34/40점"
6. 답변 하단에 expander로 상세 결과 표시

**평가 실패 시:**
- 평가 실패해도 답변은 정상 표시 (메인 기능에 영향 없음)
- 에러 로그만 기록하고 조용히 실패 처리
- 사용자에게는 경고 메시지만 표시

**관련 파일:**
- `src/evaluation/evaluator.py` - 평가 로직
- `ui/components/chat_interface.py` - UI 통합 (line 328-394)
- `src/evaluation/storage.py` - DB 저장

---

## 5. 세션 상태

### Q5-1. session_state란?

**A:** **Streamlit에서 제공하는 앱 전역 상태 저장소**입니다.

**주요 데이터:**
```python
st.session_state = {
    "chats": {},                 # 모든 채팅 데이터
    "current_chat_id": None,     # 현재 활성 채팅 ID
    "last_difficulty": "easy",   # 마지막 선택 난이도
    "dark_mode": False,          # 다크 모드 여부
    "copied_message": None       # 복사된 메시지 임시 저장
}
```

**초기화 시점:**
```python
# app.py
if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
```

**특징:**
- **전역 접근**: 모든 컴포넌트에서 접근 가능
- **자동 동기화**: 값 변경 시 UI 자동 업데이트
- **휘발성**: 브라우저 새로고침 시 초기화 (영구 저장 아님)

---

### Q5-2. 브라우저를 닫으면 채팅이 사라지나요?

**A:** **네, session_state는 휘발성**입니다.

**해결 방법:**

**1. 로컬 저장소 사용 (선택):**
```python
# storage.py
def save_chats_to_local_storage():
    chat_data = st.session_state.chats
    with open('.streamlit/chat_storage.json', 'w', encoding='utf-8') as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)

def load_chats_from_local_storage():
    if os.path.exists('.streamlit/chat_storage.json'):
        with open('.streamlit/chat_storage.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
```

**2. 데이터베이스 저장 (향후):**
```sql
CREATE TABLE chat_sessions (
    chat_id VARCHAR(50) PRIMARY KEY,
    title TEXT,
    difficulty VARCHAR(10),
    messages JSONB,
    created_at TIMESTAMP
);
```

**3. Markdown 내보내기:**
- "💾 저장" 버튼으로 Markdown 파일 다운로드
- 수동으로 파일 보관

---

### Q5-3. session_state 초기화는 언제 발생하나요?

**A:**

**초기화 시점:**
1. **브라우저 새로고침** (F5)
2. **브라우저 탭 닫기**
3. **Streamlit 서버 재시작**

**초기화 방지 방법:**

**1. 자동 저장 활성화:**
```python
# app.py
import atexit

# 앱 종료 시 자동 저장
atexit.register(save_chats_to_local_storage)
```

**2. 주기적 저장:**
```python
# 5분마다 자동 저장
if datetime.now().minute % 5 == 0:
    save_chats_to_local_storage()
```

**3. 사용자 알림:**
```python
st.warning("⚠️ 브라우저를 닫기 전에 '💾 저장' 버튼을 클릭하세요!")
```

---

## 6. 파일 저장

### Q6-1. 답변을 파일로 저장하려면?

**A:** **save_file 도구를 사용**하거나 **"💾 저장" 버튼을 클릭**합니다.

**방법 1: save_file 도구 (Agent 자동 호출)**
```
사용자: "Transformer 논문 요약하고 파일로 저장해줘"
    ↓
Agent: [summarize, save_file] 도구 선택 (향후 지원)
    ↓
summarize 도구: 요약 생성
    ↓
save_file 도구: experiments/.../outputs/summary.md 저장
    ↓
답변: "summary.md 파일로 저장되었습니다."
```

**방법 2: Markdown 내보내기 (수동)**
```
사이드바에서 "💾 저장" 버튼 클릭
    ↓
Markdown 파일 다운로드
    ↓
브라우저 다운로드 폴더에 저장
```

---

### Q6-2. experiments/ 폴더와의 관계는?

**A:** **ExperimentManager가 experiments/ 폴더에 자동 저장**합니다.

**저장 위치:**
```
experiments/
└── 20251104/
    └── 20251104_103015_session_001/
        ├── metadata.json
        ├── chatbot.log
        ├── tools/
        │   └── search_paper.log
        ├── database/
        │   ├── queries.sql
        │   └── search_results.json
        ├── prompts/
        │   ├── system_prompt.txt
        │   └── user_prompt.txt
        └── outputs/
            └── response.txt  ← 최종 답변 저장
```

**UI와 experiments/ 폴더 관계:**
```
UI (session_state)          experiments/ 폴더
==================          =================
사용자 질문 입력     →      ExperimentManager 초기화
Agent 실행           →      도구별 로그 기록
답변 생성            →      프롬프트 저장
UI에 표시            →      outputs/response.txt 저장
```

**차이점:**
- **UI**: 대화형 인터페이스, 휘발성
- **experiments/**: 영구 저장, 재현성 확보

---

### Q6-3. Markdown 다운로드 버튼은 어떻게 구현되나요?

**A:** **Streamlit의 `st.download_button` 사용**합니다.

**코드:**
```python
# file_download.py
def create_download_button(chat_id):
    # 1. Markdown 생성
    markdown_content = export_chat(chat_id)

    # 2. 파일명 생성
    chat = st.session_state.chats[chat_id]
    filename = f"{chat['title'][:20]}.md"

    # 3. 다운로드 버튼
    st.download_button(
        label="💾 Markdown 다운로드",
        data=markdown_content,
        file_name=filename,
        mime="text/markdown"
    )
```

**사용:**
```python
# sidebar.py
for chat in chat_list:
    col1, col2 = st.columns([4, 1])

    with col1:
        st.button(chat['title'], on_click=switch_chat, args=(chat['id'],))

    with col2:
        create_download_button(chat['id'])  # 💾 버튼
```

---

## 7. 트러블슈팅

### Q7-1. Streamlit이 실행되지 않아요

**원인:** Streamlit 미설치 또는 환경변수 미설정

**해결:**
```bash
# Streamlit 설치
pip install streamlit

# 환경변수 설정
export OPENAI_API_KEY="sk-..."
export SOLAR_API_KEY="..."
export DATABASE_URL="postgresql://..."

# 실행
streamlit run ui/app.py
```

**확인:**
```bash
# Streamlit 버전 확인
streamlit --version

# Python 경로 확인
which python
```

---

### Q7-2. 채팅이 저장되지 않아요

**원인:** session_state만 사용 (휘발성)

**해결:**
```python
# 1. 로컬 저장소 활성화
from ui.components.storage import save_chats_to_local_storage

save_chats_to_local_storage()

# 2. Markdown 내보내기
sidebar에서 "💾 저장" 버튼 클릭
```

**자동 저장 설정:**
```python
# app.py
if st.button("💾 모든 채팅 저장"):
    save_chats_to_local_storage()
    st.success("채팅이 저장되었습니다!")
```

---

### Q7-3. Agent 응답이 느려요

**원인:**
1. LLM API 응답 지연
2. DB 검색 시간
3. MultiQuery 사용

**해결:**

**1. 난이도를 Easy로 변경 (Solar Pro2 사용)**
```
Easy 모드: Solar Pro2 (빠름)
Hard 모드: GPT-5 (느림)
```

**2. 캐싱 활용**
```python
@st.cache_resource
def get_agent():
    return initialize_agent()

agent = get_agent()  # 캐싱됨
```

**3. 로딩 메시지 표시**
```python
with st.spinner("답변 생성 중... (최대 30초 소요)"):
    result = agent_executor.invoke(...)
```

---

### Q7-4. 메시지가 중복으로 표시돼요

**원인:** Streamlit 재실행 로직

**해결:**
```python
# 메시지 표시 전에 중복 체크
if "last_message_id" not in st.session_state:
    st.session_state.last_message_id = None

current_message_id = hash(message["content"])

if current_message_id != st.session_state.last_message_id:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

    st.session_state.last_message_id = current_message_id
```

---

## 8. 고급 활용

### Q8-1. 다크 모드 구현 방법은?

**A:** **CSS Injection으로 구현**합니다.

**코드:**
```python
# sidebar.py
dark_mode = st.toggle("🌙 다크 모드", value=False)

if dark_mode:
    st.markdown("""
    <style>
    :root {
        --background-color: #0E1117;
        --secondary-background-color: #262730;
        --text-color: #FAFAFA;
    }

    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }

    .stChatMessage {
        background-color: var(--secondary-background-color);
    }
    </style>
    """, unsafe_allow_html=True)
```

---

### Q8-2. 채팅 검색 기능 추가 방법은?

**A:**

```python
# sidebar.py
search_query = st.text_input("🔍 채팅 검색")

if search_query:
    # 채팅 제목 검색
    filtered_chats = [
        chat for chat in get_chat_list()
        if search_query.lower() in chat['title'].lower()
    ]

    # 검색 결과 표시
    for chat in filtered_chats:
        st.button(chat['title'], on_click=switch_chat, args=(chat['id'],))
```

---

### Q8-3. 채팅 통계 대시보드 구현 방법은?

**A:**

```python
# sidebar.py
with st.expander("📊 통계"):
    total_chats = len(st.session_state.chats)
    total_messages = sum(
        len(chat['messages'])
        for chat in st.session_state.chats.values()
    )

    easy_count = sum(
        1 for chat in st.session_state.chats.values()
        if chat['difficulty'] == 'easy'
    )

    hard_count = total_chats - easy_count

    st.metric("총 채팅 수", total_chats)
    st.metric("총 메시지 수", total_messages)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Easy 모드", easy_count)
    with col2:
        st.metric("Hard 모드", hard_count)
```

---

## 참고 자료

### 관련 문서
- [14_Streamlit_UI_시스템.md](../modularization/14_Streamlit_UI_시스템.md)
- [06_AI_Agent_시스템.md](../modularization/06_AI_Agent_시스템.md)

### 구현 파일
- `ui/app.py` - 메인 애플리케이션
- `ui/components/sidebar.py` - 사이드바
- `ui/components/chat_interface.py` - 채팅 UI
- `ui/components/chat_manager.py` - 채팅 관리

### 외부 자료
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Streamlit Chat Elements](https://docs.streamlit.io/library/api-reference/chat)

---

## 작성자
- **최현화[팀장]** (Streamlit UI 시스템 구현 및 문서화)
