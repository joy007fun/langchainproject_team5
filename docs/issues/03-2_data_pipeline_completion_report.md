# 데이터 파이프라인 구현 완료 보고서

- **작업 주제**: arXiv 논문 수집, Document 처리, 임베딩 생성 및 PostgreSQL + pgvector 적재
- **작성자**: 최현화[팀장]
- **담당자**: 박재홍  
- **작업 기간**: 2025-10-28 ~ 2025-10-31  
- **문서 작성일**: 2025-10-31  

---

## 📊 전체 완료 상태

| Phase | 항목 | 상태 | 비고 |
|-------|------|------|------|
| Phase 1 | 데이터 수집 스크립트 | ✅ 완료 | ArxivPaperCollector 구현 완료 |
| Phase 2 | Document Loader | ✅ 완료 | PaperDocumentLoader 구현 완료 |
| Phase 3 | 임베딩 및 Vector DB | ✅ 완료 | PaperEmbeddingManager 구현 완료 |
| Phase 4 | 데이터베이스 초기 설정 | ✅ 완료 | setup_database.py 구현 완료 |
| Phase 5 | 인수인계 문서 | ✅ 완료 | 본 문서 및 실행 가이드 작성 |

**전체 진행률**: 100% ✅

---

## Phase 1: 데이터 수집 스크립트 ✅

### 구현 완료 항목

#### ✅ ArxivPaperCollector 클래스 구현
- **파일 위치**: `scripts/collect_arxiv_papers.py`
- **구현 상태**: 완료

**주요 메서드:**

1. **`collect_papers(query, max_results)`**
   - arXiv API를 사용하여 논문 검색
   - PDF 다운로드 및 저장 (`data/raw/pdfs/`)
   - 메타데이터 추출:
     - `title`: 논문 제목
     - `authors`: 저자 목록
     - `published_date`: 출판일
     - `summary`: 초록
     - `pdf_url`: PDF URL
     - `categories`: 카테고리 목록
     - `entry_id`: arXiv ID

2. **`collect_by_keywords(keywords, per_keyword)`**
   - 여러 키워드로 반복 수집
   - 키워드별로 지정된 수만큼 논문 수집
   - 중복 자동 제거

3. **`remove_duplicates(items)`**
   - 제목 기준 중복 제거
   - `title`을 키로 사용하여 중복 논문 제거

**AI/ML 키워드 리스트:**
```python
keywords = [
    "transformer attention",
    "BERT GPT",
    "large language model",
    "retrieval augmented generation",
    "neural machine translation",
    "question answering",
    "AI agent",
]
```

**메타데이터 저장:**
- **파일 위치**: `data/raw/arxiv_papers_metadata.json`
- **형식**: JSON 배열
- **실제 수집 데이터**: 75개 논문

**실행 방법:**
```bash
python scripts/collect_arxiv_papers.py
```

---

## Phase 2: Document Loader 구현 ✅

### 구현 완료 항목

#### ✅ PaperDocumentLoader 클래스 구현
- **파일 위치**: `src/data/document_loader.py`
- **구현 상태**: 완료

**주요 메서드:**

1. **초기화**
   ```python
   loader = PaperDocumentLoader(
       chunk_size=1000,
       chunk_overlap=200
   )
   ```
   - `RecursiveCharacterTextSplitter` 사용
   - 청크 크기: 1000자
   - 오버랩: 200자

2. **`load_pdf(pdf_path)`**
   - `PyPDFLoader`를 사용하여 PDF 로드
   - PDF에서 텍스트 추출

3. **`load_and_split(pdf_path, metadata=None)`**
   - PDF 로드 및 청크 분할
   - 각 청크에 `chunk_id` 메타데이터 추가
   - arXiv ID, 제목 등 메타데이터 포함

4. **`load_all_pdfs(pdf_dir, metadata_path)`**
   - 디렉토리 내 모든 PDF 처리
   - 메타데이터 JSON 파일과 매핑
   - arXiv ID → 논문 정보 매핑

**실행 방법:**
```bash
python scripts/process_documents.py
```

---

## Phase 3: 임베딩 및 Vector DB 적재 ✅

