from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from typing import List, Optional, Any, Dict
import logging
import os
import pickle
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class VectorStoreManager:
    """Advanced FAISS VectorStore manager with hybrid search, filtering, and index utilities."""

    def __init__(self, embedding_model: Any, index_path: str = "faiss_index"):
        """
        Args:
            embedding_model (Any): An embedding model instance (e.g., EmbeddingGenerator).
            index_path (str): Path to store FAISS index.
        """
        self.embedding_model = embedding_model
        self.index_path = index_path
        self.vectorstore: Optional[FAISS] = None


    def build_from_documents(self, docs: List[Document]):
        """Create a new FAISS index from a list of documents."""
        logging.info("Building FAISS index from documents...")
        self.vectorstore = FAISS.from_documents(docs, self.embedding_model.embedding_model)
        logging.info(f"FAISS index built with {len(docs)} documents.")

    def add_documents(self, docs: List[Document]):
        """Add more documents to an existing FAISS index."""
        if not self.vectorstore:
            raise ValueError("No FAISS index found. Build it first.")
        logging.info(f"Adding {len(docs)} new documents to FAISS index...")
        self.vectorstore.add_documents(docs)

    def similarity_search(self, query: str, k: int = 5, score_threshold: Optional[float] = None,
                          filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Search for top-k similar documents given a query, with optional score threshold and metadata filters.

        Args:
            query (str): Search query.
            k (int): Number of results.
            score_threshold (float): Minimum cosine similarity score.
            filters (dict): Metadata filters (e.g., {"year": 2022})
        """
        if not self.vectorstore:
            raise ValueError("FAISS index not initialized. Build or load it first.")

        logging.info(f"Performing similarity search for query='{query}' (top {k})")

        results = self.vectorstore.similarity_search_with_score(query, k=k)
        filtered_results = []

        for doc, score in results:
            if score_threshold and score < score_threshold:
                continue
            if filters:
                if not all(doc.metadata.get(k) == v for k, v in filters.items()):
                    continue
            filtered_results.append(doc)

        return filtered_results


    def save_index(self):
        """Save FAISS index to disk with metadata."""
        if not self.vectorstore:
            raise ValueError("No FAISS index to save.")
        logging.info(f"Saving FAISS index to {self.index_path}...")
        self.vectorstore.save_local(self.index_path)
        with open(os.path.join(self.index_path, "metadata.pkl"), "wb") as f:
            pickle.dump(self.vectorstore.index_to_docstore_id, f)
        logging.info("FAISS index saved successfully.")

    def load_index(self):
        """Load FAISS index from disk."""
        logging.info(f"Loading FAISS index from {self.index_path}...")
        self.vectorstore = FAISS.load_local(
            self.index_path, 
            self.embedding_model.embedding_model,
            allow_dangerous_deserialization=True
        )
        with open(os.path.join(self.index_path, "metadata.pkl"), "rb") as f:
            self.vectorstore.index_to_docstore_id = pickle.load(f)
        logging.info("FAISS index loaded successfully.")


    def get_index_stats(self) -> Dict[str, Any]:
        """Return index stats like size, embedding dim, and memory usage."""
        if not self.vectorstore:
            raise ValueError("FAISS index not initialized.")

        index = self.vectorstore.index
        stats = {
            "total_docs": index.ntotal,
            "embedding_dim": index.d,
            "memory_estimate_MB": index.ntotal * index.d * 4 / 1e6
        }
        logging.info(f"Index stats: {stats}")
        return stats

    def delete_index(self):
        """Delete FAISS index from memory and disk."""
        if os.path.exists(self.index_path):
            logging.info(f"Deleting FAISS index from {self.index_path}...")
            for file in os.listdir(self.index_path):
                os.remove(os.path.join(self.index_path, file))
            os.rmdir(self.index_path)
        self.vectorstore = None
        logging.info("FAISS index deleted successfully.")