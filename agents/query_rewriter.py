"""
Query Rewriter — Rewrites user queries into clearer, retrieval-optimized versions.

Stage 1 of the RAG pipeline: Query Rewrite → Query Expand → Retrieve → Rerank → Generate
"""
import json
import logging
from agents.llm_client import call_llm

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """You are a query rewriting assistant for a maritime engineering knowledge base.

Your job is to take a user's raw query and rewrite it into a single, clear, retrieval-optimized query.

Rules:
- Preserve the user's original intent exactly.
- Fix spelling errors, vague phrasing, and ambiguity.
- Expand abbreviations where helpful (e.g., "ME" → "Main Engine", "FO" → "Fuel Oil").
- Add relevant maritime domain context if the query is too short or vague.
- Output ONLY the rewritten query as plain text, nothing else.
- Do NOT add explanations, prefixes, or quotes.
- If the query is already clear and specific, return it as-is with minimal changes.
- Keep it as a single sentence or question."""


def rewrite_query(original_query: str) -> str:
    """
    Rewrite a user query into a clearer, retrieval-optimized version.
    
    Args:
        original_query: The raw user query.
    
    Returns:
        The rewritten query string.
    """
    messages = [
        {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Rewrite this query for better retrieval:\n\n{original_query}"},
    ]

    try:
        rewritten = call_llm(messages, temperature=0.1, max_tokens=150)
        # Strip any quotes the LLM might wrap around the result
        rewritten = rewritten.strip().strip('"').strip("'").strip()

        if not rewritten or len(rewritten) < 3:
            logger.warning("[QueryRewrite] LLM returned empty/short result, using original query")
            return original_query

        logger.info(f"[QueryRewrite] '{original_query}' → '{rewritten}'")
        return rewritten

    except Exception as e:
        logger.error(f"[QueryRewrite] Error: {e}. Falling back to original query.")
        return original_query
