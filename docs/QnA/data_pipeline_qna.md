# 데이터 파이프라인 Q&A

## 문서 정보
- **작성일**: 2025-11-05
- **작성자**: 최현화[팀장]
- **목적**: 데이터 파이프라인(`scripts/data/run_full_pipeline.py`) 관련 초보자 질문 및 답변

---

## 목차
1. [기본 개념](#1-기본-개념)
2. [청킹(Chunking)](#2-청킹chunking)
3. [임베딩 생성](#3-임베딩-생성)
4. [PGVector 저장소](#4-pgvector-저장소)
5. [파이프라인 단계](#5-파이프라인-단계)
6. [트러블슈팅](#6-트러블슈팅)
7. [고급 주제](#7-고급-주제)

---

## 1. 기본 개념

### Q1-1. 데이터 파이프라인이 무엇인가요?

**A:** **PDF 논문을 RAG 시스템이 사용할 수 있는 형태로 변환하는 전체 과정**입니다.

**전체 흐름:**
```
arXiv 논문 (PDF)
    ↓
[Phase 1] PDF 다운로드
    ↓
[Phase 2] Papers 테이블에 메타데이터 저장
    ↓
[Phase 3] PDF → 텍스트 추출 → 청크 분할
    ↓
[Phase 4] 청크 → 임베딩 생성 → PGVector 저장
    ↓
RAG 시스템에서 검색 가능
```

**파이프라인 스크립트:**
- **메인 스크립트**: `scripts/data/run_full_pipeline.py`
- **실행 명령**: `python scripts/data/run_full_pipeline.py`
- **소요 시간**: 논문 20개 기준 약 5-10분

---

### Q1-2. 왜 PDF를 그대로 사용하지 않나요?

**A:** PDF는 **LLM이 직접 읽을 수 없고, 검색도 불가능**하기 때문입니다.

**문제점:**

| 항목 | PDF 원본 | 처리된 청크 + 임베딩 |
|------|---------|-------------------|
| **크기** | 수 MB | 수 KB (청크당) |
| **LLM 입력** | ❌ 불가 (바이너리) | ✅ 가능 (텍스트) |
| **의미 검색** | ❌ 불가 | ✅ 가능 (벡터) |
| **부분 검색** | ❌ 전체만 가능 | ✅ 관련 부분만 추출 |
| **컨텍스트 크기** | 수만 토큰 (초과) | 수천 토큰 (적합) |

**예시:**
```
원본 PDF: 10페이지, 50,000토큰
  → LLM 컨텍스트 초과 (GPT-4: 128K 토큰)
  → 전체를 한 번에 처리 불가

청크로 분할: 50개 청크, 각 1,000토큰
  → 유사도 검색으로 Top-5 청크만 선택
  → 5,000토큰만 LLM에 전달
  → 정확한 답변 가능
```

---

### Q1-3. 데이터 파이프라인을 언제 실행하나요?

**A:** 다음 상황에서 실행합니다:

**필수 실행 시점:**
1. ✅ **프로젝트 초기 설정**: 처음 RAG 시스템을 구축할 때
2. ✅ **논문 추가**: 새로운 논문을 추가하고 싶을 때
3. ✅ **데이터 삭제 후**: Papers 테이블이나 PGVector 데이터를 삭제한 후

**재실행이 필요한 경우:**
1. ⚠️ **청크 중복 문제**: 동일한 내용의 청크가 여러 개 발견될 때
2. ⚠️ **검색 품질 저하**: 특정 논문이 검색되지 않을 때
3. ⚠️ **스키마 변경**: chunk_index 같은 메타데이터 필드를 추가했을 때

**재실행하지 않아도 되는 경우:**
- ❌ 코드 수정만 했을 때 (UI, Agent 로직 등)
- ❌ LLM 모델만 변경했을 때
- ❌ Glossary나 Query Logs만 수정했을 때

---

## 2. 청킹(Chunking)

### Q2-1. 청킹이 무엇인가요?

**A:** **긴 문서를 작은 단위로 나누는 과정**입니다.

**왜 필요한가요?**

1. **LLM 컨텍스트 제한**: LLM은 한 번에 처리할 수 있는 토큰 수가 제한되어 있습니다.
   ```
   GPT-4-turbo: 128K 토큰
   논문 1개: 평균 50K 토큰
   논문 100개: 5,000K 토큰 ❌ (초과)
   ```

2. **관련 정보만 추출**: 질문과 관련된 부분만 찾아서 LLM에 전달합니다.
   ```
   질문: "Transformer의 Attention 메커니즘은?"

   [청킹 없이]
   논문 전체 50K 토큰 → LLM
   - 대부분 불필요한 내용 (서론, 실험, 참고문헌 등)

   [청킹 사용]
   "Attention 메커니즘" 설명 청크 5개 (5K 토큰) → LLM
   - 질문과 직접 관련된 내용만
   ```

3. **검색 정확도 향상**: 작은 청크일수록 특정 주제에 집중되어 검색이 정확합니다.
   ```
   [청크 크기 10,000자 (큼)]
   서론 + Attention + 실험 + 결론 섞여있음
   → "Attention" 검색 시 노이즈 많음

   [청크 크기 1,000자 (작음)]
   Attention 메커니즘만 집중 설명
   → "Attention" 검색 시 정확히 매칭
   ```

---

### Q2-2. 청크 크기는 어떻게 정하나요?

**A:** 우리 프로젝트에서는 **chunk_size=1000, chunk_overlap=200**을 사용합니다.

**설정 위치:**
```python
# src/data/document_loader.py
class PaperDocumentLoader:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,      # 청크 최대 크기
            chunk_overlap=chunk_overlap, # 청크 간 겹침
        )
```

**설정 값 의미:**

| 설정 | 값 | 의미 |
|-----|-----|-----|
| **chunk_size** | 1000 | 각 청크의 최대 문자 수 |
| **chunk_overlap** | 200 | 인접 청크 간 겹치는 문자 수 |

**예시:**
```
원본 텍스트: "Transformer는 ... [2000자] ... Attention은 ..."

[청크 1] (0-1000자)
"Transformer는 ... 인코더는 ..."

[청크 2] (800-1800자)  ← 200자 겹침 (800-1000)
"... 인코더는 ... Attention은 ..."
```

**왜 겹치나요?**
- 문맥 유지: 청크 경계에서 문장이 잘려도 이전 내용 참조 가능
- 검색 누락 방지: 중요한 문장이 청크 경계에 있어도 다른 청크에서 검색됨

**적절한 크기 선택:**

| 크기 | 장점 | 단점 | 적합한 경우 |
|-----|------|------|----------|
| **작음 (500)** | 정확한 매칭 | 문맥 부족, 청크 수 많음 | 짧은 FAQ, 용어집 |
| **중간 (1000)** | 균형 잡힘 | - | **논문 (권장)** |
| **큼 (2000)** | 문맥 풍부 | 노이즈 많음, 검색 부정확 | 긴 기술 문서 |

---

### Q2-3. 청크는 어떻게 나뉘나요?

**A:** **RecursiveCharacterTextSplitter**가 우선순위에 따라 분할합니다.

**분할 우선순위:**
```python
separators = [
    "\n\n",  # 1순위: 문단 (가장 선호)
    "\n",    # 2순위: 줄바꿈
    ". ",    # 3순위: 문장
    " ",     # 4순위: 단어
    ""       # 5순위: 글자 (최후)
]
```

**동작 예시:**
```
원본 (1500자):
"""
Transformer는 2017년 발표된 모델입니다.

Self-Attention은 입력 시퀀스의 모든 위치를 참고합니다.
이를 통해 장거리 의존성을 효과적으로 학습합니다.

실험 결과 BLEU 점수가 향상되었습니다.
"""

↓ chunk_size=1000, chunk_overlap=200

[청크 1] (0-1000자)
"""
Transformer는 2017년 발표된 모델입니다.

Self-Attention은 입력 시퀀스의 모든 위치를 참고합니다.
이를 통해 장거리 의존성을 효과적으로 학습합니다.
"""
→ 문단("\n\n") 기준으로 깔끔하게 분할

[청크 2] (800-1500자)  ← 200자 겹침
"""
이를 통해 장거리 의존성을 효과적으로 학습합니다.

실험 결과 BLEU 점수가 향상되었습니다.
"""
```

**문단 경계가 없다면?**
```
긴 문단 (2000자, 줄바꿈 없음):
"Transformer는... [2000자 한 문단]"

↓ 문단 분할 불가 → 줄바꿈("\n") 시도
↓ 줄바꿈도 없음 → 문장(". ") 시도
↓ 적절한 문장 찾아서 분할

[청크 1] "Transformer는... 모델입니다."  ← 문장 끝에서 분할
[청크 2] "Self-Attention은... 학습합니다."
```

---

### Q2-4. 청크 메타데이터는 무엇인가요?

**A:** **각 청크에 추가되는 정보**로, 검색과 추적에 사용됩니다.

**우리 프로젝트의 청크 메타데이터:**
```python
chunk.metadata = {
    # 논문 메타데이터 (Papers 테이블에서 가져옴)
    "paper_id": 1,                           # Papers 테이블 FK
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", ...],
    "arxiv_id": "1706.03762",
    "entry_id": "http://arxiv.org/abs/1706.03762v7",
    "published": "2017-06-12",

    # 청크 메타데이터 (document_loader.py에서 추가)
    "chunk_id": 5,                           # 청크 고유 ID
    "chunk_index": 5,                        # 청크 순서 (검색용)

    # PDF 메타데이터 (PyPDFLoader에서 추가)
    "page": 3,                               # 원본 PDF 페이지 번호
    "source": "/path/to/1706.03762.pdf",     # PDF 파일 경로
}
```

**메타데이터 활용:**

1. **필터링**: 특정 논문의 청크만 검색
   ```python
   # paper_id=1의 청크만 검색
   results = vectorstore.similarity_search(
       "Attention 메커니즘",
       filter={"paper_id": 1}
   )
   ```

2. **추적**: 검색 결과가 어느 논문의 어느 부분인지 파악
   ```python
   for doc in results:
       print(f"논문: {doc.metadata['title']}")
       print(f"페이지: {doc.metadata['page']}")
       print(f"청크 순서: {doc.metadata['chunk_index']}")
   ```

3. **정렬**: 청크 순서대로 정렬하여 문맥 재구성
   ```python
   # chunk_index 순서대로 정렬
   sorted_chunks = sorted(results, key=lambda x: x.metadata['chunk_index'])
   ```

---

## 3. 임베딩 생성

### Q3-1. 임베딩이 무엇인가요?

**A:** **텍스트를 의미를 담은 숫자 벡터로 변환하는 과정**입니다.

**개념:**
```
텍스트 (인간이 읽음)
"Transformer uses self-attention"

    ↓ 임베딩 모델 (OpenAI text-embedding-3-small)

벡터 (컴퓨터가 계산)
[0.123, -0.456, 0.789, ..., 0.234]  ← 1536개 숫자
```

**왜 필요한가요?**
- 의미 유사도 계산 가능
- 키워드 매칭보다 정확

**예시:**
```
[키워드 매칭]
질문: "주의 메커니즘"
청크: "Attention mechanism"
→ 매칭 실패 ❌ (단어가 다름)

[임베딩 유사도]
질문: "주의 메커니즘" → [0.1, 0.9, ...]
청크: "Attention mechanism" → [0.12, 0.88, ...]
→ 벡터 거리 0.05 (매우 유사) ✅
```

---

### Q3-2. 어떤 임베딩 모델을 사용하나요?

**A:** **OpenAI의 `text-embedding-3-small`** 모델을 사용합니다.

**설정 위치:**
```python
# src/database/embeddings.py
from langchain_openai import OpenAIEmbeddings

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

def get_embeddings(model: Optional[str] = None) -> OpenAIEmbeddings:
    model_name = model or DEFAULT_EMBEDDING_MODEL
    return OpenAIEmbeddings(model=model_name)
```

**사용:**
```python
# src/database/vector_store.py
from .embeddings import get_embeddings

embeddings = get_embeddings()  # text-embedding-3-small (1536 차원)
```

**모델 비교:**

| 모델 | 차원 | 성능 | 비용 | 속도 |
|-----|------|------|------|------|
| **text-embedding-3-small** | 1536 | 높음 | 낮음 | **빠름 ✅** |
| text-embedding-3-large | 3072 | 매우 높음 | 높음 | 느림 |
| text-embedding-ada-002 | 1536 | 중간 | 낮음 | 빠름 |

**왜 3-small을 선택했나요?**
- ✅ 성능과 비용의 균형
- ✅ 1536 차원으로 충분히 정확
- ✅ 빠른 임베딩 생성 (논문 100개 기준 5-10분)

---

### Q3-3. 임베딩은 언제 생성되나요?

**A:** **Phase 4: `load_embeddings.py` 실행 시** 생성됩니다.

**흐름:**
```
1. 청크 로드
   loader = PaperDocumentLoader()
   chunks = loader.load_all_pdfs(pdf_dir, metadata_path)
   → 5,000개 청크

2. 중복 제거
   chunks = deduplicate_chunks(chunks)
   → 4,500개 청크 (500개 중복 제거)

3. 배치 처리
   batch_size = 50
   for i in range(0, len(chunks), 50):
       batch = chunks[i:i+50]

4. 임베딩 생성 + PGVector 저장
       vectorstore.add_documents(batch)
       → OpenAI API 호출 (50개 청크 임베딩 생성)
       → PostgreSQL에 저장

       time.sleep(0.1)  # Rate Limit 방지
```

**소요 시간:**
```
청크 1개: 약 0.1초
배치 50개: 약 5초
총 4,500개: 약 450초 (7.5분)
```

---

### Q3-4. 임베딩 비용은 얼마나 드나요?

**A:** **논문 20개 기준 약 $0.10-0.20** 정도입니다.

**비용 계산:**
```
모델: text-embedding-3-small
가격: $0.02 / 1M 토큰

논문 1개: 평균 50K 토큰
청크 50개: 각 1K 토큰 = 50K 토큰
논문 20개: 50K × 20 = 1M 토큰

비용: 1M 토큰 × $0.02 = $0.02
```

**Rate Limit:**
- OpenAI 무료 티어: 분당 200 요청, 시간당 1M 토큰
- 배치 크기 50개, sleep 0.1초로 제한 준수

---

## 4. PGVector 저장소

### Q4-1. PGVector 테이블이 2개인데 왜 그런가요?

**A:** **컬렉션 메타데이터와 실제 임베딩을 분리**하기 위함입니다.

**2개 테이블:**

#### 1. `langchain_pg_collection` (컬렉션 테이블)
```sql
CREATE TABLE langchain_pg_collection (
    uuid UUID PRIMARY KEY,           -- 컬렉션 고유 ID
    name VARCHAR,                    -- 컬렉션 이름 (예: "paper_chunks")
    cmetadata JSONB                  -- 컬렉션 메타데이터
);
```

**역할**: 임베딩 데이터의 "폴더" 역할
```
langchain_pg_collection
├── uuid: 550e8400-e29b-41d4-a716-446655440000
├── name: "paper_chunks"           ← 논문 청크 컬렉션
└── cmetadata: {}

├── uuid: 660e8400-e29b-41d4-a716-446655440111
├── name: "glossary_chunks"        ← 용어집 컬렉션
└── cmetadata: {}
```

#### 2. `langchain_pg_embedding` (임베딩 테이블)
```sql
CREATE TABLE langchain_pg_embedding (
    id UUID PRIMARY KEY,             -- 임베딩 고유 ID
    collection_id UUID,              -- FK: langchain_pg_collection.uuid
    document TEXT,                   -- 청크 원본 텍스트
    cmetadata JSONB,                 -- 청크 메타데이터
    embedding VECTOR(1536)           -- 임베딩 벡터 (1536 차원)
);
```

**역할**: 실제 청크와 임베딩 벡터 저장
```
langchain_pg_embedding
├── id: aaa...
├── collection_id: 550e8400-... (paper_chunks 참조)
├── document: "Transformer는 2017년..."
├── cmetadata: {"paper_id": 1, "chunk_index": 0, ...}
└── embedding: [0.123, -0.456, ..., 0.789]

├── id: bbb...
├── collection_id: 550e8400-... (paper_chunks 참조)
├── document: "Self-Attention은..."
├── cmetadata: {"paper_id": 1, "chunk_index": 1, ...}
└── embedding: [0.234, -0.567, ..., 0.890]
```

**관계:**
```
langchain_pg_collection (1개)
    ↓ 1:N
langchain_pg_embedding (4,500개)
```

---

### Q4-2. 컬렉션 이름은 왜 필요한가요?

**A:** **같은 PGVector 데이터베이스에 여러 종류의 데이터를 구분**하기 위함입니다.

**우리 프로젝트의 컬렉션:**

| 컬렉션 이름 | 용도 | 데이터 예시 |
|-----------|------|-----------|
| **paper_chunks** | 논문 청크 | "Transformer는... Attention은..." |
| glossary_terms | 용어 정의 | "Transformer: 2017년 발표된 모델" |
| (미래) faq_chunks | FAQ 데이터 | "Q: RAG란? A: ..." |

**검색 시 컬렉션 지정:**
```python
# paper_chunks 컬렉션에서만 검색
vectorstore = get_pgvector_store("paper_chunks")
results = vectorstore.similarity_search("Attention")

# glossary_terms 컬렉션에서만 검색
glossary_store = get_pgvector_store("glossary_terms")
glossary = glossary_store.similarity_search("Transformer")
```

**장점:**
- ✅ 데이터 격리: 논문과 용어집을 섞지 않음
- ✅ 독립 삭제: paper_chunks만 삭제 가능
- ✅ 성능: 작은 컬렉션에서 검색이 빠름

---

### Q4-3. 벡터 인덱스는 무엇인가요?

**A:** **벡터 유사도 검색을 빠르게 하기 위한 인덱스**입니다.

**PGVector 인덱스 종류:**

#### 1. HNSW (Hierarchical Navigable Small World)
```sql
CREATE INDEX ON langchain_pg_embedding
USING hnsw (embedding vector_l2_ops);
```

**특징:**
- 매우 빠른 검색 (ANN: Approximate Nearest Neighbor)
- 메모리 많이 사용
- **권장**: 대규모 데이터 (10,000개 이상)

#### 2. IVFFlat (Inverted File with Flat)
```sql
CREATE INDEX ON langchain_pg_embedding
USING ivfflat (embedding vector_l2_ops);
```

**특징:**
- 중간 속도
- 메모리 효율적
- **권장**: 중간 규모 (1,000-10,000개)

**우리 프로젝트:**
- 청크 수: 약 5,000개
- 인덱스: HNSW 또는 IVFFlat 모두 가능
- 기본: PGVector가 자동으로 최적화

---

### Q4-4. L2 거리가 무엇인가요?

**A:** **두 벡터 간의 유사도를 측정하는 방법**입니다.

**L2 거리 (Euclidean Distance):**
```
벡터 A: [1, 2, 3]
벡터 B: [4, 5, 6]

L2 거리 = √((4-1)² + (5-2)² + (6-3)²)
        = √(9 + 9 + 9)
        = √27
        = 5.196
```

**의미:**
- **거리 작음 (0에 가까움)**: 매우 유사 ✅
- **거리 큼**: 유사하지 않음 ❌

**실제 예시:**
```python
results = vectorstore.similarity_search_with_score("Attention", k=5)

for doc, score in results:
    print(f"L2 거리: {score:.4f}")
    print(f"내용: {doc.page_content[:50]}")
    print()

# 출력:
# L2 거리: 0.3452  ← 매우 유사
# 내용: "Self-Attention은 입력 시퀀스의..."
#
# L2 거리: 0.5618  ← 중간 유사
# 내용: "Multi-Head Attention은..."
#
# L2 거리: 0.7823  ← 덜 유사
# 내용: "Position Encoding은..."
```

**다른 거리 측정법:**

| 측정법 | 수식 | 범위 | 사용 시점 |
|-------|------|------|----------|
| **L2** | 유클리드 거리 | 0 ~ ∞ | 일반적 (기본값) |
| Cosine | 코사인 유사도 | -1 ~ 1 | 벡터 크기 무시 |
| Inner Product | 내적 | -∞ ~ ∞ | 정규화된 벡터 |

---

## 5. 파이프라인 단계

### Q5-1. Phase 1: 논문 수집이 무엇인가요?

**A:** **arXiv API에서 논문 PDF를 다운로드**하는 단계입니다.

**스크립트:** `scripts/data/collect_arxiv_papers.py`

**동작 흐름:**
```python
1. arXiv API 쿼리 실행
   query = "cat:cs.CL"  # 컴퓨터언어학 카테고리
   results = arxiv.Search(query, max_results=20)

2. 메타데이터 수집
   for result in results:
       metadata = {
           "entry_id": result.entry_id,
           "title": result.title,
           "authors": [a.name for a in result.authors],
           "published": result.published,
           "summary": result.summary,
           "categories": result.categories,
           "pdf_url": result.pdf_url,
       }

3. PDF 다운로드
   arxiv_id = "1706.03762"
   result.download_pdf(dirpath="data/raw/pdfs", filename=f"{arxiv_id}.pdf")

4. 메타데이터 저장
   with open("data/raw/arxiv_papers_metadata.json", "w") as f:
       json.dump(papers_metadata, f)
```

**결과:**
```
data/raw/
├── pdfs/
│   ├── 1706.03762.pdf  ← "Attention Is All You Need"
│   ├── 1810.04805.pdf  ← "BERT"
│   └── ...
└── arxiv_papers_metadata.json  ← 메타데이터
```

---

### Q5-2. Phase 2: 데이터베이스 초기화는 무엇인가요?

**A:** **Papers 테이블에 논문 메타데이터를 저장**하는 단계입니다.

**스크립트:** `scripts/data/setup_database.py`

**동작 흐름:**
```python
1. 메타데이터 로드
   with open("data/raw/arxiv_papers_metadata.json") as f:
       papers = json.load(f)

2. Papers 테이블에 INSERT
   for paper in papers:
       conn.execute("""
           INSERT INTO papers (title, authors, arxiv_id, published, summary, pdf_url)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING id;
       """, (paper['title'], paper['authors'], ...))

       paper_id = cursor.fetchone()[0]

3. paper_id 매핑 저장
   mapping[paper['arxiv_id']] = paper_id
   # {"1706.03762": 1, "1810.04805": 2, ...}

4. 매핑 파일 저장
   with open("data/processed/paper_id_mapping.json", "w") as f:
       json.dump(mapping, f)
```

**결과:**
```sql
-- Papers 테이블
SELECT * FROM papers;
 id |         title          |     arxiv_id  | ...
----+------------------------+---------------+-----
  1 | Attention Is All You Need | 1706.03762 | ...
  2 | BERT                      | 1810.04805 | ...
```

```json
// data/processed/paper_id_mapping.json
{
  "1706.03762": 1,
  "1810.04805": 2
}
```

---

### Q5-3. Phase 3: 문서 처리는 무엇인가요?

**A:** **PDF를 텍스트로 변환하고 청크로 분할**하는 단계입니다.

**스크립트:** `scripts/data/process_documents.py`

**동작 흐름:**
```python
1. PDF 로드
   loader = PaperDocumentLoader(chunk_size=1000, chunk_overlap=200)

2. PDF → 텍스트 변환 (PyPDFLoader)
   documents = PyPDFLoader("1706.03762.pdf").load()
   # [
   #   Document(page_content="Page 1 text...", metadata={"page": 1}),
   #   Document(page_content="Page 2 text...", metadata={"page": 2}),
   # ]

3. 저작권 페이지 필터링
   for doc in documents:
       if "copyright" in doc.page_content.lower() and len(doc.page_content) < 1000:
           continue  # 제외

4. 청크 분할 (RecursiveCharacterTextSplitter)
   chunks = text_splitter.split_documents(filtered_docs)
   # 10페이지 → 50개 청크

5. 메타데이터 추가
   for i, chunk in enumerate(chunks):
       chunk.metadata["chunk_id"] = i
       chunk.metadata["chunk_index"] = i
       chunk.metadata["paper_id"] = 1  # mapping.json에서 가져옴
```

**결과:**
```python
chunks = [
    Document(
        page_content="Transformer는 2017년 발표된 모델입니다...",
        metadata={"paper_id": 1, "chunk_index": 0, "page": 1}
    ),
    Document(
        page_content="Self-Attention은...",
        metadata={"paper_id": 1, "chunk_index": 1, "page": 1}
    ),
    ...
]
```

---

### Q5-4. Phase 4: 임베딩 저장은 무엇인가요?

**A:** **청크를 임베딩하여 PGVector에 저장**하는 단계입니다.

**스크립트:** `scripts/data/load_embeddings.py`

**동작 흐름:**
```python
1. 청크 로드 (Phase 3 결과 사용)
   chunks = loader.load_all_pdfs(pdf_dir, metadata_path)
   # 5,000개 청크

2. 중복 제거
   chunks = deduplicate_chunks(chunks)
   # 4,500개 청크 (500개 중복 제거)

3. PGVector Store 초기화
   vectorstore = get_pgvector_store("paper_chunks")
   # collection_id: 550e8400-...

4. 배치 임베딩 생성 + 저장
   batch_size = 50
   for i in range(0, len(chunks), batch_size):
       batch = chunks[i:i+50]

       # OpenAI API 호출 (임베딩 생성)
       # + PostgreSQL INSERT (저장)
       vectorstore.add_documents(batch)

       time.sleep(0.1)  # Rate Limit 방지
```

**내부 동작 (`add_documents`):**
```python
def add_documents(documents):
    # 1. 임베딩 생성 (OpenAI API)
    texts = [doc.page_content for doc in documents]
    embeddings = openai_embeddings.embed_documents(texts)
    # embeddings = [[0.1, 0.2, ...], [0.3, 0.4, ...], ...]

    # 2. PostgreSQL INSERT
    for doc, embedding in zip(documents, embeddings):
        cursor.execute("""
            INSERT INTO langchain_pg_embedding
            (id, collection_id, document, cmetadata, embedding)
            VALUES (%s, %s, %s, %s, %s);
        """, (
            uuid.uuid4(),
            collection_uuid,
            doc.page_content,
            json.dumps(doc.metadata),
            embedding
        ))
```

**결과:**
```sql
-- langchain_pg_embedding 테이블
SELECT
    cmetadata->>'paper_id' as paper_id,
    COUNT(*) as chunk_count
FROM langchain_pg_embedding
WHERE collection_id = '550e8400-...'
GROUP BY cmetadata->>'paper_id';

 paper_id | chunk_count
----------+-------------
        1 |         50
        2 |         48
      ... |        ...
```

---

## 6. 트러블슈팅

### Q6-1. "청크 중복이 발생했어요"

**증상:**
```sql
SELECT document, COUNT(*)
FROM langchain_pg_embedding
WHERE cmetadata->>'paper_id' = '1'
GROUP BY document
HAVING COUNT(*) > 1;

-- 결과: 동일한 내용의 청크가 3개
```

**원인:**
1. **저작권 페이지 중복**: 첫 페이지(저작권 + 제목)가 여러 청크로 분할됨
2. **필터링 미적용**: `load_pdf()`에서 저작권 페이지를 필터링하지 않음

**해결 방법:**
```python
# src/data/document_loader.py 수정됨 (2025-11-05)
def load_pdf(self, pdf_path: str | Path, metadata: Optional[Dict] = None) -> List[Document]:
    loader = PyPDFLoader(str(pdf_path))
    documents = loader.load()

    # ✅ 저작권 페이지 필터링 추가
    filtered_docs = []
    for doc in documents:
        content = doc.page_content.lower()
        is_copyright_page = (
            ("copyright" in content or "permission" in content) and
            len(doc.page_content) < 1000
        )
        if not is_copyright_page:
            filtered_docs.append(doc)

    return filtered_docs
```

**재실행:**
```bash
# 1. 기존 데이터 삭제
python -c "from src.database.vector_store import delete_collection; delete_collection('paper_chunks')"

# 2. 파이프라인 재실행
python scripts/data/run_full_pipeline.py
```

---

### Q6-2. "특정 논문이 검색되지 않아요"

**증상:**
```python
results = vectorstore.similarity_search("Attention is all you need", k=10)
# paper_id=1이 결과에 없음
```

**원인:**
1. **임베딩 품질 낮음**: 저작권 페이지만 임베딩되어 본문이 없음
2. **메타데이터만 청크화**: 이메일, 저자 목록 등 의미 없는 정보만 있음

**진단:**
```python
# paper_id=1의 청크 내용 확인
chunks = vectorstore.similarity_search("", k=100, filter={"paper_id": 1})
for chunk in chunks[:5]:
    print(chunk.page_content[:100])
    print("---")

# 출력:
# Provided proper attribution is provided, Google hereby grants permission...
# ---
# equal@google.com avaswani@google.com samy@google.com...
# ---
# Attention Is All You Need Ashish Vaswani Jakob Uszkoreit...
```

**해결 방법:**
1. **데이터 재생성**: 저작권 필터링이 적용된 코드로 재실행
2. **특정 논문만 재임베딩**:
   ```bash
   python scripts/data/reembed_proper.py --paper-id 1
   ```

---

### Q6-3. "OpenAI Rate Limit 오류가 나요"

**증상:**
```
openai.error.RateLimitError: Rate limit reached for requests
```

**원인:**
- OpenAI API 무료 티어 제한 초과
  - 분당 3 요청 (무료 티어)
  - 분당 3,000 요청 (유료 티어)

**해결 방법:**

#### 1. 배치 크기 줄이기
```python
# scripts/data/load_embeddings.py
batch_size = 50  # → 10으로 줄이기
```

#### 2. 대기 시간 늘리기
```python
# scripts/data/load_embeddings.py
time.sleep(0.1)  # → 1.0으로 늘리기
```

#### 3. 재시도 로직 활용
```python
# load_embeddings.py에 이미 구현됨
max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        vectorstore.add_documents(batch)
        break
    except Exception as e:
        if "rate limit" in str(e).lower():
            wait_time = 5 * (retry_count + 1)
            time.sleep(wait_time)
            retry_count += 1
```

---

### Q6-4. "chunk_index가 NULL이에요"

**증상:**
```sql
SELECT cmetadata->>'chunk_index' FROM langchain_pg_embedding LIMIT 5;
-- 결과: NULL, NULL, NULL, ...
```

**원인:**
- `document_loader.py`에서 `chunk_index` 메타데이터를 추가하지 않음

**해결 방법:**
```python
# src/data/document_loader.py 수정됨 (2025-11-05)
def load_and_split(self, pdf_path: str | Path, metadata: Optional[Dict] = None) -> List[Document]:
    docs = self.load_pdf(pdf_path, metadata)
    chunks = self.text_splitter.split_documents(docs)
    for i, ch in enumerate(chunks):
        ch.metadata["chunk_id"] = i
        ch.metadata["chunk_index"] = i  # ✅ 추가됨
    return chunks
```

**재실행:**
```bash
# 1. Papers 테이블 및 PGVector 삭제
psql $DATABASE_URL -c "TRUNCATE TABLE papers RESTART IDENTITY CASCADE;"
psql $DATABASE_URL -c "DELETE FROM langchain_pg_embedding WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = 'paper_chunks');"

# 2. 파이프라인 재실행
python scripts/data/run_full_pipeline.py
```

---

### Q6-5. "파이프라인 실행이 중간에 멈춰요"

**증상:**
- Phase 3까지는 성공
- Phase 4에서 멈춤 (진행 표시 없음)

**원인:**
1. **OpenAI API 키 만료**: `.env`의 `OPENAI_API_KEY` 확인
2. **PostgreSQL 연결 끊김**: 장시간 실행 시 연결 타임아웃
3. **메모리 부족**: 청크가 너무 많을 때

**해결 방법:**

#### 1. API 키 확인
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY')[:10])"
# 출력: sk-proj-ab...
```

#### 2. 연결 유지 설정
```python
# src/database/connection.py
conn = psycopg2.connect(
    os.getenv("DATABASE_URL"),
    keepalives=1,
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5
)
```

#### 3. 배치 크기 줄이기
```python
# scripts/data/load_embeddings.py
batch_size = 50  # → 10으로 줄이기
```

---

## 7. 고급 주제

### Q7-1. 청크 크기를 변경하고 싶어요

**방법:**
```python
# scripts/data/load_embeddings.py (또는 process_documents.py)
loader = PaperDocumentLoader(
    chunk_size=1500,    # 1000 → 1500
    chunk_overlap=300   # 200 → 300
)
```

**재실행 필요:**
- ✅ 청크 크기 변경 시 Phase 3부터 재실행
- ❌ 기존 임베딩은 사용 불가 (청크 내용이 달라짐)

**권장 설정:**

| 문서 타입 | chunk_size | chunk_overlap | 이유 |
|----------|-----------|--------------|------|
| 논문 (길고 복잡) | 1000-1500 | 200-300 | 문맥 필요 |
| FAQ (짧고 간결) | 500-800 | 100-150 | 정확한 매칭 |
| 기술 문서 (중간) | 1000-1200 | 200 | 균형 |

---

### Q7-2. 특정 논문만 추가하고 싶어요

**방법:**

#### 1. PDF 파일 추가
```bash
# data/raw/pdfs/에 새 PDF 추가
cp /path/to/new_paper.pdf data/raw/pdfs/2103.00020.pdf
```

#### 2. 메타데이터 추가
```json
// data/raw/arxiv_papers_metadata.json에 추가
{
  "entry_id": "http://arxiv.org/abs/2103.00020v1",
  "title": "New Paper",
  "authors": ["Author Name"],
  "arxiv_id": "2103.00020",
  "published": "2021-03-01",
  ...
}
```

#### 3. Phase 2-4만 재실행
```bash
# Phase 2: Papers 테이블에 INSERT
python scripts/data/setup_database.py

# Phase 3: 청크 분할
python scripts/data/process_documents.py

# Phase 4: 임베딩 생성
python scripts/data/load_embeddings.py
```

**주의:**
- Phase 2에서 중복 INSERT 방지 필요
- 기존 논문은 영향 없음 (새 논문만 추가)

---

### Q7-3. 임베딩 모델을 변경하고 싶어요

**방법:**
```python
# src/database/embeddings.py
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"  # small → large
```

또는 실행 시 환경변수 설정:
```bash
# .env 파일
EMBEDDING_MODEL=text-embedding-3-large
```

**주의사항:**
1. **벡터 차원 변경**: PGVector 스키마 변경 필요
   ```sql
   -- 기존 컬렉션 삭제 후 재생성
   DROP TABLE langchain_pg_embedding;
   -- 새 차원으로 테이블 재생성
   CREATE TABLE langchain_pg_embedding (
       ...
       embedding VECTOR(3072)  -- 1536 → 3072
   );
   ```

2. **비용 증가**: 3-large는 3-small보다 약 10배 비쌈

3. **재임베딩 필요**: 모든 청크 재임베딩 (Phase 4 재실행)

---

### Q7-4. 여러 컬렉션을 동시에 검색하고 싶어요

**방법:**
```python
# 여러 컬렉션에서 검색
from src.database.vector_store import get_pgvector_store

# 각 컬렉션에서 검색
paper_store = get_pgvector_store("paper_chunks")
glossary_store = get_pgvector_store("glossary_terms")

paper_results = paper_store.similarity_search("Transformer", k=5)
glossary_results = glossary_store.similarity_search("Transformer", k=3)

# 결과 병합
all_results = paper_results + glossary_results
```

**고급: 가중치 적용**
```python
# 논문 결과에 높은 가중치
for doc in paper_results:
    doc.metadata["score"] = doc.metadata.get("score", 0) * 1.5  # 논문 우선

for doc in glossary_results:
    doc.metadata["score"] = doc.metadata.get("score", 0) * 0.8  # 용어집 보조

# 점수 기준 정렬
all_results.sort(key=lambda x: x.metadata["score"], reverse=True)
```

---

### Q7-5. 청크를 재배열해서 보여주고 싶어요

**방법:**
```python
# 검색 결과를 chunk_index 순서대로 정렬
results = vectorstore.similarity_search(
    "Transformer Attention",
    k=10,
    filter={"paper_id": 1}
)

# chunk_index 기준 정렬
sorted_results = sorted(
    results,
    key=lambda x: x.metadata.get("chunk_index", 0)
)

# 연속된 텍스트로 재구성
full_text = "\n\n".join([doc.page_content for doc in sorted_results])
print(full_text)
```

**활용 사례:**
- 논문 요약: Top-K 청크를 순서대로 연결
- 문맥 복원: 검색된 청크 앞뒤 문맥 추가
- 하이라이트: 원본 논문에서 위치 표시

---

## 관련 문서

- [데이터 삭제 가이드](../usage/데이터_삭제_가이드.md)
- [데이터 파이프라인 이슈](../issues/데이터_파이프라인_청크_중복_문제.md)
- [RAG 시스템 Q&A](./rag_system_qna.md)
- [실행 명령어 가이드](../usage/실행_명령어_가이드.md)

---

**최종 수정일**: 2025-11-05
