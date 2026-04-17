"""
RAG Agent — Advanced retrieval pipeline for internal documents.

Pipeline: Query Rewrite → Query Expand → Retrieve → Rerank → Generate

Each stage is modular and logged independently for observability.
"""
import logging
from agents.llm_client import call_llm
from agents.vector_store import query_vectors
from agents.query_rewriter import rewrite_query
from agents.query_expander import expand_query
from agents.reranker import rerank_chunks
from ingestion.models import Document

logger = logging.getLogger(__name__)

# ── Stage 5: Generation Prompt ────────────────────────────────────────────────

GENERATE_SYSTEM_PROMPT = """You are a highly knowledgeable marine engineering AI assistant for MarineMind.

You answer questions based ONLY on the provided context from ship manuals, noon reports, and technical documents.

CITATION RULES (MANDATORY):
- Every factual statement MUST have an inline citation placed IMMEDIATELY after the sentence it supports.
- Use the citation format [doc1], [doc2], etc. matching the source labels provided.
- If a sentence draws from multiple sources, include all relevant citations: [doc1][doc3].
- Do NOT group citations at the end. They must appear inline throughout.
- If the context does not contain enough information, say so clearly — do NOT fabricate.
- Only cite sources that actually support the statement.

FORMATTING RULES (MANDATORY):
- Do NOT use markdown formatting. No **, ##, __, ``` or any markdown symbols.
- Use plain numbered lists (1. 2. 3.) or dash bullet points (- item) for structure.
- Use blank lines to separate sections.
- Use UPPERCASE or Title Case for section headings on their own line.
- Keep the response clean, professional, and easy to read.
- Be precise and technical — your audience is marine engineers.
"""


# ── Stage 3: Multi-Query Retrieval ────────────────────────────────────────────