### 구현 완료 항목

#### ✅ PaperEmbeddingManager 클래스 구현
- **파일 위치**: `src/data/embeddings.py`
- **구현 상태**: 완료

**주요 기능:**

1. **초기화**
   ```python
   manager = PaperEmbeddingManager(
       collection_name="paper_chunks"
   )
   ```
   - OpenAI Embeddings 모델: `text-embedding-3-small`
   - PGVector 컬렉션: `paper_chunks`
   - 연결: `DATABASE_URL` 환경 변수 사용

2. **`add_documents(documents, batch_size=50)`**
   - 문서 리스트를 배치로 나누어 저장
   - 배치 크기: 50개
   - 진행 상황 로깅
   - Rate Limit 대응 (배치 간 100ms 대기)
   - Rate Limit 오류 시 5초 대기 후 재시도

3. **`add_documents_with_paper_id(documents, paper_id_mapping, batch_size=50)`**
   - `paper_id` 메타데이터 추가
   - `arxiv_id` → `paper_id` 매핑 사용
   - 문서에 `paper_id` 메타데이터 포함하여 저장

**오류 처리:**
- OpenAI API Rate Limit 감지 및 대기
- 배치 실패 시 해당 배치만 건너뛰고 계속 진행
- 상세한 로그 기록

**실행 방법:**
```bash
python scripts/load_embeddings.py
```

---

## Phase 4: 데이터베이스 초기 설정 ✅

### 구현 완료 항목

#### ✅ PostgreSQL 스키마 생성
- **파일 위치**: `scripts/setup_database.py`
- **구현 상태**: 완료

**구현된 함수:**

1. **`ensure_pgvector(conn, cur)`**
   - pgvector extension 설치 및 활성화

2. **테이블 생성**
   - **`papers` 테이블**:
     - `paper_id` (SERIAL PRIMARY KEY)
     - `arxiv_id` (VARCHAR(64))
     - `title` (TEXT NOT NULL)
     - `authors` (TEXT)
     - `publish_date` (DATE)
     - `source` (VARCHAR(32))
     - `url` (TEXT UNIQUE)
     - `category` (TEXT)
     - `citation_count` (INT)
     - `abstract` (TEXT)
     - `created_at` (TIMESTAMP)

   - **`glossary` 테이블**:
     - `term_id` (SERIAL PRIMARY KEY)
     - `term` (VARCHAR(200) UNIQUE)
     - `definition` (TEXT)
     - `easy_explanation` (TEXT)
     - `hard_explanation` (TEXT)
     - `category` (TEXT)
     - `difficulty_level` (INT)
     - `related_terms` (TEXT)
     - `examples` (TEXT)
     - `created_at` (TIMESTAMP)

3. **인덱스 생성**
   - `idx_papers_title`: GIN 인덱스 (Full-text search)
   - `idx_papers_category`: 카테고리 인덱스
   - `idx_papers_date`: 날짜 인덱스
   - `idx_glossary_term`: 용어 인덱스
   - `idx_glossary_category`: 카테고리 인덱스

4. **`insert_paper_metadata(conn, cur)`**
   - JSON 메타데이터를 `papers` 테이블에 INSERT
   - `ON CONFLICT (url) DO NOTHING` (중복 방지)
   - `RETURNING paper_id`로 ID 조회
   - arXiv ID → paper_id 매핑 딕셔너리 생성

5. **`insert_glossary_data(conn, cur)`**
   - 초기 용어집 데이터 삽입
   - Attention Mechanism, Fine-tuning, BLEU Score 등 포함

6. **`save_paper_id_mapping(conn, mapping=None)`**
   - `data/processed/paper_id_mapping.json` 파일 생성
   - arXiv ID → paper_id 매핑 저장

**실행 방법:**
```bash
python scripts/setup_database.py
```

**주요 기능 상세:**
- pgvector 확장 자동 설치 확인
- `papers` 테이블에 메타데이터 자동 삽입
- `glossary` 테이블에 초기 용어집 데이터 삽입
- `paper_id_mapping.json` 파일 자동 생성

---

