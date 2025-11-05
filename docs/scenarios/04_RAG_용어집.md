# 시나리오: RAG 용어집 (Glossary)

## 📋 도구 설명

**도구명**: `glossary`
**목적**: PostgreSQL glossary 테이블에서 AI/ML 용어 정의 검색

### 주요 기능
- 용어집 데이터베이스 검색
- 난이도별 설명 제공 (Easy/Hard)
- 빠른 용어 정의 조회
- 자동으로 수집된 용어 활용

---

## 🎯 사용 시나리오

### 시나리오 1: 용어 정의 요청

**사용자 상황**: 논문에서 처음 보는 용어를 이해하고 싶음

**사용자 질문**:
```
"Attention Mechanism이 뭐야?"
```

**Agent 동작**:
1. Router가 용어 질문으로 판단
2. `glossary` 도구 선택
3. LLM이 질문에서 "Attention Mechanism" 추출
4. glossary 테이블 검색: `SELECT * FROM glossary WHERE term ILIKE '%Attention Mechanism%'`
5. 난이도에 맞는 설명 반환

**DB 검색 쿼리** (database/queries.sql):
```sql
-- 실행 시간: 2024-11-03 10:30:15
-- 도구: rag_glossary
-- 설명: 용어집 검색

SELECT term, definition, easy_explanation, hard_explanation, category
FROM glossary
WHERE term ILIKE '%Attention Mechanism%';
```

**예상 답변** (Easy 모드):
```
**용어**: Attention Mechanism

**카테고리**: Deep Learning

**설명**:
Attention Mechanism은 신경망이 입력 데이터의 중요한 부분에 집중할 수 있게 하는 기법입니다.

🔍 쉬운 비유:
책을 읽을 때 중요한 문장에 형광펜을 긋는 것과 비슷합니다. 모든 단어를 똑같이 보지 않고,
중요한 부분에 더 많은 "주의"를 기울입니다.

📝 예시:
번역에서 "I love you"를 "나는 너를 사랑해"로 번역할 때:
- "love" 번역 시 → "사랑해"에 집중
- "you" 번역 시 → "너를"에 집중

💡 왜 중요한가:
- 긴 문장도 정확하게 번역
- Transformer의 핵심 기술
- GPT, BERT 등 최신 AI의 기반
```

**예상 답변** (Hard 모드):
```
**용어**: Attention Mechanism

**카테고리**: Deep Learning

**설명**:
Attention Mechanism은 시퀀스 모델링에서 입력의 각 위치에 대한 가중 합(weighted sum)을
계산하여 중요한 정보를 선택적으로 활용하는 기법입니다.

📐 수학적 정의:
Attention(Q, K, V) = softmax(QK^T / √d_k)V

where:
- Q (Query): 현재 위치의 쿼리 벡터
- K (Key): 모든 위치의 키 벡터
- V (Value): 모든 위치의 값 벡터
- d_k: 키 벡터의 차원

🔬 주요 변형:
1. Self-Attention: Q, K, V 모두 같은 입력
2. Multi-Head Attention: 여러 Attention을 병렬로 학습
3. Cross-Attention: Encoder-Decoder 간 Attention

⚙️ 계산 복잡도:
- 시간: O(n²d) where n은 시퀀스 길이, d는 임베딩 차원
- 공간: O(n²)

📊 응용:
- NMT (Neural Machine Translation)
- Vision Transformer
- BERT, GPT 등 모든 Transformer 기반 모델
```

---

### 시나리오 2: 약어 설명

**사용자 질문**:
```
"BLEU Score가 뭐야?"
```

**Agent 동작**:
1. `glossary` 도구 선택
2. "BLEU Score" 검색
3. 용어집에서 정의 반환

**예상 답변**:
```
**용어**: BLEU Score

**카테고리**: Metric

**설명**:
BLEU (Bilingual Evaluation Understudy)는 기계 번역의 품질을 평가하는 지표입니다.

📊 평가 방법:
- 생성된 번역과 참조 번역 비교
- n-gram 매칭 비율 계산
- 0 (최악) ~ 1 (완벽) 점수

💯 점수 해석:
- 0.5 이상: 양호한 번역
- 0.3 ~ 0.5: 보통
- 0.3 미만: 개선 필요

⚠️ 한계:
- 문법적 정확성 미평가
- 의미적 유사성 부족
- 다양한 올바른 번역 중 하나만 인정
```

