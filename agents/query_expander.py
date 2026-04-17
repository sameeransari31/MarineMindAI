"""
Query Expander — Generates semantically related search variations of a query.

Stage 2 of the RAG pipeline: Query Rewrite → Query Expand → Retrieve → Rerank → Generate
"""
import json
import logging
from agents.llm_client import call_llm

logger = logging.getLogger(__name__)

EXPAND_SYSTEM_PROMPT = """You are a query expansion assistant for a maritime engineering knowledge base.

Your job is to take a single search query and generate 3 to 5 alternative search queries
that would help retrieve additional relevant documents from a technical maritime document store.

Expansion strategies to use:
- Synonym variations (e.g., "fuel consumption" → "fuel usage", "bunker consumption")
- Technical vs. plain-language variations (e.g., "scavenge air" → "charge air")
- Abbreviation/full-form variations (e.g., "SFOC" → "Specific Fuel Oil Consumption")
- Domain-specific phrasing (e.g., "engine overhaul" → "main engine top overhaul procedure")
- Related concept queries (e.g., "cylinder liner wear" → "cylinder liner inspection limits")

Rules:
- Each expanded query must remain closely related to the original intent.
- Do NOT generate overly broad or unrelated queries.
- Return ONLY a JSON array of strings. Example: ["query 1", "query 2", "query 3"]
- No explanations, no numbering outside the array, no markdown."""


def expand_query(rewritten_query: str, max_expansions: int = 4) -> list[str]:
    """
    Expand a rewritten query into multiple semantically related search variations.
    
    Args:
        rewritten_query: The rewritten (optimized) query.
        max_expansions: Max number of expanded queries (3-5).
    
    Returns:
        List of expanded query strings (does NOT include the original).
    """
    messages = [
        {"role": "system", "content": EXPAND_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Generate {max_expansions} search query variations for:\n\n"
                f"{rewritten_query}"
            ),
        },
    ]

    try:
        raw = call_llm(messages, temperature=0.3, max_tokens=400)

        # Parse JSON array from LLM output
        # Handle cases where LLM wraps in code fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        expansions = json.loads(cleaned)

        if not isinstance(expansions, list):
            logger.warning("[QueryExpand] LLM returned non-list, falling back to empty")
            return []

        # Filter and clean
        expansions = [
            q.strip() for q in expansions
            if isinstance(q, str) and len(q.strip()) >= 5
        ][:max_expansions]

        logger.info(f"[QueryExpand] Generated {len(expansions)} expansions for '{rewritten_query}':")
        for i, eq in enumerate(expansions, 1):
            logger.info(f"  [{i}] {eq}")

        return expansions

    except json.JSONDecodeError:
        logger.warning(f"[QueryExpand] Failed to parse JSON from LLM output: {raw[:200]}")
        return []
    except Exception as e:
        logger.error(f"[QueryExpand] Error: {e}")
        return []
