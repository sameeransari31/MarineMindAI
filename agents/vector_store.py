"""
Embeddings & Vector Store utilities — Pinecone integration with sentence-transformers.
"""
import logging
import hashlib
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from django.conf import settings

logger = logging.getLogger(__name__)

_embedding_model = None
_pinecone_index = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        existing = [idx.name for idx in pc.list_indexes()]
        if settings.PINECONE_INDEX_NAME not in existing:
            from pinecone import ServerlessSpec
            pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=settings.PINECONE_DIMENSION,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1'),
            )
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


def upsert_vectors(chunks: list[dict]):
    """
    Upsert document chunks to Pinecone.
    
    Each chunk dict should have:
        - "text": str
        - "metadata": dict with source, page, document_id, etc.
    """
    index = get_pinecone_index()
    texts = [c["text"] for c in chunks]
    embeddings = generate_embeddings(texts)

    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vec_id = hashlib.sha256(
            f"{chunk['metadata'].get('document_id', '')}_chunk_{i}_{chunk['text'][:50]}".encode()
        ).hexdigest()[:64]
        metadata = {**chunk["metadata"], "text": chunk["text"][:1000]}
        vectors.append({
            "id": vec_id,
            "values": embedding,
            "metadata": metadata,
        })

    # Upsert in batches of 100
    batch_size = 100
    for start in range(0, len(vectors), batch_size):
        batch = vectors[start:start + batch_size]
        index.upsert(vectors=batch)
        logger.info(f"Upserted batch {start // batch_size + 1} ({len(batch)} vectors)")


def query_vectors(query_text: str, top_k: int = 5, filter_dict: dict = None) -> list[dict]:
    """
    Query Pinecone for the most relevant chunks.
    
    Returns list of dicts with "text", "score", and "metadata".
    """
    index = get_pinecone_index()
    query_embedding = generate_embeddings([query_text])[0]

    kwargs = {
        "vector": query_embedding,
        "top_k": top_k,
        "include_metadata": True,
    }
    if filter_dict:
        kwargs["filter"] = filter_dict

    results = index.query(**kwargs)

    matches = []
    for match in results.get("matches", []):
        matches.append({
            "text": match["metadata"].get("text", ""),
            "score": match["score"],
            "metadata": match["metadata"],
        })
    return matches


def delete_vectors_by_document(document_id: str) -> int:
    """
    Delete all vectors belonging to a specific document from Pinecone.

    Uses metadata filtering to find matching vector IDs, then deletes them
    in batches.  Returns the number of vectors deleted.
    """
    index = get_pinecone_index()
    deleted = 0

    # Use a dummy query vector (zeros) to list vectors with matching metadata
    dummy_vector = [0.0] * settings.PINECONE_DIMENSION
    batch_size = 100

    while True:
        results = index.query(
            vector=dummy_vector,
            top_k=batch_size,
            include_metadata=False,
            filter={"document_id": {"$eq": document_id}},
        )
        ids = [m["id"] for m in results.get("matches", [])]
        if not ids:
            break
        index.delete(ids=ids)
        deleted += len(ids)
        logger.info(f"Deleted {len(ids)} vectors for document {document_id}")

    logger.info(f"Total vectors deleted for document {document_id}: {deleted}")
    return deleted
