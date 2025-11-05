from __future__ import annotations

"""PDF → LangChain Document 변환 및 청크 분할 유틸.

한글 주석과 가독성 중심 구현.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class PaperDocumentLoader:
    """논문 PDF를 LangChain Document로 변환하고 분할합니다."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def load_pdf(self, pdf_path: str | Path, metadata: Optional[Dict] = None) -> List[Document]:
        """PDF 파일을 로드하여 Document 리스트를 반환합니다."""

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        # 저작권 페이지 필터링 (첫 페이지가 메타데이터만 있는 경우)
        filtered_docs = []
        for doc in documents:
            content = doc.page_content.lower()
            content_length = len(doc.page_content)

            # 저작권 페이지 판별 조건
            is_copyright_page = (
                ("copyright" in content or "permission" in content) and
                content_length < 1000
            )

            if not is_copyright_page:
                filtered_docs.append(doc)

        # 필터링 결과가 없으면 원본 사용 (모든 페이지가 저작권인 경우 방지)
        if not filtered_docs:
            filtered_docs = documents

        if metadata:
            for d in filtered_docs:
                d.metadata.update(metadata)
        return filtered_docs

    def load_and_split(self, pdf_path: str | Path, metadata: Optional[Dict] = None) -> List[Document]:
        """PDF를 로드하고 청크로 분할합니다."""

        docs = self.load_pdf(pdf_path, metadata)
        chunks = self.text_splitter.split_documents(docs)
        for i, ch in enumerate(chunks):
            ch.metadata["chunk_id"] = i
            ch.metadata["chunk_index"] = i  # chunk_index 추가 (pgvector 검색용)
        return chunks

    def load_all_pdfs(self, pdf_dir: str | Path, metadata_json_path: str | Path) -> List[Document]:
        """디렉토리의 모든 PDF를 로드하고 분할합니다."""

        pdf_dir = Path(pdf_dir)
        with Path(metadata_json_path).open("r", encoding="utf-8") as f:
            papers_metadata = json.load(f)

        id_to_meta: Dict[str, Dict] = {}
        for p in papers_metadata:
            arxiv_id = p.get("entry_id", "").split("/")[-1]
            id_to_meta[arxiv_id] = p

        all_chunks: List[Document] = []
        for filename in os.listdir(pdf_dir):
            if not filename.endswith(".pdf"):
                continue
            arxiv_id = filename[:-4]
            meta = id_to_meta.get(arxiv_id, {})
            try:
                chunks = self.load_and_split(pdf_dir / filename, meta)
                all_chunks.extend(chunks)
            except Exception as e:  # noqa: BLE001
                # 로더 오류 시 해당 파일은 건너뜁니다.
                continue
        return all_chunks


