# RAG 시스템 Q&A

## 문서 정보
- **작성일**: 2025-11-04
- **작성자**: 최현화[팀장]
- **목적**: RAG 시스템 관련 자주 묻는 질문 및 답변

---

## 목차
1. [기본 개념](#1-기본-개념)
2. [벡터 검색](#2-벡터-검색)
3. [검색 전략](#3-검색-전략)
4. [메타데이터 필터](#4-메타데이터-필터)
5. [데이터베이스](#5-데이터베이스)
6. [성능 최적화](#6-성능-최적화)
7. [트러블슈팅](#7-트러블슈팅)
8. [고급 활용](#8-고급-활용)

---

## 1. 기본 개념

### Q1-1. RAG가 무엇인가요?

**A:** RAG(Retrieval-Augmented Generation)는 **외부 지식 데이터베이스에서 관련 정보를 검색하여 LLM의 답변을 보강하는 기술**입니다.

**동작 흐름:**
```
사용자: "Transformer 논문 설명해줘"
    ↓
1. 질문 임베딩 (OpenAI Embeddings)
    ↓
2. 벡터 DB에서 유사한 논문 청크 검색
    ↓
3. 검색된 논문 내용을 LLM에 컨텍스트로 제공
    ↓
4. LLM이 논문 내용 기반으로 답변 생성
```

**RAG 없이:**
- LLM 자체 지식으로만 답변 (2021년 이전 지식)
- 환각(hallucination) 가능성 높음

**RAG 사용:**
- 최신 논문 DB 기반 정확한 답변
- 출처 제공 가능 (논문 제목, 저자, URL)

---

### Q1-2. 왜 PostgreSQL + pgvector를 사용하나요?

**A:** **관계형 데이터베이스와 벡터 검색을 하나로 통합**하기 위함입니다.

**장점:**

| 구분 | PostgreSQL + pgvector | 전용 Vector DB (Pinecone, Weaviate 등) |
|------|---------------------|-----------------------------------|
| **통합성** | 논문 메타데이터 + 벡터를 하나의 DB에 | 벡터 DB + 별도 관계형 DB 필요 |
| **SQL 쿼리** | 복잡한 필터링 가능 (년도, 저자 등) | 제한적 |
| **비용** | 무료 (오픈소스) | 유료 (사용량 기반) |
| **관리** | 기존 PostgreSQL 관리 도구 사용 | 별도 학습 필요 |

**예시:**
```sql
-- PostgreSQL + pgvector로 가능한 복잡한 쿼리
SELECT paper_title, authors
FROM paper_chunks
WHERE publish_date >= '2023-01-01'
  AND category = 'cs.CL'
  AND embedding <-> '질문 벡터' < 0.5  -- 벡터 유사도
ORDER BY embedding <-> '질문 벡터'
LIMIT 5;
```

---

### Q1-3. 임베딩(Embedding)이란?

**A:** **텍스트를 숫자 벡터로 변환하는 과정**입니다.

**왜 필요한가?**
- 컴퓨터는 텍스트 유사도를 직접 비교할 수 없음
- 벡터로 변환하면 수학적 거리 계산 가능

**본 프로젝트 설정:**
- **모델**: 환경변수 `EMBEDDING_MODEL` 사용 (기본값: `text-embedding-3-small`)
  - 참고: `configs/model_config.yaml`의 `embeddings.model` 설정은 문서용이며, 실제 코드에는 환경변수가 반영됨
- **차원**: 1536차원 (text-embedding-3-small 기본값)
- **재시도**: OpenAIEmbeddings 기본 설정 사용
- **비용**: 매우 저렴 ($0.02 / 1M 토큰)

**예시:**
```python
from src.database.embeddings import get_embeddings

embeddings = get_embeddings()

# 텍스트 → 벡터 변환
vector = embeddings.embed_query("Transformer 논문")
print(len(vector))  # 1536

# 비슷한 의미는 비슷한 벡터
v1 = embeddings.embed_query("Transformer")
v2 = embeddings.embed_query("Self-Attention")
v3 = embeddings.embed_query("사과")

# v1과 v2는 가까움, v1과 v3는 멀
```

---

### Q1-4. RAGRetriever와 VectorStore의 차이는?

**A:**

| 구분 | VectorStore | RAGRetriever |
|------|------------|--------------|
| **역할** | 벡터 저장소 (DB 인터페이스) | 검색 전략 관리 |
| **파일** | `src/database/vector_store.py` | `src/rag/retriever.py` |
| **기능** | PGVector 초기화, 기본 검색 | Similarity/MMR/MultiQuery 선택 |
| **사용** | 저수준 DB 작업 | 고수준 검색 API |

**VectorStore:**
```python
from src.database.vector_store import get_pgvector_store

# 벡터 저장소 생성
vectorstore = get_pgvector_store("paper_chunks")

# 기본 검색만 가능
docs = vectorstore.similarity_search("Transformer", k=5)
```

**RAGRetriever:**
```python
from src.rag.retriever import RAGRetriever

# 고급 검색 기능 제공
retriever = RAGRetriever(search_type="mmr", k=5)

# MMR, MultiQuery 등 다양한 검색 전략 사용 가능
docs = retriever.multi_query_search("Transformer", k=5)
```

---

## 2. 벡터 검색

### Q2-1. 벡터 검색은 어떻게 동작하나요?

**A:** **질문 벡터와 DB의 논문 벡터 간의 거리를 계산**하여 가장 가까운 문서를 찾습니다.

**단계:**
1. **질문 임베딩**: "Transformer 설명" → [0.123, -0.456, ...]
2. **거리 계산**: DB의 모든 청크 벡터와 거리 계산
3. **정렬**: 거리가 가까운 순서로 정렬
4. **Top-K 선택**: 상위 K개 반환 (기본 k=5)

**거리 측정 방식:**
- **코사인 유사도** (Cosine Similarity): 방향의 유사성
- **L2 거리** (Euclidean Distance): 실제 거리
- pgvector는 기본적으로 **코사인 거리** 사용

**예시:**
```python
from src.rag.retriever import RAGRetriever

retriever = RAGRetriever(k=5)
docs = retriever.invoke("Transformer의 Self-Attention 설명")

for i, doc in enumerate(docs):
    print(f"[{i+1}] {doc.metadata['paper_title']}")
    print(f"내용: {doc.page_content[:100]}...\n")
```

---

### Q2-2. 검색 점수(score)는 무엇인가요?

**A:** **질문 벡터와 문서 벡터 간의 유사도**를 숫자로 나타낸 값입니다.

**점수 범위:**
- **0.0**: 완전 동일 (거리 0)
- **0.0 ~ 0.5**: 매우 유사
- **0.5 ~ 1.0**: 중간 유사
- **1.0 ~ 2.0**: 낮은 유사도

**점수 확인 방법:**
```python
retriever = RAGRetriever(k=5)

# 점수 포함 검색
docs_with_scores = retriever.similarity_search_with_score(
    "Transformer 논문",
    k=5
)

for doc, score in docs_with_scores:
    print(f"제목: {doc.metadata['paper_title']}")
    print(f"점수: {score:.4f}")  # 낮을수록 유사
    print()
```

**점수 기반 필터링:**
```python
# 점수 0.5 이하만 사용 (매우 유사한 것만)
high_quality_docs = [
    doc for doc, score in docs_with_scores
    if score <= 0.5
]
```

---

### Q2-3. 검색 결과가 부정확한 이유는?

**A:** 여러 원인이 있을 수 있습니다.

**1. 임베딩 모델의 한계**
- 질문과 논문의 표현 방식이 너무 다름
- 예: "어텐션 메커니즘" vs "Attention Mechanism" (한영 차이)

**2. 청크 크기 문제**
- 청크가 너무 크면: 관련 없는 내용이 섞임
- 청크가 너무 작으면: 맥락 부족

**3. DB에 관련 논문이 없음**
- 최신 논문이나 특정 주제는 DB에 없을 수 있음

**해결 방법:**
```python
# 1. MultiQuery 사용 (여러 관점에서 검색)
docs = retriever.multi_query_search("Transformer", k=7)

# 2. 검색 결과 수 증가
retriever = RAGRetriever(k=10)  # k=5 → k=10

# 3. MMR 사용 (다양한 내용 확보)
retriever = RAGRetriever(search_type="mmr", lambda_mult=0.3)
```

---

## 3. 검색 전략

### Q3-1. Similarity Search vs MMR vs MultiQuery 차이는?

**A:**

| 특성 | Similarity Search | MMR | MultiQuery |
|------|------------------|-----|------------|
| **원리** | 유사도만 고려 | 유사도 + 다양성 | LLM이 쿼리 확장 |
| **속도** | ⚡⚡⚡ 가장 빠름 | ⚡⚡ 빠름 | ⚡ 느림 |
| **정확도** | ⭐⭐ 중간 | ⭐⭐⭐ 높음 | ⭐⭐⭐ 매우 높음 |
| **다양성** | ⭐ 낮음 | ⭐⭐⭐ 높음 | ⭐⭐ 중간 |
| **비용** | 낮음 (임베딩만) | 낮음 (임베딩만) | 중간 (LLM 호출) |
| **사용 시점** | 빠른 검색 필요 | 균형잡힌 검색 (권장) | 복잡한 질문 |

**코드 예시:**
```python
from src.rag.retriever import RAGRetriever

# 1. Similarity Search
retriever = RAGRetriever(search_type="similarity", k=5)
docs = retriever.invoke("Transformer")

# 2. MMR
retriever = RAGRetriever(search_type="mmr", lambda_mult=0.5, k=5)
docs = retriever.invoke("Transformer")

# 3. MultiQuery
retriever = RAGRetriever(search_type="mmr", k=5)
docs = retriever.multi_query_search("Transformer")
```

---

### Q3-2. MMR의 lambda_mult는 무엇인가요?

**A:** **관련성과 다양성의 균형을 조절하는 파라미터**입니다 (0~1).

**값에 따른 차이:**

| lambda_mult | 행동 | 결과 |
|-------------|------|------|
| **1.0** | 관련성만 고려 | 비슷한 내용 여러 개 (중복 가능) |
| **0.5** | 균형 (기본값) | 관련성 + 다양성 적절히 혼합 |
| **0.0** | 다양성만 고려 | 서로 다른 주제 (관련성 떨어짐) |

**예시:**
```python
# 관련성 우선 (비슷한 내용 여러 개)
retriever = RAGRetriever(
    search_type="mmr",
    lambda_mult=0.9,  # 관련성 90%
    fetch_k=20,
    k=5
)
docs = retriever.invoke("Transformer의 Self-Attention")
# 결과: Self-Attention만 집중적으로 설명

# 다양성 우선 (여러 관점)
retriever = RAGRetriever(
    search_type="mmr",
    lambda_mult=0.3,  # 다양성 70%
    fetch_k=20,
    k=5
)
docs = retriever.invoke("Transformer")
# 결과: Self-Attention, Positional Encoding, FFN 등 다양한 내용
```

**권장 설정:**
- **일반 검색**: `lambda_mult=0.5` (균형)
- **특정 주제 집중**: `lambda_mult=0.7~0.9`
- **포괄적 정보**: `lambda_mult=0.3~0.5`

---

### Q3-3. MultiQuery는 어떻게 동작하나요?

**A:** **LLM이 원본 질문을 여러 관점의 쿼리로 확장**한 후 병렬 검색합니다.

**동작 흐름:**
```
원본 질문: "Transformer의 장단점"
    ↓
Solar Pro2 (LLM) 쿼리 확장:
    - "Transformer 모델의 장점은?"
    - "Transformer의 단점과 한계는?"
    - "Transformer와 RNN/CNN의 차이는?"
    ↓
각 쿼리로 병렬 검색
    ↓
결과 통합 + 중복 제거
    ↓
Top-K 반환
```

**코드:**
```python
from src.rag.retriever import RAGRetriever

retriever = RAGRetriever(k=5)

# MultiQuery 검색
docs = retriever.multi_query_search(
    query="Transformer의 장단점",
    k=7
)

# 단일 질문보다 더 포괄적인 결과 반환
```

**장점:**
- 복잡한 질문에 강함
- 여러 관점 자동 포함

**단점:**
- Solar Pro2 API 호출 필요 (비용 증가)
- 검색 시간 증가 (약 0.5~1초 추가)

---

### Q3-4. MultiQuery가 동작하지 않으면?

**A:** **자동으로 기본 검색으로 폴백**됩니다.

**동작하지 않는 경우:**
1. Solar API 키가 없음 (`SOLAR_API_KEY` 미설정)
2. `langchain-community` 미설치
3. LLM 네트워크 오류

**확인 방법:**
```python
from src.rag.retriever import RAGRetriever

retriever = RAGRetriever(k=5)

# MultiQuery 활성화 여부 확인
if retriever._multi_query_retriever is None:
    print("MultiQuery 비활성화 → 기본 검색 사용")
else:
    print("MultiQuery 활성화")
```

**활성화 방법:**
```bash
# 1. Solar API 키 설정
export SOLAR_API_KEY="your-solar-api-key"

# 2. langchain-community 설치
pip install langchain-community
```

**중요:** MultiQuery 없이도 시스템은 정상 동작합니다 (에러 발생 안함).

---

## 4. 메타데이터 필터

### Q4-1. 메타데이터 필터란?

**A:** **벡터 검색 전에 특정 조건으로 문서를 미리 걸러내는 기능**입니다.

**지원 필터:**
- `year_gte`: 특정 연도 이상
- `author`: 저자 이름 부분일치
- `category`: 논문 카테고리 (예: cs.CL, cs.AI)

**예시:**
```python
from src.rag.retriever import RAGRetriever

retriever = RAGRetriever(k=5)

# 2023년 이후 논문만 검색
docs = retriever.search_with_filter(
    query="최신 LLM 모델",
    filter_dict={"year": {"$gte": 2023}},
    k=5
)

# 특정 저자 논문만 검색
docs = retriever.search_with_filter(
    query="Attention 메커니즘",
    filter_dict={"authors": {"$ilike": "%Vaswani%"}},
    k=5
)

# 복합 필터
docs = retriever.search_with_filter(
    query="Transformer",
    filter_dict={
        "year": {"$gte": 2020},
        "category": "cs.CL"
    },
    k=5
)
```

---

### Q4-2. search_paper_database 도구의 필터 파라미터는?

**A:** `search_paper_database` 도구는 사용자 친화적인 파라미터를 제공합니다.

**파라미터:**
```python
from src.tools.search_paper import search_paper_database

result = search_paper_database(
    query="Transformer 논문",
    year_gte=2020,              # 2020년 이상
    author="Vaswani",           # 저자 필터
    category="cs.CL",           # 카테고리
    top_k=5,                    # 결과 개수
    with_scores=True,           # 점수 포함
    use_multi_query=True,       # MultiQuery 사용
    search_mode="mmr"           # 검색 모드
)
```

**내부 동작:**
1. `year_gte`, `author`, `category` → 메타데이터 필터로 변환
2. 필터가 있으면 `search_with_filter()` 호출
3. 없으면 일반 검색 (MultiQuery 또는 기본)

---

### Q4-3. 필터링 후 결과가 없으면?

**A:** **빈 리스트 반환** (에러 없음).

**코드:**
```python
retriever = RAGRetriever(k=5)

docs = retriever.search_with_filter(
    query="Transformer",
    filter_dict={"publish_date": {"$gte": "2030-01-01"}},  # 미래 날짜
    k=5
)

print(len(docs))  # 0
```

**처리 방법:**
```python
if not docs:
    print("필터 조건에 맞는 논문이 없습니다.")
    # 필터 없이 재검색
    docs = retriever.invoke(query)
```

---

## 5. 데이터베이스

### Q5-1. pgvector는 무엇인가요?

**A:** **PostgreSQL에서 벡터 연산을 가능하게 하는 확장(extension)**입니다.

**주요 기능:**
- 벡터 타입 지원 (`vector(1536)`)
- 벡터 거리 연산자 (`<->`, `<#>`, `<=>`)
- 벡터 인덱스 (IVFFlat, HNSW)

**설치:**
```bash
# PostgreSQL에 pgvector 설치
CREATE EXTENSION IF NOT EXISTS vector;
```

**테이블 예시:**
```sql
CREATE TABLE paper_chunks (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER,
    content TEXT,
    embedding vector(1536),  -- pgvector 타입
    metadata JSONB
);

-- 벡터 인덱스 생성 (검색 속도 향상)
CREATE INDEX ON paper_chunks USING ivfflat (embedding vector_cosine_ops);
```

**벡터 검색 SQL:**
```sql
-- 가장 유사한 5개 문서 검색
SELECT content, metadata
FROM paper_chunks
ORDER BY embedding <-> '[0.123, -0.456, ...]'  -- 질문 벡터
LIMIT 5;
```

---

### Q5-2. paper_chunks 테이블 구조는?

**A:** 논문을 청크(chunk)로 나눠 저장하는 테이블입니다.

**스키마:**
```sql
CREATE TABLE paper_chunks (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER,           -- 논문 ID (papers 테이블 참조)
    content TEXT,               -- 청크 텍스트 (약 1000자)
    embedding vector(1536),     -- 텍스트 임베딩
    metadata JSONB              -- 메타데이터
);
```

**metadata 필드:**
```json
{
    "paper_id": 123,
    "paper_title": "Attention is All You Need",
    "authors": "Vaswani et al.",
    "publish_date": "2017-06-12",
    "chunk_index": 0,
    "section": "Abstract",
    "category": "cs.CL"
}
```

**데이터 확인:**
```sql
-- 총 청크 수
SELECT COUNT(*) FROM paper_chunks;

-- 특정 논문의 청크 수
SELECT COUNT(*) FROM paper_chunks WHERE paper_id = 123;

-- 논문별 청크 수 통계
SELECT paper_id, COUNT(*) as chunk_count
FROM paper_chunks
GROUP BY paper_id
ORDER BY chunk_count DESC
LIMIT 10;
```

---

### Q5-3. 청크(chunk)란?

**A:** **긴 논문을 작은 단위로 나눈 텍스트 조각**입니다.

**왜 청킹이 필요한가?**
1. **LLM 컨텍스트 제한**: 논문 전체를 넣을 수 없음
2. **검색 정확도**: 작은 단위가 더 정밀한 검색 가능
3. **임베딩 품질**: 짧은 텍스트가 더 명확한 벡터

**청킹 설정 (configs/model_config.yaml):**
```yaml
rag:
  chunk_size: 1000        # 청크 크기 (문자)
  chunk_overlap: 200      # 오버랩 (문자)
```

**예시:**
```
논문 전체 (5000자)
    ↓ 청킹
청크 1: [0~1000자]   (Abstract + Introduction 일부)
청크 2: [800~1800자] (Introduction 나머지 + Method 일부) ← 200자 오버랩
청크 3: [1600~2600자] (Method 계속)
...
```

**오버랩의 역할:**
- 문장이 잘리는 것 방지
- 맥락 연결 유지

---

### Q5-4. PostgreSQL 연결 문자열은 어떻게 설정하나요?

**A:** **configs/db_config.yaml** 파일을 사용합니다 (권장).

**1. db_config.yaml 설정:**
```yaml
# configs/db_config.yaml
postgresql:
  host: localhost
  port: 5432
  database: papers
  user: postgres
  password: your-password
```

**2. 환경변수 (폴백):**
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=papers
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your-password
```

**3. 코드에서 확인:**
```python
from src.utils.config_loader import get_postgres_connection_string

conn_str = get_postgres_connection_string()
print(conn_str)
# postgresql://postgres:password@localhost:5432/papers
```

---

### Q5-5. 벡터 인덱스는 무엇이고 왜 필요한가요?

**A:** **벡터 검색 속도를 향상시키는 데이터 구조**입니다.

**인덱스 없을 때:**
- 모든 벡터와 거리 계산 (Full Scan)
- 1만 개 청크 → 1만 번 계산
- 느림 (몇 초 소요)

**인덱스 있을 때:**
- 유사한 벡터만 빠르게 탐색
- 근사 검색 (Approximate Nearest Neighbor)
- 빠름 (0.1초 이하)

**인덱스 종류:**

| 인덱스 | 속도 | 정확도 | 권장 상황 |
|--------|------|--------|----------|
| **IVFFlat** | ⚡⚡ 빠름 | ⭐⭐ 중간 | 일반적 (권장) |
| **HNSW** | ⚡⚡⚡ 매우 빠름 | ⭐⭐⭐ 높음 | 대용량 (10만+ 벡터) |

**인덱스 생성:**
```sql
-- IVFFlat 인덱스 (권장)
CREATE INDEX ON paper_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- HNSW 인덱스 (대용량)
CREATE INDEX ON paper_chunks
USING hnsw (embedding vector_cosine_ops);
```

**인덱스 확인:**
```sql
-- 인덱스 목록
\d paper_chunks

-- 인덱스 크기
SELECT pg_size_pretty(pg_total_relation_size('paper_chunks_embedding_idx'));
```

---

## 6. 성능 최적화

### Q6-1. 검색 속도를 높이려면?

**A:** 여러 방법이 있습니다.

**1. 검색 모드 변경**
```python
# Similarity (가장 빠름)
retriever = RAGRetriever(search_type="similarity", k=5)

# MMR (중간)
retriever = RAGRetriever(search_type="mmr", k=5)

# MultiQuery 사용 안 함 (빠름)
docs = retriever.invoke(query)  # MultiQuery 대신
```

**2. k 값 줄이기**
```python
# k=10 → k=3
retriever = RAGRetriever(k=3)  # 검색 결과 개수 감소
```

**3. 벡터 인덱스 추가**
```sql
CREATE INDEX ON paper_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**4. PostgreSQL 최적화**
```sql
-- 쿼리 캐시 증가
ALTER SYSTEM SET shared_buffers = '256MB';

-- 병렬 쿼리 활성화
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
```

**속도 비교:**

| 설정 | 평균 응답 시간 |
|------|---------------|
| Similarity + k=3 + 인덱스 | 0.10초 |
| MMR + k=5 + 인덱스 | 0.18초 |
| MultiQuery + k=5 + 인덱스 | 0.85초 |
| Similarity + k=10 + 인덱스 없음 | 1.50초 |

---

### Q6-2. 검색 정확도를 높이려면?

**A:**

**1. MultiQuery 사용**
```python
retriever = RAGRetriever(k=5)
docs = retriever.multi_query_search(query, k=7)
# 여러 관점에서 검색 → 정확도 향상
```

**2. k 값 증가 후 재정렬**
```python
# 많이 검색 후 점수로 필터링
retriever = RAGRetriever(k=10)
docs_with_scores = retriever.similarity_search_with_score(query, k=10)

# 점수 0.5 이하만 사용
high_quality = [doc for doc, score in docs_with_scores if score <= 0.5]
```

**3. MMR 사용 (다양성 확보)**
```python
retriever = RAGRetriever(
    search_type="mmr",
    lambda_mult=0.5,  # 균형
    fetch_k=20,       # 후보 많이
    k=5
)
```

**4. 청크 크기 조정**
```yaml
# configs/model_config.yaml
rag:
  chunk_size: 800       # 1000 → 800 (더 정밀)
  chunk_overlap: 150    # 오버랩 증가
```

---

### Q6-3. chunk_size를 어떻게 설정해야 하나요?

**A:** 사용 목적에 따라 다릅니다.

**청크 크기별 특성:**

| chunk_size | 장점 | 단점 | 권장 상황 |
|-----------|------|------|----------|
| **500자** | 정밀한 검색 | 맥락 부족, 청크 수 많음 | 특정 용어/개념 검색 |
| **1000자 (기본)** | 균형 | - | 일반적 사용 (권장) |
| **2000자** | 넓은 맥락 | 관련 없는 내용 섞임 | 포괄적 정보 수집 |

**설정 방법:**
```yaml
# configs/model_config.yaml
rag:
  chunk_size: 1000      # 청크 크기
  chunk_overlap: 200    # 오버랩 (chunk_size의 20%)
```

**권장 오버랩:**
- chunk_size의 15~20%
- 예: chunk_size=1000 → overlap=150~200

---

### Q6-4. fetch_k는 무엇이고 어떻게 설정하나요?

**A:** **MMR 검색 시 최초로 가져올 후보 문서 수**입니다.

**동작:**
```
fetch_k=20, k=5 설정 시:
    ↓
1. 유사도 검색으로 20개 문서 가져오기
    ↓
2. 20개 중에서 MMR 알고리즘으로 5개 선택
   (관련성 + 다양성 고려)
```

**권장 설정:**
- **fetch_k = 4 × k** (기본 권장)
- 예: k=5 → fetch_k=20
- 예: k=10 → fetch_k=40

**fetch_k가 클수록:**
- 장점: 다양성 확보, 더 나은 품질
- 단점: 검색 시간 증가

**코드:**
```python
# 다양성 중요 (fetch_k 크게)
retriever = RAGRetriever(
    search_type="mmr",
    k=5,
    fetch_k=30,          # 6배
    lambda_mult=0.3      # 다양성 우선
)

# 속도 중요 (fetch_k 작게)
retriever = RAGRetriever(
    search_type="mmr",
    k=5,
    fetch_k=10,          # 2배
    lambda_mult=0.7      # 관련성 우선
)
```

---

## 7. 트러블슈팅

### Q7-1. "relation paper_chunks does not exist" 에러

**원인:** `paper_chunks` 테이블이 없습니다.

**해결:**
```bash
# 1. PostgreSQL 연결 확인
psql $DATABASE_URL -c "SELECT 1;"

# 2. 테이블 존재 확인
psql $DATABASE_URL -c "\dt"

# 3. paper_chunks 테이블 생성 (스크립트 실행)
python scripts/create_vector_table.py
```

---

### Q7-2. "OpenAI API key not found" 에러

**원인:** OpenAI API 키가 설정되지 않았습니다.

**해결:**
```bash
# 환경변수 설정
export OPENAI_API_KEY="sk-..."

# 확인
echo $OPENAI_API_KEY
```

**코드에서 확인:**
```python
import os
print(os.getenv("OPENAI_API_KEY"))  # None이면 미설정
```

---

### Q7-3. 검색 결과가 항상 같은 논문만 나옴

**원인:** 데이터베이스에 논문이 적거나, MMR 설정 문제입니다.

**해결:**

**1. DB 데이터 확인**
```sql
-- 총 논문 수
SELECT COUNT(DISTINCT paper_id) FROM paper_chunks;

-- 총 청크 수
SELECT COUNT(*) FROM paper_chunks;
```

**2. MMR 다양성 증가**
```python
retriever = RAGRetriever(
    search_type="mmr",
    lambda_mult=0.2,  # 다양성 우선 (0.5 → 0.2)
    fetch_k=30,       # 후보 증가
    k=5
)
```

**3. k 값 증가**
```python
retriever = RAGRetriever(k=10)  # k=5 → k=10
```

---

### Q7-4. 검색 속도가 너무 느림 (3초 이상)

**원인:**
1. 벡터 인덱스 없음
2. MultiQuery 사용
3. PostgreSQL 성능 문제

**해결:**

**1. 인덱스 확인 및 생성**
```sql
-- 인덱스 확인
\d paper_chunks

-- 인덱스 생성
CREATE INDEX ON paper_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**2. MultiQuery 비활성화**
```python
# MultiQuery 사용 안 함
docs = retriever.invoke(query)  # multi_query_search 대신
```

**3. PostgreSQL 설정 최적화**
```sql
-- shared_buffers 증가
ALTER SYSTEM SET shared_buffers = '256MB';

-- 재시작
sudo systemctl restart postgresql
```

---

### Q7-5. 한글 검색이 잘 안됨

**원인:** 임베딩 모델이 영어에 최적화되어 있습니다.

**해결:**

**1. 영문 키워드 포함**
```python
# "어텐션" → "Attention 메커니즘"
docs = retriever.invoke("Attention 메커니즘")
```

**2. MultiQuery 사용 (자동 번역 효과)**
```python
# Solar Pro2가 영어로 쿼리 확장
docs = retriever.multi_query_search("어텐션 메커니즘")
# 확장: "Attention mechanism", "Self-Attention", ...
```

**3. 다국어 임베딩 모델 (향후)**
```python
# multilingual 모델로 변경 (향후 지원 예정)
embeddings = get_embeddings("multilingual-e5-large")
```

---

## 8. 고급 활용

### Q8-1. 검색 모드를 런타임에 변경하려면?

**A:** `set_mode()` 메서드를 사용합니다.

```python
from src.rag.retriever import RAGRetriever

retriever = RAGRetriever(search_type="similarity", k=5)

# 첫 번째 검색: Similarity
docs = retriever.invoke("Transformer")

# 검색 모드 변경: MMR로 전환
retriever.set_mode("mmr")

# 두 번째 검색: MMR
docs = retriever.invoke("Transformer")
```

---

### Q8-2. 검색 결과를 LLM에 전달하려면?

**A:** LangChain의 `Document` 형식이므로 바로 사용 가능합니다.

```python
from src.rag.retriever import RAGRetriever
from src.llm.client import LLMClient
from langchain.schema import SystemMessage, HumanMessage

# 1. 검색
retriever = RAGRetriever(k=5)
docs = retriever.invoke("Transformer 설명")

# 2. 검색 결과를 컨텍스트로 변환
context = "\n\n".join([
    f"[논문 {i+1}] {doc.metadata['paper_title']}\n{doc.page_content}"
    for i, doc in enumerate(docs)
])

# 3. 두 수준의 답변 생성 (실제 search_paper 도구 방식)
level_mapping = {
    "easy": ["elementary", "beginner"],
    "hard": ["intermediate", "advanced"]
}

difficulty = "easy"  # 또는 "hard"
levels = level_mapping[difficulty]
final_answers = {}

# LLM 클라이언트 초기화
llm_client = LLMClient.from_difficulty(difficulty=difficulty)

# 각 수준별로 답변 생성
for level in levels:
    # 수준별 시스템 프롬프트 로드
    from src.prompts import get_tool_prompt
    system_prompt = get_tool_prompt("search_paper", level)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"컨텍스트:\n{context}\n\n질문: Transformer 설명해줘")
    ]

    response = llm_client.llm.invoke(messages)
    final_answers[level] = response.content

# 결과: easy 모드면 {"elementary": "...", "beginner": "..."}
#      hard 모드면 {"intermediate": "...", "advanced": "..."}
print(f"생성된 수준: {list(final_answers.keys())}")
print(f"첫 번째 답변: {final_answers[levels[0]][:100]}...")
```

---

### Q8-3. 특정 섹션만 검색하려면?

**A:** 메타데이터 필터로 `section` 필드를 사용합니다.

```python
retriever = RAGRetriever(k=5)

# Abstract만 검색
docs = retriever.search_with_filter(
    query="Transformer",
    filter_dict={"section": "Abstract"},
    k=5
)

# Method 섹션만 검색
docs = retriever.search_with_filter(
    query="Self-Attention 구현",
    filter_dict={"section": "Method"},
    k=5
)
```

**section 값:**
- `"Abstract"`: 초록
- `"Introduction"`: 서론
- `"Method"`: 방법론
- `"Results"`: 결과
- `"Conclusion"`: 결론
- `"본문"`: 섹션 구분 없음

---

### Q8-4. 검색 결과를 파일로 저장하려면?

**A:**

```python
import json
from src.rag.retriever import RAGRetriever

retriever = RAGRetriever(k=5)
docs_with_scores = retriever.similarity_search_with_score("Transformer", k=5)

# JSON으로 저장
results = []
for doc, score in docs_with_scores:
    results.append({
        "paper_title": doc.metadata.get("paper_title", "N/A"),
        "authors": doc.metadata.get("authors", "N/A"),
        "content": doc.page_content,
        "score": float(score),
        "metadata": doc.metadata
    })

with open("search_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("검색 결과 저장 완료: search_results.json")
```

---

### Q8-5. 벡터 DB 통계를 확인하려면?

**A:**

```sql
-- 1. 총 논문/청크 수
SELECT
    COUNT(DISTINCT paper_id) as total_papers,
    COUNT(*) as total_chunks
FROM paper_chunks;

-- 2. 논문별 청크 수
SELECT
    paper_id,
    COUNT(*) as chunk_count,
    MAX(metadata->>'paper_title') as title
FROM paper_chunks
GROUP BY paper_id
ORDER BY chunk_count DESC
LIMIT 10;

-- 3. 카테고리별 통계
SELECT
    metadata->>'category' as category,
    COUNT(*) as count
FROM paper_chunks
GROUP BY category
ORDER BY count DESC;

-- 4. 연도별 통계
SELECT
    EXTRACT(YEAR FROM (metadata->>'publish_date')::date) as year,
    COUNT(DISTINCT paper_id) as paper_count
FROM paper_chunks
GROUP BY year
ORDER BY year DESC;

-- 5. 데이터베이스 크기
SELECT pg_size_pretty(pg_total_relation_size('paper_chunks'));
```

---

## 참고 자료

### 관련 문서
- [11_RAG_시스템.md](../modularization/11_RAG_시스템.md)
- [08_데이터베이스_통합_가이드.md](../modularization/08_데이터베이스_통합_가이드.md)
- [09_도구_시스템.md](../modularization/09_도구_시스템.md) - search_paper 도구

### 구현 파일
- `src/rag/retriever.py` - RAGRetriever 클래스
- `src/database/vector_store.py` - PGVector VectorStore
- `src/database/embeddings.py` - OpenAI Embeddings
- `src/tools/search_paper.py` - 논문 검색 도구

### 외부 자료
- [LangChain PGVector 문서](https://python.langchain.com/docs/integrations/vectorstores/pgvector)
- [pgvector 공식 문서](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [MMR 알고리즘 논문](https://www.cs.cmu.edu/~jgc/publication/The_Use_MMR_Diversity_Based_LTMIR_1998.pdf)

---

## 작성자
- **최현화[팀장]** (RAG 시스템 구현 및 문서화)
