"""
Internet Search Agent — Uses Tavily API for external knowledge retrieval.
"""
import logging
from tavily import TavilyClient
from django.conf import settings
from agents.llm_client import call_llm

logger = logging.getLogger(__name__)

SEARCH_SYSTEM_PROMPT = """You are a maritime industry AI assistant for MarineMind.

You answer questions using the provided internet search results.

CITATION RULES (MANDATORY):
- Every factual statement MUST have an inline citation placed IMMEDIATELY after the sentence it supports.
- Use the citation format [web1], [web2], etc. matching the source labels provided.
- If a sentence draws from multiple sources, include all relevant citations: [web1][web3].
- Do NOT group citations at the end. They must appear inline throughout.
- Only cite sources that actually support the statement.
- If search results are insufficient, state that clearly.

FORMATTING RULES (MANDATORY):
- Do NOT use markdown formatting. No **, ##, __, ``` or any markdown symbols.
- Use plain numbered lists (1. 2. 3.) or dash bullet points (- item) for structure.
- Use blank lines to separate sections.
- Use UPPERCASE or Title Case for section headings on their own line.
- Keep the response clean, professional, and easy to read.
- Focus on maritime, shipping, and marine engineering relevance.
"""


def run_search_agent(user_query: str, max_results: int = 5) -> dict:
    """
    Search the internet via Tavily and generate an answer.
    
    Returns:
        dict with:
            - "answer": str
            - "sources": list of search result URLs
            - "agent": "internet"
    """
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        return {
            "answer": "Internet search is not configured. Please set TAVILY_API_KEY.",
            "sources": [],
            "agent": "internet",
        }

    try:
        client = TavilyClient(api_key=api_key)
        search_results = client.search(
            query=f"maritime shipping {user_query}",
            max_results=max_results,
            search_depth="advanced",
        )
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {
            "answer": "I was unable to perform the internet search. Please try again later.",
            "sources": [],
            "agent": "internet",
        }

    results = search_results.get("results", [])
    if not results:
        return {
            "answer": "No relevant results found from internet search.",
            "sources": [],
            "agent": "internet",
        }

    # Build context from search results and citation map
    context_parts = []
    sources = []
    citation_map = {}
    for i, result in enumerate(results, 1):
        title = result.get("title", "")
        content = result.get("content", "")
        url = result.get("url", "")
        cite_key = f"web{i}"
        context_parts.append(f"[{cite_key}: {title}]\n{content}")
        source_entry = {"title": title, "url": url, "type": "web"}
        sources.append(source_entry)
        citation_map[cite_key] = source_entry

    context = "\n\n---\n\n".join(context_parts)

    # Build citation reference guide for the LLM
    cite_guide = "\n".join(
        f"[{k}] = {v['title']} ({v['url']})" for k, v in citation_map.items()
    )

    messages = [
        {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Search results:\n\n{context}\n\n---\n\n"
                f"Citation Reference:\n{cite_guide}\n\n---\n\n"
                f"Question: {user_query}"
            ),
        },
    ]

    answer = call_llm(messages, temperature=0.3, max_tokens=1024)

    return {
        "answer": answer,
        "sources": sources,
        "citation_map": citation_map,
        "agent": "internet",
    }
