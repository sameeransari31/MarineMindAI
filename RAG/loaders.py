from langchain_community.document_loaders import UnstructuredPDFLoader, UnstructuredWordDocumentLoader
from typing import List
import logging
import os


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class DocumentLoader:
    """Advanced loader supporting PDF & DOCX with optional text cleaning and logging."""

    def __init__(self, clean: bool = True):
        self.clean = clean

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text by removing extra whitespace and normalizing line breaks."""
        return ' '.join(text.split())

    def load_pdf(self, path: str) -> List:
        if not os.path.exists(path):
            raise FileNotFoundError(f"PDF file not found: {path}")
        logging.info(f"Loading PDF: {path}")
        loader = UnstructuredPDFLoader(path)
        docs = loader.load()
        logging.info(f"Loaded {len(docs)} pages from PDF")
        if self.clean:
            for doc in docs:
                doc.page_content = self._clean_text(doc.page_content)
        return docs

    def load_docx(self, path: str) -> List:
        if not os.path.exists(path):
            raise FileNotFoundError(f"DOCX file not found: {path}")
        logging.info(f"Loading DOCX: {path}")
        loader = UnstructuredWordDocumentLoader(path)
        docs = loader.load()
        logging.info(f"Loaded {len(docs)} pages from DOCX")
        if self.clean:
            for doc in docs:
                doc.page_content = self._clean_text(doc.page_content)
        return docs

    def load_document(self, path: str) -> List:
        ext = path.lower().split('.')[-1]
        if ext == "pdf":
            return self.load_pdf(path)
        elif ext == "docx":
            return self.load_docx(path)
        else:
            raise ValueError("Unsupported file format. Only PDF and DOCX are supported.")
