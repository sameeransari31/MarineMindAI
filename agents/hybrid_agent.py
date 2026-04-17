"""
Hybrid Agent — Combines RAG and Internet Search results into a unified answer.
"""
from agents.llm_client import call_llm

HYBRID_SYSTEM_PROMPT = """You are a maritime AI assistant for MarineMind.

You have been given TWO sets of information:
1. Internal documents (from ship manuals, noon reports, technical docs) — cited as [doc1], [doc2], etc.
2. External internet search results (current regulations, news, benchmarks) — cited as [web1], [web2], etc.

Your job is to MERGE both into a single, coherent, and comprehensive answer.

CITATION RULES (MANDATORY):
- Every factual statement MUST have an inline citation placed IMMEDIATELY after the sentence it supports.
- Use [doc1], [doc2] etc. for information from internal documents.
- Use [web1], [web2] etc. for information from external internet sources.
- If a sentence draws from multiple sources, include all: [doc1][web2].
- Do NOT group citations at the end. They must appear inline throughout.
- Only cite sources that actually support the statement.
- Prioritize internal documents for vessel-specific data.
- Use external data for current standards, benchmarks, and regulations.
- If there are conflicts between sources, note the discrepancy.

FORMATTING RULES (MANDATORY):
- Do NOT use markdown formatting. No **, ##, __, ``` or any markdown symbols.
- Use plain numbered lists (1. 2. 3.) or dash bullet points (- item) for structure.
- Use blank lines to separate sections.
- Use UPPERCASE or Title Case for section headings on their own line.
- Keep the response clean, professional, and easy to read.
"""


def run_hybrid_agent(user_query: str, rag_result: dict, search_result: dict) -> dict:
    """
    Merge RAG and Internet Search results into a unified answer.
    
    Returns:
        dict with:
            - "answer": str
            - "sources": combined sources
            - "citation_map": merged citation references
            - "agent": "hybrid"
    """
    rag_answer = rag_result.get("answer", "No internal documents found.")
    search_answer = search_result.get("answer", "No internet results found.")

    # Merge citation maps from both agents
    rag_citation_map = rag_result.get("citation_map", {})
    search_citation_map = search_result.get("citation_map", {})
    merged_citation_map = {**rag_citation_map, **search_citation_map}

    # Build citation reference guide
    cite_lines = []
    for k, v in rag_citation_map.items():
        cite_lines.append(f"[{k}] = {v.get('source', 'Unknown')} (internal document)")
    for k, v in search_citation_map.items():
        cite_lines.append(f"[{k}] = {v.get('title', 'Unknown')} ({v.get('url', '')})")
    cite_guide = "\n".join(cite_lines)

    messages = [
        {"role": "system", "content": HYBRID_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Question: {user_query}\n\n"
                f"--- INTERNAL DOCUMENTS ---\n{rag_answer}\n\n"
                f"--- EXTERNAL SEARCH ---\n{search_answer}\n\n"
                f"--- CITATION REFERENCE ---\n{cite_guide}\n\n"
                "Provide a unified, comprehensive answer with inline citations from both sources."
            ),
        },
    ]

    answer = call_llm(messages, temperature=0.3, max_tokens=1500)

    combined_sources = {
        "internal": rag_result.get("sources", []),
        "external": search_result.get("sources", []),
    }

    return {
        "answer": answer,
        "sources": combined_sources,
        "citation_map": merged_citation_map,
        "agent": "hybrid",
    }