---

### 시나리오 3: 비교 질문 (용어 위주)

**사용자 질문**:
```
"Fine-tuning이 뭐야?"
```

**Agent 동작**:
1. `glossary` 도구 선택
2. "Fine-tuning" 검색
3. Transfer Learning 맥락에서 설명

**예상 답변**:
```
**용어**: Fine-tuning

**카테고리**: Transfer Learning

**설명**:
사전 학습된 모델을 특정 작업에 맞게 추가로 학습시키는 기법입니다.

🔄 과정:
1. 사전 학습: 대규모 데이터로 기본 모델 학습 (예: ImageNet)
2. Fine-tuning: 목표 작업의 작은 데이터로 미세 조정

💡 장점:
- 적은 데이터로 높은 성능
- 학습 시간 단축
- 과적합 방지

📝 예시:
GPT-3 (일반 언어 모델) → ChatGPT (대화 특화)
- 사전 학습: 인터넷 텍스트
- Fine-tuning: 대화 데이터

🎯 활용 분야:
- 이미지 분류
- 감정 분석
- 챗봇 개발
```

---

## 📊 성능 지표

- **응답 속도**: 매우 빠름 (단순 DB 조회)
- **정확도**: 높음 (검증된 용어집)
- **커버리지**: 자동 수집으로 지속 확장

---

## 🔧 내부 구현

### 용어 추출 + 검색
```python
# 1. LLM으로 질문에서 용어 추출
extract_prompt = f"다음 질문에서 핵심 용어를 추출하세요: {question}"
term = llm.invoke(extract_prompt)

# 2. glossary 테이블 검색
query = "SELECT * FROM glossary WHERE term ILIKE %s"
cursor.execute(query, (f"%{term}%",))
result = cursor.fetchone()

# 3. 난이도별 설명 선택
if difficulty == "easy":
    explanation = result["easy_explanation"]
else:
    explanation = result["hard_explanation"]
```

### 로깅
- **tools/rag_glossary.log**: 용어 추출 및 검색 과정
- **database/queries.sql**: 실행된 SQL 쿼리

---

## ⚠️ 제한사항

1. **용어집 의존**: DB에 없는 용어는 검색 불가
2. **약어 문제**: 동일 약어의 다른 의미 구분 어려움
3. **업데이트**: 자동 수집되지만 즉시 반영 안 됨

---

## 🔄 다른 도구로의 전환

| 상황 | 추천 도구 |
|------|----------|
| 용어집에 없을 때 | `general` (LLM 지식 활용) |
| 용어 관련 논문 필요 | `search_paper` |
| 최신 용어 검색 | `web_search` |

---

## 💡 활용 팁

1. **정확한 용어**: 약어보다 전체 이름 사용 (예: "NMT" → "Neural Machine Translation")
2. **단일 용어**: 한 번에 하나의 용어만 질문
3. **난이도 활용**: Easy/Hard 모드로 학습 수준에 맞는 설명 확인

---

## 📈 자동 수집 기능

챗봇 답변에서 자동으로 용어 추출 및 저장:
```
✅ 3개 용어가 용어집에 추가되었습니다!
```

- LLM이 답변에서 AI/ML 용어 감지
- 정의와 카테고리 자동 생성
- glossary 테이블에 저장 (중복 방지)

---

## 📈 예상 질문 리스트

### 단일요청 (5개)
1. Transformer 모델이란?
2. Gradient Descent의 원리를 쉽게 설명해줘
3. Reinforcement Learning이란 무엇이며, 어떻게 작동해?
4. GAN(Generative Adversarial Network)의 기본 개념 설명해줘
5. ViT의 구조를 간단히 설명해줘

### 다중요청 (다른 도구와 결합)
- `glossary` → `search_paper`: Attention Mechanism과 Feed Forward Network 구조의 차이를 설명하고, 관련 논문을 함께 보여줘

---

**작성일**: 2025-11-05
**버전**: 2.0
