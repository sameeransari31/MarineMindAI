"""
Router / Decision Layer — Deterministic query classification.

Classifies queries into exactly one of:
  - "rag"        → Internal documents only
  - "internet"   → External search only  
  - "hybrid"     → Both RAG + Internet, merged
  - "graph"      → Vessel performance graph generation
  - "diagnosis"  → Machinery issue diagnosis (hybrid data + knowledge)
NO random/probabilistic behavior. Uses keyword analysis + LLM classification.
"""
from agents.llm_client import call_llm

ROUTER_SYSTEM_PROMPT = """You are the Router Agent for MarineMind, a maritime AI platform.

Your ONLY job is to classify a user query into exactly ONE category. Respond with ONLY the JSON.

Categories:
1. "rag" — The query is about INTERNAL content that would exist in ship manuals, noon reports, vessel documentation, or previously uploaded technical documents. Examples:
   - "What is the fuel oil purifier procedure for MAN B&W 6S50MC-C?"
   - "What does the manual say about boiler water treatment?"
   - "Explain the turbocharger maintenance schedule"
   - Questions about specific vessels, specific machinery, specific procedures from manuals

2. "internet" — The query requires UP-TO-DATE or GENERAL external knowledge NOT found in ship manuals. Examples:
   - "What are the latest IMO 2026 emission regulations?"
   - "Current bunker fuel prices in Singapore"
   - "Latest MARPOL amendments"
   - News, regulations, market data, current events

3. "hybrid" — The query needs BOTH internal documents AND external data to answer completely. Examples:
   - "Compare our vessel's fuel consumption with current industry benchmarks"
   - "Is our NOx emission compliant with the latest IMO Tier III standards?"

4. "graph" — The query asks for a CHART, GRAPH, PLOT, TREND VISUALIZATION, or PERFORMANCE ANALYSIS from noon report data. This includes ANY analytical question about relationships between vessel performance metrics (speed, fuel, RPM, weather, wind, sea state, draft, cargo, etc.). Examples:
   - "Show fuel consumption trend for the last 30 days"
   - "Plot RPM vs speed for vessel ABC"
   - "Compare engine power against fuel consumption"
   - "Show performance trend over time"
   - "Graph the fuel efficiency for voyage 42"
   - "Display speed vs consumption scatter plot"
   - "Show weather impact on performance"
   - "Compare fleet fuel consumption"
   - "How does wind force affect vessel performance?" (analytical question about measurable metrics)
   - "What is the impact of sea state on speed?" (performance data analysis)
   - "How does weather affect fuel consumption?" (metric relationship analysis)
   - "How does draft affect speed?" (noon report data analysis)
   - Any request that implies: show, plot, graph, chart, trend, visualize, compare metrics, display data
   - Any question about HOW one measured metric AFFECTS/IMPACTS another (these are answerable from noon report data)

5. "diagnosis" — The query describes a MACHINERY PROBLEM, MALFUNCTION, FAULT, or asks for TROUBLESHOOTING help. The user is reporting an issue or asking for diagnosis. Examples:
   - "Engine is overheating"
   - "Fuel consumption suddenly increased"
   - "Vessel speed dropped despite constant RPM"
   - "Main engine exhaust temperature is too high"
   - "Turbocharger is surging"
   - "Excessive vibration in the engine"
   - "Cooling water temperature is rising"
   - "Lube oil pressure is dropping"
   - "Why is the engine losing power?"
   - "What could cause high SFOC?"
   - "Diagnose high cylinder liner wear"
   - "Troubleshoot fuel injector failure"
   - Any query describing a symptom, fault, failure, malfunction, or abnormal condition
   - Any query asking for root cause analysis, troubleshooting, or diagnosis
   - Any query where the user reports something is wrong, broken, abnormal, failing, or degraded

Decision Rules (STRICT):
- If the query describes a PROBLEM, SYMPTOM, MALFUNCTION, or asks to DIAGNOSE/TROUBLESHOOT → "diagnosis"
- If the query asks to show, plot, graph, chart, visualize, or trend any metric data → "graph"
- If the query asks how a measurable factor (wind, weather, sea state, draft, cargo, RPM) affects vessel performance, speed, or fuel → "graph" (can be answered from noon report data)
- If the query mentions specific ship systems, manuals, procedures, or uploaded documents → "rag"
- If the query asks about current events, regulations, news, prices, weather FORECASTS → "internet"
- If the query needs both internal data AND external context → "hybrid"
- When in doubt between "diagnosis" and "rag" for problem-related queries → prefer "diagnosis"
- When in doubt between "graph" and "internet" for performance/metric questions → prefer "graph"
- When in doubt between "rag" and "hybrid", prefer "rag"
- When in doubt between "internet" and "hybrid", prefer "internet"
- NEVER guess randomly. Apply the rules above deterministically.

Respond in this EXACT format:
{"route": "rag|internet|hybrid|graph|diagnosis", "reasoning": "brief one-line explanation"}
"""


