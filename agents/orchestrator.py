"""
Orchestrator — Main entry point for the multi-agent pipeline.

Flow:
  1. Guardrails Agent → filter/reject/greet
  2. Router → classify as rag / internet / hybrid
  3. Execute appropriate agent(s)
  4. Return final response
"""
import logging
import time
from agents.guardrails_agent import run_guardrails
from agents.router import route_query
from agents.rag_agent import run_rag_agent
from agents.search_agent import run_search_agent
from agents.hybrid_agent import run_hybrid_agent
from agents.graph_agent import run_graph_agent
from agents.diagnosis_agent import run_diagnosis_agent
from agents.post_processing import strip_markdown_artifacts

logger = logging.getLogger(__name__)


def process_query(user_query: str) -> dict:
    """
    Process a user query through the full multi-agent pipeline.
    
    Returns:
        dict with:
            - "answer": str
            - "agent": str (which agent handled it)
            - "sources": list/dict of sources
            - "route": str (routing decision)
            - "guardrails": str (guardrails category)
            - "processing_time": float (seconds)
    """
    start_time = time.time()
    query = user_query.strip()

    if not query:
        return {
            "answer": "Please enter a question.",
            "agent": "system",
            "sources": [],
            "route": "none",
            "guardrails": "reject",
            "processing_time": 0,
        }

    # --- Step 1: Guardrails ---
    logger.info(f"[Orchestrator] Running guardrails for: {query[:80]}...")
    guardrails_result = run_guardrails(query)
    category = guardrails_result["category"]

    if category == "greeting":
        return {
            "answer": guardrails_result["message"] or "Hello! I'm MarineMind, your maritime AI assistant. How can I help you today?",
            "agent": "guardrails",
            "sources": [],
            "route": "greeting",
            "guardrails": "greeting",
            "processing_time": time.time() - start_time,
        }

    if category == "reject":
        return {
            "answer": guardrails_result["message"] or "I can only assist with maritime and marine engineering queries. Please ask a relevant question.",
            "agent": "guardrails",
            "sources": [],
            "route": "rejected",
            "guardrails": "reject",
            "processing_time": time.time() - start_time,
        }

    # --- Step 2: Router ---
    logger.info("[Orchestrator] Query passed guardrails. Routing...")
    routing = route_query(query)
    route = routing["route"]
    logger.info(f"[Orchestrator] Route: {route} — {routing['reasoning']}")

    # --- Step 3: Execute Agent(s) ---
    if route == "graph":
        result = run_graph_agent(query)
    elif route == "diagnosis":
        result = run_diagnosis_agent(query)
    elif route == "rag":
        result = run_rag_agent(query)
    elif route == "internet":
        result = run_search_agent(query)
    elif route == "hybrid":
        rag_result = run_rag_agent(query)
        search_result = run_search_agent(query)
        result = run_hybrid_agent(query, rag_result, search_result)
    else:
        result = run_rag_agent(query)  # Default fallback

    # Post-process: strip markdown artifacts from the answer
    result["answer"] = strip_markdown_artifacts(result.get("answer", ""))

    result["route"] = route
    result["guardrails"] = "pass"
    result["routing_reasoning"] = routing["reasoning"]
    result["processing_time"] = round(time.time() - start_time, 2)

    return result