## Phase 5: 인수인계 문서 ✅

### 완료 항목

#### ✅ 문서 작성 완료

1. **실행 가이드** (`docs/실행_가이드.md`)
   - 단계별 실행 명령어
   - 환경 변수 설정 방법
   - 데이터 확인 방법

2. **테스트 결과** (`docs/test_results.md`)
   - 파이프라인 구조 테스트 결과
   - 환경 문제 및 해결 방법

3. **데이터 파이프라인 이슈 문서** (`docs/issues/data_pipeline_implementation.md`)
   - 작업 체크리스트
   - 구현 요구사항

4. **데이터베이스 설계 문서** (`docs/PRD/11_데이터베이스_설계.md`)
   - DB 스키마 상세 설명
   - pgvector 설정
   - 데이터 흐름

5. **본 완료 보고서** (`docs/issues/data_pipeline_completion_report.md`)

---

## 📦 실행 명령어

### 사전 준비

```bash
# 가상환경 활성화
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate  # Windows

# 필요한 패키지 설치
pip install arxiv pypdf langchain langchain-openai langchain-postgres pgvector psycopg2-binary python-dotenv

# 환경 변수 설정 (.env 파일)
DATABASE_URL=postgresql://user:password@localhost:5432/papers
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # 선택사항
```

### 단계별 실행

#### 1단계: arXiv 논문 수집
```bash
python scripts/collect_arxiv_papers.py
```
- **소요 시간**: 약 20-30분
- **결과**: 
  - `data/raw/pdfs/`: PDF 파일 (75개)
  - `data/raw/arxiv_papers_metadata.json`: 메타데이터

#### 2단계: PostgreSQL 스키마 생성
```bash
python scripts/setup_database.py
```
- **소요 시간**: 약 1-2분
- **결과**:
  - PostgreSQL 테이블 생성
  - 메타데이터 삽입
  - `data/processed/paper_id_mapping.json`: 매핑 파일

#### 3단계: Document 로드 및 청크 분할
```bash
python scripts/process_documents.py
```
- **소요 시간**: 약 10-20분
- **결과**: Document 객체 리스트 (메모리)

#### 4단계: 임베딩 생성 및 Vector DB 저장
```bash
python scripts/load_embeddings.py
```
- **소요 시간**: 약 30분-1시간 (논문 수에 따라 다름)
- **결과**: PostgreSQL pgvector에 임베딩 저장

#### 전체 파이프라인 일괄 실행
```bash
python scripts/run_full_pipeline.py
```
- 위 4단계를 순차적으로 실행

---

## 📁 데이터 위치

### 로컬 파일
```
data/
├── raw/
│   ├── pdfs/                           # 다운로드한 PDF 파일 (75개)
│   └── arxiv_papers_metadata.json     # 논문 메타데이터 (75개)
└── processed/
    └── paper_id_mapping.json           # arxiv_id → paper_id 매핑
```

### 데이터베이스
- **PostgreSQL**: 논문 메타데이터, 용어집
- **pgvector 컬렉션**: `paper_chunks` (임베딩 벡터)

---

## 🔍 데이터 확인 방법

### 파일 확인
```bash
# PDF 파일 개수
ls -lh data/raw/pdfs/ | wc -l  # Linux/Mac
dir data\raw\pdfs\*.pdf | measure  # Windows

# 논문 개수 확인
python -c "import json; data=json.load(open('data/raw/arxiv_papers_metadata.json', encoding='utf-8')); print(len(data))"

# 매핑 파일 확인
python -c "import json; m=json.load(open('data/processed/paper_id_mapping.json', encoding='utf-8')); print(f'{len(m)}개 매핑')"
```

### 데이터베이스 확인
```bash
# 논문 개수
psql -U your_username -d papers -c "SELECT COUNT(*) FROM papers;"

# 용어집 개수
psql -U your_username -d papers -c "SELECT COUNT(*) FROM glossary;"

# 최근 논문 5개
psql -U your_username -d papers -c "SELECT paper_id, title, category FROM papers ORDER BY created_at DESC LIMIT 5;"

# pgvector 컬렉션 확인
psql -U your_username -d papers -c "SELECT COUNT(*) FROM langchain_pg_collection WHERE collection_name = 'paper_chunks';"
```

