# 전문가 모드 테스트 질문 (20개)

## 📌 개요
- **난이도**: 전문가 (Hard)
- **총 질문 수**: 20개
- **구성**: 단일요청 11개 + 다중요청 7개 + 멀티턴 2세트
- **사용 도구**: 7가지 전체 (general, search_paper, glossary, web_search, summarize, text2sql, save_file)

---

## 🎯 단일요청 질문 (11개)

### 1. general (일반 답변) - 3개

**Q1. Self-Attention의 시간 복잡도는?**
- 예상 도구: `general`
- 목적: 알고리즘 복잡도 분석

**Q2. Transformer가 RNN보다 나은 이유를 기술적으로 설명해줘**
- 예상 도구: `general`
- 목적: 구조 비교 분석

**Q3. Gradient Vanishing 문제와 해결책을 알려줘**
- 예상 도구: `general`
- 목적: 기술적 문제 해결 설명

---

### 2. search_paper (논문 검색) - 4개

**Q4. LoRA Fine-tuning 기법 논문 찾아줘**
- 예상 도구: `search_paper`
- 목적: 특정 기법 논문 검색

**Q5. Multimodal Learning 최신 연구 논문 검색해줘**
- 예상 도구: `search_paper`
- 목적: 연구 분야 논문 검색

**Q6. Chain-of-Thought prompting 논문 있어?**
- 예상 도구: `search_paper`
- 목적: 프롬프팅 기법 논문

**Q7. Constitutional AI 관련 논문 찾아줘**
- 예상 도구: `search_paper`
- 목적: AI 윤리 관련 논문

---

### 3. glossary (용어집) - 2개

**Q8. Zero-shot Learning의 정의를 알려줘**
- 예상 도구: `glossary`
- 목적: 전문 용어 정의

**Q9. Mixture of Experts란?**
- 예상 도구: `glossary`
- 목적: 아키텍처 용어 조회

---

### 4. text2sql (통계 조회) - 3개

**Q10. 2022년 이후 Attention 메커니즘 관련 논문을 연도별로 보여줘**
- 예상 도구: `text2sql`
- 목적: WHERE 절 AND/OR 정확성 검증

**Q11. 카테고리별 논문 수 통계 보여줘**
- 예상 도구: `text2sql`
- 목적: GROUP BY 쿼리

**Q12. 2024년 인용 수 상위 10개 논문 제목 알려줘**
- 예상 도구: `text2sql`
- 목적: ORDER BY + LIMIT 쿼리

---

### 5. summarize (논문 요약) - 1개

**Q13. "BERT: Pre-training of Deep Bidirectional Transformers" 논문 요약해줘**
- 예상 도구: `summarize`
- 목적: 긴 제목 논문 요약

---

### 6. web_search (웹 검색) - 1개

**Q14. 2025년 NeurIPS 컨퍼런스 소식 찾아줘**
- 예상 도구: `web_search`
- 목적: 최신 학회 정보

---

## 🔄 다중요청 질문 (7개)

### 7. search_paper → summarize → save_file (3-tool)

**Q15. BERT와 GPT 논문 비교해서 분석하고 저장해줘**
- 예상 도구: `search_paper` → `summarize` → `general` → `save_file`
- 목적: 복잡한 파이프라인 + Fallback 검증
- **중요**: search_paper 실패 시 web_search로 자동 대체 확인

---

### 8. glossary → search_paper → summarize (3-tool)

**Q16. Diffusion Model 설명하고 관련 논문 찾아서 요약해줘**
- 예상 도구: `glossary` → `search_paper` → `summarize`
- 목적: 3단계 파이프라인

---

### 9. text2sql → search_paper → summarize (3-tool)

**Q17. 2024년 BERT 계열 논문 통계 보여주고 대표 논문 하나 요약해줘**
- 예상 도구: `text2sql` → `search_paper` → `summarize`
- 목적: 통계 → 검색 → 요약 워크플로우

