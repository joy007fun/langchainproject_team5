# src/tools/arxiv_handler.py
"""
arXiv 논문 자동 저장 모듈

웹 검색 결과에서 arXiv 논문을 자동으로 다운로드하고 DB에 저장:
- arXiv URL 파싱 및 메타데이터 추출
- PDF 다운로드 (data/raw 폴더)
- papers 테이블 저장
- 고품질 청킹 (PaperDocumentLoader 활용)
- 임베딩 생성 및 pgvector 저장
"""

# ==================== Import ==================== #
import os
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import psycopg2
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector

# PaperDocumentLoader import
import sys
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
from src.data.document_loader import PaperDocumentLoader

# PDF 텍스트 추출
try:
    from pypdf import PdfReader
    PDF_EXTRACTOR = "pypdf"
except ImportError:
    try:
        import PyPDF2
        PDF_EXTRACTOR = "PyPDF2"
    except ImportError:
        try:
            import pdfplumber
            PDF_EXTRACTOR = "pdfplumber"
        except ImportError:
            PDF_EXTRACTOR = None


# ==================== arXiv 논문 처리 클래스 ==================== #
class ArxivPaperHandler:
    """
    arXiv 논문 자동 저장 핸들러

    웹 검색 결과에서 arXiv 논문을 자동으로 처리:
    1. arXiv URL 파싱
    2. 메타데이터 추출 (arXiv API)
    3. PDF 다운로드
    4. PDF 텍스트 추출
    5. papers 테이블 저장
    6. 임베딩 생성 및 pgvector 저장
    """

    def __init__(self, data_dir: str = "data/raw/pdfs", logger=None):
        """
        초기화

        Args:
            data_dir: PDF 저장 폴더
            logger: Logger 인스턴스 (선택)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

        # DB 연결 정보
        self.db_url = os.getenv("DATABASE_URL")

        if self.logger:
            self.logger.write(f"ArxivPaperHandler 초기화: 저장 폴더={self.data_dir}")
            self.logger.write(f"PDF 추출기: {PDF_EXTRACTOR}")

    # ============================================================ #
    #                     1. arXiv URL 파싱                        #
    # ============================================================ #
    def parse_arxiv_url(self, url: str) -> Optional[str]:
        """
        arXiv URL에서 논문 ID 추출

        Args:
            url: arXiv URL

        Returns:
            arxiv_id (예: "2301.12345") 또는 None

        지원 형식:
        - https://arxiv.org/abs/2301.12345
        - https://arxiv.org/pdf/2301.12345.pdf
        - https://arxiv.org/abs/2301.12345v1
        """
        patterns = [
            r'arxiv\.org/abs/(\d{4}\.\d{4,5})',
            r'arxiv\.org/pdf/(\d{4}\.\d{4,5})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                arxiv_id = match.group(1)
                if self.logger:
                    self.logger.write(f"arXiv ID 추출 성공: {arxiv_id}")
                return arxiv_id

        if self.logger:
            self.logger.write(f"arXiv URL 파싱 실패: {url}")
        return None

    # ============================================================ #
    #                  2. arXiv 메타데이터 추출                     #
    # ============================================================ #
    def fetch_arxiv_metadata(self, arxiv_id: str) -> Optional[Dict]:
        """
        arXiv API에서 논문 메타데이터 추출

        Args:
            arxiv_id: arXiv ID (예: "2301.12345")

        Returns:
            메타데이터 딕셔너리 또는 None
        """
        api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"

        try:
            if self.logger:
                self.logger.write(f"arXiv API 호출: {arxiv_id}")

            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            # XML 파싱 (간단한 정규식 사용)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)

            # Namespace 처리
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }

            entry = root.find('atom:entry', ns)
            if entry is None:
                if self.logger:
                    self.logger.write(f"논문을 찾을 수 없음: {arxiv_id}")
                return None

            # 메타데이터 추출
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')

            # 저자 추출
            authors = []
            for author in entry.findall('atom:author', ns):
                name = author.find('atom:name', ns)
                if name is not None:
                    authors.append(name.text)

            # 초록 추출
            summary = entry.find('atom:summary', ns)
            abstract = summary.text.strip().replace('\n', ' ') if summary is not None else ""

            # 발행일 추출
            published = entry.find('atom:published', ns)
            publish_date = published.text.split('T')[0] if published is not None else None

            metadata = {
                'arxiv_id': arxiv_id,
                'title': title,
                'authors': ', '.join(authors),
                'abstract': abstract,
                'publish_date': publish_date,
                'url': f"https://arxiv.org/abs/{arxiv_id}"
            }

            if self.logger:
                self.logger.write(f"메타데이터 추출 성공: {title}")

            return metadata

        except Exception as e:
            if self.logger:
                self.logger.write(f"메타데이터 추출 실패: {e}", print_error=True)
            return None

    # ============================================================ #
    #                       3. PDF 다운로드                         #
    # ============================================================ #
    def download_pdf(self, arxiv_id: str) -> Optional[Path]:
        """
        arXiv PDF 다운로드

        Args:
            arxiv_id: arXiv ID

        Returns:
            PDF 파일 경로 또는 None
        """
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = self.data_dir / f"{arxiv_id}.pdf"

        # 이미 다운로드된 경우
        if pdf_path.exists():
            if self.logger:
                self.logger.write(f"PDF 이미 존재: {pdf_path}")
            return pdf_path

        try:
            if self.logger:
                self.logger.write(f"PDF 다운로드 시작: {pdf_url}")

            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()

            # PDF 저장
            with open(pdf_path, 'wb') as f:
                f.write(response.content)

            if self.logger:
                self.logger.write(f"PDF 다운로드 완료: {pdf_path} ({len(response.content)} bytes)")

            return pdf_path

        except Exception as e:
            if self.logger:
                self.logger.write(f"PDF 다운로드 실패: {e}", print_error=True)
            return None

    # ============================================================ #
    #                    4. PDF 텍스트 추출                         #
    # ============================================================ #
    def extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        PDF 파일에서 텍스트 추출

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            추출된 텍스트 또는 None
        """
        if not pdf_path.exists():
            if self.logger:
                self.logger.write(f"PDF 파일 없음: {pdf_path}", print_error=True)
            return None

        try:
            if PDF_EXTRACTOR == "pypdf":
                return self._extract_with_pypdf(pdf_path)
            elif PDF_EXTRACTOR == "PyPDF2":
                return self._extract_with_pypdf2(pdf_path)
            elif PDF_EXTRACTOR == "pdfplumber":
                return self._extract_with_pdfplumber(pdf_path)
            else:
                if self.logger:
                    self.logger.write("PDF 추출 라이브러리 없음 (pypdf 또는 pdfplumber 설치 필요)", print_error=True)
                return None

        except Exception as e:
            if self.logger:
                self.logger.write(f"PDF 텍스트 추출 실패: {e}", print_error=True)
            return None

    def _extract_with_pypdf(self, pdf_path: Path) -> str:
        """pypdf로 텍스트 추출 (최신 버전)"""
        from pypdf import PdfReader

        text = []
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text())

        full_text = '\n'.join(text)

        if self.logger:
            self.logger.write(f"pypdf 텍스트 추출 완료: {len(full_text)} 글자")

        return full_text

    def _extract_with_pypdf2(self, pdf_path: Path) -> str:
        """PyPDF2로 텍스트 추출"""
        import PyPDF2

        text = []
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text())

        full_text = '\n'.join(text)

        if self.logger:
            self.logger.write(f"PyPDF2 텍스트 추출 완료: {len(full_text)} 글자")

        return full_text

    def _extract_with_pdfplumber(self, pdf_path: Path) -> str:
        """pdfplumber로 텍스트 추출"""
        import pdfplumber

        text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text())

        full_text = '\n'.join(text)

        if self.logger:
            self.logger.write(f"pdfplumber 텍스트 추출 완료: {len(full_text)} 글자")

        return full_text

    # ============================================================ #
    #                   5. papers 테이블 저장                       #
    # ============================================================ #
    def save_to_papers_table(self, metadata: Dict) -> Optional[int]:
        """
        papers 테이블에 논문 저장

        Args:
            metadata: 논문 메타데이터

        Returns:
            paper_id 또는 None
        """
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()

            # 중복 확인 (arxiv_id 또는 url로 확인)
            cursor.execute(
                "SELECT paper_id FROM papers WHERE arxiv_id = %s OR url = %s",
                (metadata['arxiv_id'], metadata['url'])
            )
            existing = cursor.fetchone()

            if existing:
                paper_id = existing[0]
                if self.logger:
                    self.logger.write(f"논문 이미 존재: paper_id={paper_id}")
                cursor.close()
                conn.close()
                return paper_id

            # 새 논문 저장
            query = """
            INSERT INTO papers (arxiv_id, title, authors, abstract, publish_date, url, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING paper_id
            """

            cursor.execute(query, (
                metadata['arxiv_id'],
                metadata['title'],
                metadata['authors'],
                metadata['abstract'],
                metadata['publish_date'],
                metadata['url'],
                datetime.now()
            ))

            paper_id = cursor.fetchone()[0]
            conn.commit()

            if self.logger:
                self.logger.write(f"papers 테이블 저장 완료: paper_id={paper_id}")

            cursor.close()
            conn.close()

            return paper_id

        except Exception as e:
            if self.logger:
                self.logger.write(f"papers 테이블 저장 실패: {e}", print_error=True)
            return None

    # ============================================================ #
    #              6. 임베딩 생성 및 pgvector 저장                  #
    # ============================================================ #
    def save_to_pgvector(self, paper_id: int, arxiv_id: str, pdf_path: Path, metadata: Optional[Dict] = None) -> bool:
        """
        PaperDocumentLoader를 사용하여 고품질 청킹 후 pgvector에 저장

        Args:
            paper_id: papers 테이블의 paper_id
            arxiv_id: arXiv ID
            pdf_path: PDF 파일 경로
            metadata: 추가 메타데이터

        Returns:
            성공 여부
        """
        try:
            # PaperDocumentLoader 초기화 (run_full_pipeline과 동일한 설정)
            loader = PaperDocumentLoader(
                chunk_size=1000,
                chunk_overlap=200
            )

            if self.logger:
                self.logger.write(f"PaperDocumentLoader 초기화 완료 (chunk_size=1000, overlap=200)")

            # 메타데이터 준비
            if metadata is None:
                metadata = {}
            metadata['paper_id'] = paper_id
            metadata['arxiv_id'] = arxiv_id

            # load_and_split: 저작권 필터링 + RecursiveCharacterTextSplitter 청킹
            documents = loader.load_and_split(pdf_path, metadata)

            if self.logger:
                self.logger.write(f"고품질 청킹 완료: {len(documents)}개 청크 (저작권 필터링 적용)")

            # 중복 제거 (load_embeddings.py와 동일)
            documents = self._deduplicate_chunks(documents)

            if self.logger:
                self.logger.write(f"중복 제거 후: {len(documents)}개 청크")

            # PGVector에 저장
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            vectorstore = PGVector(
                collection_name="paper_chunks",
                embeddings=embeddings,
                connection=self.db_url,
                use_jsonb=True
            )

            if self.logger:
                self.logger.write(f"pgvector 저장 시작: {len(documents)}개 청크")

            vectorstore.add_documents(documents)

            if self.logger:
                self.logger.write(f"pgvector 저장 완료: {len(documents)}개 청크")

            return True

        except Exception as e:
            if self.logger:
                self.logger.write(f"pgvector 저장 실패: {e}", print_error=True)
            return False

    def _deduplicate_chunks(self, chunks: List[Document]) -> List[Document]:
        """
        중복 청크 제거 (load_embeddings.py의 deduplicate_chunks와 동일)

        Args:
            chunks: 청크 리스트

        Returns:
            중복이 제거된 청크 리스트
        """
        seen_contents = set()
        unique_chunks = []
        duplicate_count = 0

        for chunk in chunks:
            # 내용 해시 생성 (page_content 기준)
            content_hash = hash(chunk.page_content)

            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_chunks.append(chunk)
            else:
                duplicate_count += 1

        if duplicate_count > 0 and self.logger:
            self.logger.write(f"   ℹ️  {duplicate_count}개 중복 청크 제거됨")

        return unique_chunks

    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """
        [DEPRECATED] 단순 청킹 방식 (overlap 없음)

        이 메서드는 더 이상 사용되지 않습니다.
        대신 save_to_pgvector()가 PaperDocumentLoader를 사용합니다.

        Args:
            text: 전체 텍스트
            chunk_size: 청크 크기 (글자 수)

        Returns:
            청크 리스트
        """
        # 간단한 청킹 (overlap 없음) - DEPRECATED
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            if chunk.strip():  # 빈 청크 제외
                chunks.append(chunk)

        return chunks

    # ============================================================ #
    #                      전체 프로세스 실행                        #
    # ============================================================ #
    def process_arxiv_paper(self, url: str) -> bool:
        """
        arXiv 논문 전체 처리 프로세스 (고품질 청킹)

        Args:
            url: arXiv URL

        Returns:
            성공 여부
        """
        if self.logger:
            self.logger.write(f"arXiv 논문 처리 시작: {url}")

        # 1. URL 파싱
        arxiv_id = self.parse_arxiv_url(url)
        if not arxiv_id:
            return False

        # 2. 메타데이터 추출
        metadata = self.fetch_arxiv_metadata(arxiv_id)
        if not metadata:
            return False

        # 3. PDF 다운로드
        pdf_path = self.download_pdf(arxiv_id)
        if not pdf_path:
            return False

        # 4. papers 테이블 저장
        paper_id = self.save_to_papers_table(metadata)
        if not paper_id:
            return False

        # 5. pgvector 저장 (고품질 청킹: PaperDocumentLoader 사용)
        # 추가 메타데이터 준비
        extra_metadata = {
            'title': metadata.get('title'),
            'authors': metadata.get('authors'),
            'publish_date': metadata.get('publish_date'),
            'url': metadata.get('url')
        }

        success = self.save_to_pgvector(paper_id, arxiv_id, pdf_path, extra_metadata)

        if success and self.logger:
            self.logger.write(f"arXiv 논문 처리 완료: {arxiv_id} (paper_id={paper_id})")
            self.logger.write(f"고품질 청킹 적용: RecursiveCharacterTextSplitter + 저작권 필터링 + 중복 제거")

        return success