---

## 📝 Logger 적용

모든 스크립트에 Logger가 적용되어 있습니다:

- **`scripts/collect_arxiv_papers.py`**: 논문 수집 진행 상황 로깅
- **`src/data/embeddings.py`**: 배치 처리 진행 상황 로깅
- **`scripts/setup_database.py`**: 데이터베이스 설정 진행 상황 출력

**로그 위치:**
- 실험 로그: `experiments/YYYYMMDD/HHMMSS_task_name/experiment.log`
- 콘솔 출력: 진행 상황 및 오류 메시지

---

## ⚠️ 주의사항

### 1. 실행 순서
반드시 다음 순서대로 실행해야 합니다:
1. `collect_arxiv_papers.py` → 논문 수집
2. `setup_database.py` → DB 초기화 및 메타데이터 삽입
3. `process_documents.py` → PDF 처리
4. `load_embeddings.py` → 임베딩 저장

### 2. 환경 변수
모든 스크립트는 `.env` 파일에서 환경 변수를 읽습니다:
- `DATABASE_URL`: 필수 (PostgreSQL 연결 정보)
- `OPENAI_API_KEY`: 필수 (Phase 4에서 필요)

### 3. API Rate Limit
- OpenAI Embeddings API는 Rate Limit이 있습니다
- `batch_size=50`으로 배치 처리하며 자동 대기 시간 적용
- 너무 빠르게 실행 시 일부 문서가 실패할 수 있습니다

### 4. PyTorch 오류 (Windows)
Windows에서 PyTorch DLL 오류 발생 시:
```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 5. 중복 데이터 방지
- `papers` 테이블의 `url` 컬럼에 UNIQUE 제약 조건
- `ON CONFLICT (url) DO NOTHING` 사용하여 중복 삽입 방지
- 논문 제목 기준 중복 제거 (`remove_duplicates()`)

---

## 📊 실제 수집 데이터

- **논문 개수**: 75개
- **PDF 파일**: 75개
- **메타데이터**: 75개 항목
- **목표 달성**: ✅ 50-100편 목표 달성 (75편)

---

## 🔗 유용한 링크

### 프로젝트 문서
- `docs/PRD/01_프로젝트_개요.md` - 프로젝트 전체 개요
- `docs/PRD/02_프로젝트_구조.md` - 폴더 구조
- `docs/PRD/05_로깅_시스템.md` - Logger 사용법
- `docs/PRD/06_실험_추적_관리.md` - 실험 폴더 구조
- `docs/PRD/10_기술_요구사항.md` - 기술 스택
- `docs/PRD/11_데이터베이스_설계.md` - 데이터베이스 설계
- `docs/PRD/13_RAG_시스템_설계.md` - RAG 시스템 설계
- `docs/실행_가이드.md` - 상세 실행 가이드
- `docs/test_results.md` - 테스트 결과

### 외부 문서
- [arXiv API](https://info.arxiv.org/help/api/index.html)
- [Langchain Document Loaders](https://python.langchain.com/docs/integrations/document_loaders/)
- [Langchain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [pgvector 문서](https://github.com/pgvector/pgvector)

---

## ✅ 다음 단계

데이터 파이프라인이 완성되었으므로, 다음 작업을 진행할 수 있습니다:

1. **RAG Retriever 구현**
   - `src/rag/retriever.py` 구현
   - PGVector를 사용한 유사도 검색
   - MMR (Maximal Marginal Relevance) 방식 적용

2. **추가 데이터 수집**
   - 더 많은 논문 수집 (목표: 100편 이상)
   - 다른 소스 추가 (IEEE, ACL 등)

3. **성능 최적화**
   - 배치 크기 조정
   - 인덱스 최적화
   - 쿼리 성능 개선

---

## 📞 문의

구현 관련 문의사항이 있으시면 담당자(박재홍)에게 연락해주세요.

---

**문서 작성 완료일**: 2025-10-31  
**작성자**: 박재홍

