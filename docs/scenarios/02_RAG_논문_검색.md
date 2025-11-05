# 시나리오: RAG 논문 검색 (Search Paper)

## 📋 도구 설명

**도구명**: `search_paper`
**목적**: PostgreSQL + pgvector를 활용한 논문 데이터베이스 검색 및 RAG 기반 답변 생성

### 주요 기능
- 임베딩 기반 유사도 검색 (pgvector)
- Top-5 관련 논문 자동 검색
- 검색된 논문을 컨텍스트로 활용한 답변 생성
- 논문 메타데이터 (제목, 저자, 연도) 제공

---

## 🎯 사용 시나리오

### 시나리오 1: 특정 기술 논문 검색

**사용자 상황**: Transformer 아키텍처에 대한 논문 정보가 필요함

**사용자 질문**:
```
"Transformer 논문에 대해 알려줘"
```

**Agent 동작**:
1. Router가 질문 분석
2. 논문 관련 질문으로 판단
3. `search_paper` 도구 선택
4. Vector DB에서 "Transformer" 관련 논문 검색 (Top-5)
5. PostgreSQL에서 논문 메타데이터 조회
6. 검색된 논문을 컨텍스트로 LLM 답변 생성

**실행 로그** (experiments/날짜/실행폴더/tools/rag_paper.log):
```
RAG 검색 노드 실행: Transformer 논문에 대해 알려줘
난이도: easy
Vector DB 초기화 완료
Vector DB 유사도 검색 시작 (Top-5)
검색된 문서 수: 5
SQL 쿼리 실행: paper_id IN [12, 45, 78, 123, 156]
조회된 논문 메타데이터 수: 5
LLM 답변 생성 시작
답변 생성 완료: 1247 글자
```

**예상 답변** (Easy 모드):
```
Transformer는 2017년 Google이 발표한 혁신적인 딥러닝 아키텍처입니다.

핵심 특징:
1. **어텐션 메커니즘**: 입력의 중요한 부분에 집중
2. **병렬 처리**: RNN과 달리 순차 처리가 필요 없어 빠름
3. **장거리 의존성**: 멀리 떨어진 단어 간의 관계도 잘 파악

주요 응용 분야:
- 기계 번역 (영어 → 한국어)
- GPT 시리즈 (ChatGPT의 기반)
- BERT (검색 엔진 개선)

Transformer 덕분에 최근 AI 기술이 비약적으로 발전했습니다!

📚 참고 논문:
- **Attention Is All You Need** (Vaswani et al., 2017)
- **BERT: Pre-training of Deep Bidirectional Transformers** (Devlin et al., 2018)
- **GPT-3: Language Models are Few-Shot Learners** (Brown et al., 2020)
```

**UI 표시**:
- 🗣️ 사용된 도구: **📚 RAG 논문 검색**
- 📚 참고 논문 (Expander):
  ```
  제목: Attention Is All You Need
  저자: Vaswani, Ashish; Shazeer, Noam; Parmar, Niki; ...
  연도: 2017
  ---
  제목: BERT: Pre-training of Deep Bidirectional Transformers
  저자: Devlin, Jacob; Chang, Ming-Wei; Lee, Kenton; ...
  연도: 2018
  ...
  ```

---

### 시나리오 2: 특정 문제 해결 방법 검색

**사용자 질문**:
```
"Few-shot learning을 어떻게 개선할 수 있을까?"
```

**Agent 동작**:
1. `search_paper` 도구 선택
2. "Few-shot learning improvement" 관련 논문 검색
3. 검색된 논문의 방법론을 컨텍스트로 활용
4. 실용적인 개선 방법 제시

**예상 답변** (Hard 모드):
```
Few-shot learning 성능 개선을 위한 주요 접근법:

1. **메타 학습 (Meta-Learning)**:
   - MAML (Model-Agnostic Meta-Learning): 빠른 적응을 위한 초기화 학습
   - Prototypical Networks: 클래스별 프로토타입 임베딩 학습
   - 수식: θ* = θ - α∇L(θ)

2. **데이터 증강 (Data Augmentation)**:
   - MixUp: 샘플 간 선형 보간
   - CutMix: 영역 기반 혼합
   - AutoAugment: 자동 증강 정책 학습

3. **전이 학습 강화**:
   - 대규모 사전 학습 모델 활용 (CLIP, GPT-5)
   - Task-specific fine-tuning

4. **관계 네트워크**:
   - 샘플 간 유사도 학습
   - 거리 기반 분류 (Siamese Networks)

📊 성능 비교 (논문 기준):
- Baseline: 45.3% accuracy
- MAML: 68.7% accuracy
- Prototypical Networks: 71.2% accuracy

📚 참고 논문:
- Model-Agnostic Meta-Learning (Finn et al., 2017)
- Prototypical Networks for Few-shot Learning (Snell et al., 2017)
- Meta-Learning with Differentiable Convex Optimization (Lee et al., 2019)
```

