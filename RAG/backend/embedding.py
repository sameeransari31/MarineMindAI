from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from typing import List, Optional, Dict, Any, Tuple
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class EmbeddingGenerator:
    """Advanced embedding generator with batching, async, hybrid embeddings, OOV handling, and logging stats."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        device: Optional[str] = None,
        normalize: bool = False,
        batch_size: int = 32,
        use_cache: bool = False,
        hybrid_model_name: Optional[str] = None
    ):
        """
        Args:
            model_name (str): Primary HF model for embeddings.
            device (str): "cpu" or "cuda".
            normalize (bool): Normalize embeddings.
            batch_size (int): Docs per batch.
            use_cache (bool): Cache embeddings in memory.
            hybrid_model_name (str): Optional secondary HF model for hybrid embeddings.
        """
        logging.info(f"Loading primary HF embeddings: {model_name} (device={device or 'default'})")
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device or "cpu"},
            encode_kwargs={"normalize_embeddings": normalize, "truncation": True, "padding": True}
        )
        self.hybrid_embedding_model = None
        if hybrid_model_name:
            logging.info(f"Loading secondary HF embeddings for hybrid: {hybrid_model_name}")
            self.hybrid_embedding_model = HuggingFaceEmbeddings(
                model_name=hybrid_model_name,
                model_kwargs={"device": device or "cpu"},
                encode_kwargs={"normalize_embeddings": normalize, "truncation": True, "padding": True}
            )

        self.batch_size = batch_size
        self.use_cache = use_cache
        self._cache: Dict[str, List[float]] = {}

    async def _embed_batch_async(self, texts: List[str], docs: List[Document], return_metadata: bool) -> List[Any]:
        """Embed a batch asynchronously using ThreadPoolExecutor."""
        loop = asyncio.get_running_loop()
        batch_embeddings = await loop.run_in_executor(
            ThreadPoolExecutor(),
            self._embed_batch_sync,
            texts,
            docs,
            return_metadata
        )
        return batch_embeddings

    def _embed_batch_sync(self, texts: List[str], docs: List[Document], return_metadata: bool) -> List[Any]:
        """Sync embedding for a batch, with cache and hybrid option."""
        embeddings = []
        batch_embeddings_primary = []

        for text, doc in zip(texts, docs):
            if self.use_cache and text in self._cache:
                emb = self._cache[text]
            else:
                emb = self.embedding_model.embed_documents([text])[0]
                if self.use_cache:
                    self._cache[text] = emb
            batch_embeddings_primary.append(emb)

        if self.hybrid_embedding_model:
            batch_embeddings_secondary = [self.hybrid_embedding_model.embed_documents([text])[0] for text in texts]
            batch_embeddings = [
                [(p + s)/2 for p, s in zip(p_emb, s_emb)]
                for p_emb, s_emb in zip(batch_embeddings_primary, batch_embeddings_secondary)
            ]
        else:
            batch_embeddings = batch_embeddings_primary

        if return_metadata:
            embeddings.extend([(emb, doc.metadata) for emb, doc in zip(batch_embeddings, docs)])
        else:
            embeddings.extend(batch_embeddings)

        return embeddings

    def embed_documents(self, docs: List[Document], return_metadata: bool = False) -> List[Any]:
        """Embed documents with batching, async, and optional hybrid embeddings."""
        total_docs = len(docs)
        logging.info(f"Embedding {total_docs} document chunks with batch_size={self.batch_size}...")

        all_embeddings = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for i in range(0, total_docs, self.batch_size):
            batch_docs = docs[i:i+self.batch_size]
            texts = [doc.page_content for doc in batch_docs]
            batch_embeddings = loop.run_until_complete(self._embed_batch_async(texts, batch_docs, return_metadata))
            all_embeddings.extend(batch_embeddings)

        loop.close()
        logging.info("Document embeddings generated successfully.")
        self._log_stats(all_embeddings)
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """Embed a user query."""
        logging.info("Embedding user query...")
        emb_primary = self.embedding_model.embed_query(query)
        if self.hybrid_embedding_model:
            emb_secondary = self.hybrid_embedding_model.embed_query(query)
            emb = [(p+s)/2 for p, s in zip(emb_primary, emb_secondary)]
            return emb
        return emb_primary

    def clear_cache(self):
        """Clear in-memory embedding cache."""
        self._cache = {}
        logging.info("Embedding cache cleared.")

    def change_model(self, new_model_name: str, device: Optional[str] = None):
        """Switch primary model at runtime."""
        logging.info(f"Switching embedding model to {new_model_name}")
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=new_model_name,
            model_kwargs={"device": device or "cpu"}
        )
        self.clear_cache()

    def _log_stats(self, embeddings: List[Any]):
        """Log stats about embeddings."""
        lengths = [len(e[0]) if isinstance(e, tuple) else len(e) for e in embeddings]
        if lengths:
            logging.info(f"Embeddings: count={len(lengths)}, avg_len={sum(lengths)//len(lengths)}, min_len={min(lengths)}, max_len={max(lengths)}")