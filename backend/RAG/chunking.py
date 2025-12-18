from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
from typing import List, Literal, Optional, Any
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class DocumentChunker:
    """Super-chunker supporting recursive, semantic, hybrid, stats, and auto-tuning."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        strategy: Literal["recursive", "semantic", "hybrid"] = "recursive",
        auto_tune: bool = True,
        embedding: Optional[Any] = None,
        similarity_threshold: float = 0.8
    ):
        """
        Args:
            chunk_size (int): Max characters per chunk (for recursive).
            chunk_overlap (int): Overlap between chunks (for recursive).
            strategy (str): "recursive", "semantic", or "hybrid".
            auto_tune (bool): Auto-adjust chunk size for large docs.
            embedding (Any): Pre-initialized embedding model (for semantic/hybrid).
            similarity_threshold (float): Threshold for semantic boundaries.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        self.auto_tune = auto_tune
        self.embedding = embedding
        self.similarity_threshold = similarity_threshold

        if strategy == "recursive":
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ".", " ", ""]
            )
        elif strategy in ["semantic", "hybrid"]:
            if not embedding:
                raise ValueError("Embedding model must be provided for semantic/hybrid strategies.")
            self.splitter = SemanticChunker(embedding, breakpoint_threshold_type="percentile")
        else:
            raise ValueError("Unsupported strategy. Use 'recursive', 'semantic', or 'hybrid'.")

    def _auto_tune(self, docs: List[Document]):
        """Auto adjust chunk size if docs are very large (recursive only)."""
        if self.strategy != "recursive":
            return
        total_chars = sum(len(doc.page_content) for doc in docs)
        if self.auto_tune and total_chars > 200_000:  # ~200 pages
            new_size = min(2000, self.chunk_size * 2)
            logging.info(f"Large doc detected ({total_chars} chars). Auto-tuning chunk size → {new_size}")
            self.splitter._chunk_size = new_size

    def chunk_documents(self, docs: List[Document]) -> List[Document]:
        """Split loaded documents into chunks."""
        logging.info(f"Chunking {len(docs)} documents with strategy={self.strategy}...")
        self._auto_tune(docs)

        if self.strategy == "hybrid":
            recursive_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            docs = recursive_splitter.split_documents(docs)
            logging.info(f"Hybrid step1 (recursive): {len(docs)} chunks")

            chunks = self.splitter.split_documents(docs)
            logging.info(f"Hybrid step2 (semantic): {len(chunks)} chunks")
        else:
            chunks = self.splitter.split_documents(docs)

        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i + 1

        logging.info(f"Final: {len(chunks)} chunks created.")
        return chunks

    def preview_chunks(self, chunks: List[Document], n: int = 2):
        """Preview first n chunks for debugging."""
        for i, chunk in enumerate(chunks[:n]):
            logging.info(f"\n--- Chunk {i+1} ---\n{chunk.page_content[:300]}...\n")

    def summarize_chunks(self, chunks: List[Document]):
        """Print stats about chunk sizes."""
        lengths = [len(c.page_content) for c in chunks]
        if not lengths:
            logging.info("No chunks to summarize.")
            return
        logging.info(
            f"Chunks: {len(chunks)} | Avg size: {sum(lengths)//len(lengths)} "
            f"| Min: {min(lengths)} | Max: {max(lengths)}"
        )