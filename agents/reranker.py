"""
Reranker — Reranks retrieved chunks by semantic relevance to the original query.

Stage 4 of the RAG pipeline: Query Rewrite → Query Expand → Retrieve → Rerank → Generate

Uses a cross-encoder model for accurate pairwise relevance scoring.
Falls back to embedding cosine similarity if cross-encoder is unavailable.
"""
import logging
from sentence_transformers import CrossEncoder
from django.conf import settings

logger = logging.getLogger(__name__)

_reranker_model = None


def get_reranker_model() -> CrossEncoder:
    """Lazy-load the cross-encoder reranker model (singleton)."""
    global _reranker_model
    if _reranker_model is None:
        model_name = getattr(settings, 'RERANKER_MODEL_NAME', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        logger.info(f"[Reranker] Loading cross-encoder model: {model_name}")
        _reranker_model = CrossEncoder(model_name)
        logger.info("[Reranker] Model loaded successfully")
    return _reranker_model


def rerank_chunks(
    original_query: str,
    chunks: list[dict],
    top_n: int = 5,
    relevance_threshold: float = 0.1,
) -> list[dict]:
    """
    Rerank retrieved chunks based on semantic relevance to the original query.
    
    Uses a cross-encoder model that scores (query, passage) pairs for relevance.
    Filters out low-relevance chunks and returns the top N.
    
    Args:
        original_query: The user's original query (NOT the rewritten one).
        chunks: List of chunk dicts, each with "text", "score", "metadata".
        top_n: Maximum number of chunks to return after reranking.
        relevance_threshold: Minimum reranker score to keep a chunk.
    
    Returns:
        Reranked list of chunk dicts (highest relevance first), each with an
        added "rerank_score" field.
    """
    if not chunks:
        return []

    try:
        model = get_reranker_model()

        # Build query-passage pairs for the cross-encoder
        pairs = [(original_query, chunk["text"]) for chunk in chunks]

        # Score all pairs
        scores = model.predict(pairs)

        # Attach rerank scores
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        # Sort by rerank score descending
        ranked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)

        # Filter by relevance threshold
        filtered = [c for c in ranked if c["rerank_score"] >= relevance_threshold]

        # If threshold filtering removed everything, keep the top result at minimum
        if not filtered and ranked:
            filtered = [ranked[0]]

        result = filtered[:top_n]

        logger.info(
            f"[Reranker] {len(chunks)} candidates → {len(result)} after reranking "
            f"(threshold={relevance_threshold})"
        )
        for i, c in enumerate(result, 1):
            src = c["metadata"].get("source", "?")
            logger.info(
                f"  [{i}] score={c['rerank_score']:.4f} "
                f"retrieval_score={c['score']:.4f} "
                f"source={src}"
            )

        return result

    except Exception as e:
        logger.error(f"[Reranker] Error: {e}. Falling back to retrieval-order ranking.")
        # Fallback: return chunks sorted by original retrieval score
        return sorted(chunks, key=lambda c: c["score"], reverse=True)[:top_n]