def _retrieve_multi_query(
    rewritten_query: str,
    expanded_queries: list[str],
    candidates_per_query: int = 8,
) -> list[dict]:
    """
    Retrieve chunks using the rewritten query + all expanded queries.
    Deduplicates by chunk ID and merges scores (keeps the highest).
    
    Returns:
        Deduplicated list of candidate chunks.
    """
    all_queries = [rewritten_query] + expanded_queries
    seen_ids: dict[str, dict] = {}  # vec_id → chunk dict

    for q in all_queries:
        matches = query_vectors(q, top_k=candidates_per_query)
        for match in matches:
            vec_id = match["metadata"].get("text", "")[:80]  # use text prefix as dedup key
            if vec_id in seen_ids:
                # Keep the higher retrieval score
                if match["score"] > seen_ids[vec_id]["score"]:
                    seen_ids[vec_id] = match
            else:
                seen_ids[vec_id] = match

    candidates = list(seen_ids.values())
    logger.info(
        f"[Retrieve] {len(all_queries)} queries → "
        f"{len(candidates)} unique candidate chunks"
    )
    return candidates


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def run_rag_agent(user_query: str, top_k: int = 5) -> dict:
    """
    Execute the full advanced RAG pipeline:
      1. Query Rewrite  — optimize the query for retrieval
      2. Query Expand   — generate 3-5 related search variations
      3. Retrieve       — multi-query vector search with deduplication
      4. Rerank         — cross-encoder reranking, filter weak chunks
      5. Generate       — produce the final grounded answer
    
    Returns:
        dict with "answer", "sources", "citation_map", "agent",
        and "pipeline_debug" for observability.
    """
    pipeline_debug = {"original_query": user_query}

    # ── Stage 1: Query Rewrite ────────────────────────────────────────────
    logger.info(f"[RAG Pipeline] Stage 1 — Query Rewrite")
    rewritten = rewrite_query(user_query)
    pipeline_debug["rewritten_query"] = rewritten

    # ── Stage 2: Query Expand ─────────────────────────────────────────────
    logger.info(f"[RAG Pipeline] Stage 2 — Query Expand")
    expanded = expand_query(rewritten, max_expansions=4)
    pipeline_debug["expanded_queries"] = expanded

    # ── Stage 3: Retrieve ─────────────────────────────────────────────────
    logger.info(f"[RAG Pipeline] Stage 3 — Multi-Query Retrieve")
    candidates = _retrieve_multi_query(
        rewritten_query=rewritten,
        expanded_queries=expanded,
        candidates_per_query=8,
    )
    pipeline_debug["retrieved_count"] = len(candidates)
    pipeline_debug["retrieved_chunks"] = [
        {
            "source": c["metadata"].get("source", "?"),
            "score": round(c["score"], 4),
            "text_preview": c["text"][:120],
        }
        for c in candidates
    ]

    if not candidates:
        return {
            "answer": (
                "I couldn't find any relevant information in the uploaded documents. "
                "Please make sure relevant manuals or reports have been uploaded."
            ),
            "sources": [],
            "citation_map": {},
            "agent": "rag",
            "pipeline_debug": pipeline_debug,
        }

    # ── Stage 4: Rerank ───────────────────────────────────────────────────
    logger.info(f"[RAG Pipeline] Stage 4 — Rerank ({len(candidates)} candidates)")
    reranked = rerank_chunks(
        original_query=user_query,  # Score against ORIGINAL intent
        chunks=candidates,
        top_n=top_k,
        relevance_threshold=0.1,
    )
    pipeline_debug["reranked_count"] = len(reranked)
    pipeline_debug["reranked_chunks"] = [
        {
            "source": c["metadata"].get("source", "?"),
            "retrieval_score": round(c["score"], 4),
            "rerank_score": round(c.get("rerank_score", 0), 4),
            "text_preview": c["text"][:120],
        }
        for c in reranked
    ]

    # ── Stage 5: Generate ─────────────────────────────────────────────────
    logger.info(f"[RAG Pipeline] Stage 5 — Generate (context from {len(reranked)} chunks)")

    # Build context and citation map from reranked chunks
    context_parts = []
    sources = []
    citation_map = {}
    for i, chunk in enumerate(reranked, 1):
        source_info = chunk["metadata"].get("source", "Unknown")
        cite_key = f"doc{i}"
        context_parts.append(f"[{cite_key}: {source_info}]\n{chunk['text']}")
        source_entry = {
            "source": source_info,
            "score": round(chunk["score"], 4),
            "rerank_score": round(chunk.get("rerank_score", 0), 4),
            "document_id": chunk["metadata"].get("document_id", ""),
            "chunk_index": chunk["metadata"].get("chunk_index", ""),
            "chunk_text": chunk["text"],
            "page": chunk["metadata"].get("page", None),
            "type": "document",
        }
        sources.append(source_entry)
        citation_map[cite_key] = source_entry

    context = "\n\n---\n\n".join(context_parts)

    # Resolve document file URLs for citation links
    doc_ids = [v["document_id"] for v in citation_map.values() if v.get("document_id")]
    if doc_ids:
        docs = Document.objects.filter(id__in=doc_ids)
        doc_url_map = {
            str(d.id): d.file.url
            for d in docs
            if d.file and d.file.storage.exists(d.file.name)
        }
        for entry in citation_map.values():
            doc_id = entry.get("document_id", "")
            if doc_id and doc_id in doc_url_map:
                entry["url"] = doc_url_map[doc_id]

    # Citation reference guide for the LLM
    cite_guide = "\n".join(
        f"[{k}] = {v['source']}" for k, v in citation_map.items()
    )

    messages = [
        {"role": "system", "content": GENERATE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Context from documents:\n\n{context}\n\n---\n\n"
                f"Citation Reference:\n{cite_guide}\n\n---\n\n"
                f"Question: {user_query}"
            ),
        },
    ]

    answer = call_llm(messages, temperature=0.2, max_tokens=1024)

    logger.info(f"[RAG Pipeline] Complete. Answer length: {len(answer)} chars")

    return {
        "answer": answer,
        "sources": sources,
        "citation_map": citation_map,
        "agent": "rag",
        "pipeline_debug": pipeline_debug,
    }