---

### 시나리오 3: 최신 연구 동향 파악

**사용자 질문**:
```
"Vision Transformer의 최신 연구는 어떤 게 있어?"
```

**Agent 동작**:
1. `search_paper` 도구 선택
2. "Vision Transformer" 관련 최신 논문 검색
3. 논문 DB에서 publish_date 기준 정렬
4. 연구 동향 요약

**예상 답변**:
```
Vision Transformer (ViT) 분야의 최신 연구 동향:

1. **효율성 개선**:
   - DeiT (Data-efficient Image Transformers): 적은 데이터로 학습
   - Swin Transformer: 계층적 구조로 연산량 감소
   - MobileViT: 모바일 기기에서도 실행 가능

2. **성능 향상**:
   - BEiT: BERT 스타일의 이미지 사전 학습
   - MAE (Masked Autoencoders): 마스킹 기반 자기지도학습
   - 정확도: ImageNet top-1 87.8% 달성

3. **응용 분야 확장**:
   - 의료 영상 분석
   - 자율 주행 객체 인식
   - 비디오 이해 (Video Transformer)

📚 참고 논문:
- An Image is Worth 16x16 Words: Transformers for Image Recognition (Dosovitskiy et al., 2020)
- Swin Transformer: Hierarchical Vision Transformer (Liu et al., 2021)
- Masked Autoencoders Are Scalable Vision Learners (He et al., 2021)
```

---

## 📊 성능 지표

- **검색 정확도**: pgvector 임베딩 유사도 기반
- **응답 속도**: 중간 (Vector 검색 + DB 조회 + LLM)
- **출처 신뢰성**: 높음 (실제 논문 기반)

---

## 🔧 내부 구현

### Vector 검색 과정
```python
# 1. 임베딩 생성
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 2. pgvector 유사도 검색
docs = vectorstore.similarity_search(question, k=5)

# 3. 논문 메타데이터 조회
SELECT paper_id, title, authors, publish_date
FROM papers
WHERE paper_id IN (...)
```

### 로깅
- **tools/rag_paper.log**: 검색 과정 전체 로그
- **database/queries.sql**: 실행된 SQL 쿼리
- **database/pgvector_searches.json**: Vector 검색 기록
- **prompts/system_prompt.txt**: 난이도별 시스템 프롬프트
- **prompts/user_prompt.txt**: 컨텍스트 포함 사용자 프롬프트

---

## ⚠️ 제한사항

1. **DB 의존성**: 논문이 DB에 없으면 검색 불가
2. **최신성**: DB 업데이트 주기에 따라 최신 논문 부족 가능
3. **언어 제약**: 주로 영문 논문 (한글 논문 적음)

---

## 🔄 다른 도구로의 전환

| 상황 | 추천 도구 |
|------|----------|
| DB에 논문이 없을 때 | `web_search` (최신 논문 검색) |
| 용어 정의가 필요할 때 | `glossary` (용어집 검색) |
| 논문 전문 요약 필요 | `summarize` (논문 요약) |

---

## 💡 활용 팁

1. **구체적 질문**: "Transformer"보다 "Transformer의 attention mechanism"이 더 정확
2. **키워드 활용**: 논문 제목이나 저자명 포함하면 검색 정확도 향상
3. **난이도 설정**: Hard 모드에서 더 기술적이고 상세한 설명 제공

---

## 📈 예상 질문 리스트

### 단일요청 (4개)
1. BERT 모델의 구조와 주요 개선점을 다룬 논문이 있을까?
2. Few-shot learning을 개선한 연구는 어떤게 있어?
3. LLM의 효율적인 Fine-tuning 기법 논문 찾아줘
4. 최근 Transformer 기반 음성인식 논문이 있을까?

### 다중요청 (다른 도구와 결합)
- `search_paper` → `summarize`: Transformer 논문들에 대해 정리해서 쉽게 설명해줘
- `search_paper` → `save_file`: 한국 연구자가 참여한 LLM 관련 논문이 있는지 찾아서 알려줘
- `text2sql` → `search_paper`: 2025년에 나온 ViT모델 성능에 관한 논문 찾아서 보여줘

---

**작성일**: 2025-11-05
**버전**: 2.0