---

### 10. web_search → summarize → save_file (3-tool)

**Q18. 최신 LLM 트렌드 찾아서 정리하고 저장해줘**
- 예상 도구: `web_search` → `summarize` → `save_file`
- 목적: 웹 검색 → 정리 → 저장

---

### 11. search_paper → general (비교 분석)

**Q19. Supervised Learning과 Unsupervised Learning 차이를 논문 기반으로 설명해줘**
- 예상 도구: `search_paper` → `general`
- 목적: 논문 검색 후 비교 분석

---

### 12. glossary → search_paper

**Q20. Retrieval Augmented Generation 설명하고 관련 논문도 찾아줘**
- 예상 도구: `glossary` → `search_paper`
- 목적: 정의 후 논문 검색

---

### 13. text2sql → save_file

**Q21. Transformer 관련 논문 통계를 SQL로 조회하고 결과 저장해줘**
- 예상 도구: `text2sql` → `save_file`
- 목적: 통계 조회 후 파일 저장

---

## 💬 멀티턴 대화 (멀티턴은 위 21개에서 제외, 별도 테스트)

### 멀티턴 세트 1 (추가 테스트)

**MT1-1. "Attention Is All You Need" 논문 요약해줘**
- 예상 도구: `summarize`

**MT1-2. 이 논문의 한계점은 뭐야?**
- 예상 도구: `general` (이전 문맥 활용)

**MT1-3. 개선한 후속 연구 있어?**
- 예상 도구: `search_paper` (이전 문맥 활용)

---

## 📊 도구 사용 분포

| 도구 | 단일 | 다중 | 총계 |
|------|------|------|------|
| general | 3 | 2 | 5 |
| glossary | 2 | 2 | 4 |
| search_paper | 4 | 5 | 9 |
| web_search | 1 | 1 | 2 |
| summarize | 1 | 4 | 5 |
| text2sql | 3 | 2 | 5 |
| save_file | 0 | 3 | 3 |

**총 질문 수**: 21개 (단일 14개 + 다중 7개)

---

## ✅ 테스트 체크리스트

### 단일요청 검증
- [ ] Q1-Q3: general 전문적 답변 생성
- [ ] Q4-Q7: search_paper 다양한 주제 검색
- [ ] Q8-Q9: glossary 전문 용어 조회
- [ ] Q10-Q12: text2sql 복잡한 쿼리 실행
- [ ] Q13: summarize 긴 제목 논문 처리
- [ ] Q14: web_search 최신 컨퍼런스 정보

### 다중요청 검증 (핵심)
- [ ] Q15: **search_paper 실패 시 web_search Fallback 작동 확인** (중요!)
- [ ] Q16: glossary → search_paper → summarize 3단계 파이프라인
- [ ] Q17: text2sql → search_paper → summarize 통계 기반 워크플로우
- [ ] Q18: web_search → summarize → save_file 웹 정보 저장
- [ ] Q19: search_paper → general 비교 분석
- [ ] Q20: glossary → search_paper 정의 후 검색
- [ ] Q21: text2sql → save_file 통계 저장

### 특수 검증
- [ ] Q10: SQL WHERE 절 괄호 규칙 적용 확인 (2022년 이후만)
- [ ] Q15: 파이프라인 Fallback 로직 정상 작동
- [ ] Q18, Q21: save_file 파일명 형식 확인 (날짜_시간_질문.md)
- [ ] save_file: outputs/save_data/ 폴더에 저장 확인

### 멀티턴 검증 (별도)
- [ ] MT1-1~MT1-3: 이전 대화 컨텍스트 유지

### 에러 처리 검증
- [ ] Router JSON 파싱 정상 (마크다운 코드 펜스 제거)
- [ ] 유효하지 않은 도구명 general로 폴백
- [ ] 도구 실행 실패 시 Fallback 작동

---

**작성일**: 2025-11-05
**버전**: 1.0