def route_query(user_query: str) -> dict:
    """
    Deterministically route a query to the appropriate agent(s).
    
    Returns:
        dict with:
            - "route": "rag" | "internet" | "hybrid"
            - "reasoning": str
    """
    # Step 1: Keyword-based pre-classification for obvious cases
    query_lower = user_query.lower()

    # Strong Graph indicators — check first since graph queries are distinctive
    graph_keywords = [
        "show trend", "plot", "graph", "chart", "visualize",
        "fuel consumption trend", "speed vs", "rpm vs",
        "compare rpm", "compare speed", "compare fuel",
        "performance trend", "consumption trend",
        "show fuel", "display", "fleet comparison",
        "weather impact", "anomaly", "voyage performance",
        "scatter", "bar chart", "line chart",
        "engine power against", "power vs",
        "noon report", "noon reports",
        "breakdown", "month breakdown", "monthly breakdown",
    ]

    # Analytical phrases about metric relationships → graph
    # These catch questions like "How does X affect Y?" where X and Y are measurable
    metric_terms = [
        "wind force", "wind speed", "sea state", "swell",
        "draft", "cargo", "rpm", "engine load", "me load",
        "fuel consumption", "fo consumption", "do consumption",
        "vessel performance", "vessel speed", "ship performance",
        "ship speed", "fuel efficiency", "speed",
        "sfoc", "slip", "exhaust temp",
    ]
    analysis_verbs = ["affect", "impact", "influence", "relate", "correlat", "degrad"]

    has_metric = any(m in query_lower for m in metric_terms)
    has_analysis = any(v in query_lower for v in analysis_verbs)
    if has_metric and has_analysis:
        return {"route": "graph", "reasoning": "Keyword analysis: analytical question about vessel performance metrics detected"}

    # Metric + period/breakdown requests are graph queries even without explicit "plot/chart".
    # Example: "fuel consumption month breakdown for vessel X"
    period_terms = ["breakdown", "monthly", "month", "weekly", "daily", "over time", "trend"]
    if has_metric and any(term in query_lower for term in period_terms):
        return {"route": "graph", "reasoning": "Keyword analysis: metric breakdown/time-series request detected"}

    graph_score = sum(1 for kw in graph_keywords if kw in query_lower)
    if graph_score >= 1:
        return {"route": "graph", "reasoning": "Keyword analysis: graph/chart/visualization request detected"}

    # Strong Diagnosis indicators — check before RAG
    diagnosis_keywords = [
        "overheating", "overheat", "malfunction", "failure", "failing",
        "broken", "fault", "faulty", "diagnose", "diagnosis",
        "troubleshoot", "troubleshooting", "root cause",
        "abnormal", "excessive", "vibration", "surging", "surge",
        "leaking", "leak", "blocked", "clogged",
        "not working", "not starting", "won't start",
        "dropping", "losing power", "power loss",
        "temperature rising", "pressure dropping", "pressure low",
        "what could cause", "what causes", "why is the",
        "suddenly increased", "suddenly decreased",
        "speed dropped", "consumption increased",
        "high exhaust temp", "high sfoc", "high consumption",
        "low pressure", "high temperature",
        "wear", "worn", "damaged", "damage",
        "alarm", "warning", "shut down", "shutdown",
        "misfire", "knocking", "smoke", "black smoke", "white smoke",
    ]

    # Diagnosis problem phrases
    problem_verbs = ["is overheating", "is failing", "is leaking", "is surging",
                     "is dropping", "is rising", "is degraded", "has failed",
                     "is abnormal", "is too high", "is too low", "keeps"]

    has_problem_verb = any(v in query_lower for v in problem_verbs)
    diagnosis_score = sum(1 for kw in diagnosis_keywords if kw in query_lower)

    if diagnosis_score >= 2 or (diagnosis_score >= 1 and has_problem_verb):
        return {"route": "diagnosis", "reasoning": "Keyword analysis: machinery issue/diagnosis request detected"}

    # Strong RAG indicators
    rag_keywords = [
        "manual", "procedure", "maintenance schedule",
        "engine log", "vessel report", "ship manual", "technical drawing",
        "our vessel", "our ship", "our engine", "uploaded document",
        "according to the manual", "what does the manual say",
    ]

    # Strong Internet indicators
    internet_keywords = [
        "latest", "current price", "news", "regulation update",
        "weather forecast", "market", "today", "this week",
        "imo 2025", "imo 2026", "marpol update", "bunker price",
    ]

    rag_score = sum(1 for kw in rag_keywords if kw in query_lower)
    internet_score = sum(1 for kw in internet_keywords if kw in query_lower)

    # If keyword analysis is decisive (clear winner), skip LLM call
    if rag_score >= 2 and internet_score == 0:
        return {"route": "rag", "reasoning": "Keyword analysis: strong RAG indicators detected"}
    if internet_score >= 2 and rag_score == 0:
        return {"route": "internet", "reasoning": "Keyword analysis: strong internet indicators detected"}

    # Step 2: Use LLM for ambiguous cases
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    raw = call_llm(messages, temperature=0.0, max_tokens=150)

    try:
        import json
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        result = json.loads(cleaned)
        route = result.get("route", "rag")
        if route not in ("rag", "internet", "hybrid", "graph", "diagnosis"):
            route = "rag"

        return {
            "route": route,
            "reasoning": result.get("reasoning", "LLM classification"),
        }
    except (Exception,):
        # Default to RAG if parsing fails (safer default for internal docs)
        return {"route": "rag", "reasoning": "Default fallback to RAG"}
