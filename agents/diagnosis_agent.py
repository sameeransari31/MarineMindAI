"""
Diagnosis Agent — Intelligent machinery issue diagnosis using hybrid reasoning.

Pipeline:
  1. Problem Understanding → Extract symptoms, affected components, relevant metrics
  2. Data Analysis → Fetch and analyze relevant noon report trends/anomalies
  3. Knowledge Retrieval → Fetch relevant manual/SOP content via RAG
  4. Hybrid Reasoning → Combine data insights + knowledge for root cause analysis
  5. Structured Response → Problem summary, observations, causes, recommendations

Handles queries like:
  - "Engine is overheating"
  - "Fuel consumption suddenly increased"
  - "Vessel speed dropped despite constant RPM"
"""
import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from agents.llm_client import call_llm
from agents.rag_agent import run_rag_agent
from agents.vector_store import query_vectors
from agents.reranker import rerank_chunks
from administration.models import Vessel, NoonReport
from analytics import analytics as analytics_engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: PROBLEM UNDERSTANDING — Extract symptoms, components, metrics
# ─────────────────────────────────────────────────────────────────────────────

SYMPTOM_EXTRACTION_PROMPT = """You are a marine engineering problem analysis expert for MarineMind.

Your job is to analyze a user's machinery issue description and extract structured information.

Respond with ONLY valid JSON in this EXACT format:
{
  "symptoms": ["list of identified symptoms"],
  "affected_components": ["list of potentially affected components/systems"],
  "relevant_metrics": ["list of noon report metrics that should be checked"],
  "severity_estimate": "low|medium|high|critical",
  "problem_category": "engine|fuel_system|cooling_system|propulsion|electrical|auxiliary|hull_performance|navigation|weather_related|lubrication|exhaust|turbocharger|other",
  "time_context": "recent|gradual|sudden|unknown",
  "vessel_name": "vessel name if mentioned, or null",
  "vessel_imo": "IMO number if mentioned, or null",
  "needs_data_analysis": true,
  "needs_manual_lookup": true,
  "analysis_query": "a specific query to search noon report data for anomalies",
  "knowledge_query": "a specific query to search manuals for troubleshooting information"
}

Available noon report metrics to reference:
- speed_avg, speed_ordered, distance_sailed
- rpm_avg, me_load_percent, me_power_kw, me_exhaust_temp, sfoc, slip_percent
- fo_consumption, bf_consumption, fo_rob, bf_rob
- ae_fo_consumption, boiler_fo_consumption
- me_cylinder_oil_consumption, me_system_oil_consumption, ae_lub_oil_consumption
- draft_fore, draft_aft, draft_mean, cargo_quantity, cargo_condition
- wind_force, sea_state, swell_height, current_knots
- air_temp, sea_water_temp, barometric_pressure
- hours_steaming, hours_stopped

Affected component examples:
- Main engine, auxiliary engine, turbocharger, fuel system, cooling system
- Lubrication system, exhaust system, propulsion/propeller, boiler
- Electrical system, navigation equipment, hull/fouling, fuel injectors
- Cylinder liners, piston rings, bearings, pumps, valves, filters

RULES:
1. Extract ALL symptoms mentioned or implied
2. Identify ALL potentially affected components
3. List the most relevant noon report metrics to check
4. Assess severity based on safety implications
5. Determine if data analysis and/or manual lookup is needed
6. Generate focused queries for data analysis and knowledge retrieval

Respond with ONLY the JSON object."""


def extract_problem_info(user_query: str) -> dict:
    """
    Use LLM to extract structured problem information from a user's issue description.
    """
    messages = [
        {"role": "system", "content": SYMPTOM_EXTRACTION_PROMPT},
        {"role": "user", "content": user_query},
    ]

    raw = call_llm(messages, temperature=0.0, max_tokens=600)

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        info = json.loads(cleaned)

        # Apply defaults
        info.setdefault("symptoms", [])
        info.setdefault("affected_components", [])
        info.setdefault("relevant_metrics", ["fo_consumption", "speed_avg", "rpm_avg"])
        info.setdefault("severity_estimate", "medium")
        info.setdefault("problem_category", "other")
        info.setdefault("time_context", "unknown")
        info.setdefault("vessel_name", None)
        info.setdefault("vessel_imo", None)
        info.setdefault("needs_data_analysis", True)
        info.setdefault("needs_manual_lookup", True)
        info.setdefault("analysis_query", user_query)
        info.setdefault("knowledge_query", user_query)

        return info

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse problem info: {e}. Raw: {raw[:200]}")
        return {
            "symptoms": [user_query],
            "affected_components": [],
            "relevant_metrics": ["fo_consumption", "speed_avg", "rpm_avg"],
            "severity_estimate": "medium",
            "problem_category": "other",
            "time_context": "unknown",
            "vessel_name": None,
            "vessel_imo": None,
            "needs_data_analysis": True,
            "needs_manual_lookup": True,
            "analysis_query": user_query,
            "knowledge_query": user_query,
        }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: DATA ANALYSIS — Fetch and analyze relevant noon report data
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_vessel(vessel_name: str | None, vessel_imo: str | None) -> Vessel | None:
    """Match vessel by name/IMO, or use default if only one exists."""
    if vessel_imo:
        try:
            return Vessel.objects.get(imo_number=vessel_imo)
        except Vessel.DoesNotExist:
            pass

    if vessel_name:
        try:
            return Vessel.objects.get(name__iexact=vessel_name)
        except Vessel.DoesNotExist:
            pass
        matches = Vessel.objects.filter(name__icontains=vessel_name)
        if matches.exists():
            return matches.first()

    if Vessel.objects.count() == 1:
        return Vessel.objects.first()

    return None


def analyze_vessel_data(problem_info: dict, vessel: Vessel | None) -> dict:
    """
    Fetch recent noon report data and detect anomalies relevant to the reported problem.
    Returns structured data observations.
    """
    if not vessel:
        return {
            "has_data": False,
            "message": "No vessel identified for data analysis.",
            "observations": [],
            "trends": [],
            "anomalies": [],
        }

    vessel_id = str(vessel.id)
    vessel_name = vessel.name
    date_to = date.today()
    date_from = date_to - timedelta(days=30)
    relevant_metrics = problem_info.get("relevant_metrics", [])

    observations = []
    trends = []
    anomalies = []

    # Fetch recent summary
    try:
        summary = analytics_engine.get_vessel_summary(vessel_id)
        if summary.get("has_data"):
            observations.append({
                "type": "summary",
                "description": f"Vessel {vessel_name} has {summary.get('total_reports', 0)} noon reports",
                "data": {
                    "avg_speed": summary.get("avg_speed_knots"),
                    "avg_rpm": summary.get("avg_rpm"),
                    "avg_fo_consumption": summary.get("avg_fo_consumption_mt"),
                    "avg_sfoc": summary.get("avg_sfoc"),
                    "avg_me_load": summary.get("avg_me_load_percent"),
                    "avg_slip": summary.get("avg_slip_percent"),
                },
            })
    except Exception as e:
        logger.warning(f"[Diagnosis] Summary fetch failed: {e}")

    # Fetch anomaly flags
    try:
        anomaly_data = analytics_engine.get_anomaly_flags(vessel_id, date_from, date_to)
        if anomaly_data.get("total_flags", 0) > 0:
            for flag in anomaly_data.get("flags", [])[:10]:
                anomalies.append({
                    "date": flag.get("report_date"),
                    "field": flag.get("field"),
                    "value": flag.get("value"),
                    "expected_range": flag.get("expected_range"),
                    "label": flag.get("label"),
                })
    except Exception as e:
        logger.warning(f"[Diagnosis] Anomaly fetch failed: {e}")

    # Fetch recent fuel consumption trend
    if any(m in relevant_metrics for m in ["fo_consumption", "bf_consumption", "sfoc"]):
        try:
            fuel_data = analytics_engine.get_fuel_consumption_trend(
                vessel_id, date_from, date_to, "daily"
            )
            if fuel_data.get("labels"):
                avg_fo = fuel_data["datasets"].get("avg_fo_consumption", [])
                if avg_fo:
                    recent_avg = sum(v for v in avg_fo[-7:] if v) / max(len([v for v in avg_fo[-7:] if v]), 1)
                    older_avg = sum(v for v in avg_fo[:-7] if v) / max(len([v for v in avg_fo[:-7] if v]), 1)
                    if older_avg > 0:
                        change_pct = ((recent_avg - older_avg) / older_avg) * 100
                        direction = "increased" if change_pct > 0 else "decreased"
                        trends.append({
                            "metric": "FO Consumption",
                            "direction": direction,
                            "change_percent": round(abs(change_pct), 1),
                            "recent_avg": round(recent_avg, 2),
                            "baseline_avg": round(older_avg, 2),
                            "period": "last 7 days vs prior period",
                        })
        except Exception as e:
            logger.warning(f"[Diagnosis] Fuel trend fetch failed: {e}")

    # Fetch speed/RPM relationship
    if any(m in relevant_metrics for m in ["speed_avg", "rpm_avg", "slip_percent"]):
        try:
            rpm_data = analytics_engine.get_rpm_performance(vessel_id, date_from, date_to)
            points = rpm_data.get("data_points", [])
            if len(points) >= 5:
                recent_points = points[-7:]
                older_points = points[:-7] if len(points) > 7 else points[:len(points)//2]

                if recent_points and older_points:
                    recent_speed = sum(p["speed"] for p in recent_points if p.get("speed")) / max(len([p for p in recent_points if p.get("speed")]), 1)
                    older_speed = sum(p["speed"] for p in older_points if p.get("speed")) / max(len([p for p in older_points if p.get("speed")]), 1)
                    recent_rpm = sum(p["rpm"] for p in recent_points if p.get("rpm")) / max(len([p for p in recent_points if p.get("rpm")]), 1)
                    older_rpm = sum(p["rpm"] for p in older_points if p.get("rpm")) / max(len([p for p in older_points if p.get("rpm")]), 1)

                    if older_speed > 0:
                        speed_change = ((recent_speed - older_speed) / older_speed) * 100
                        trends.append({
                            "metric": "Speed",
                            "direction": "increased" if speed_change > 0 else "decreased",
                            "change_percent": round(abs(speed_change), 1),
                            "recent_avg": round(recent_speed, 2),
                            "baseline_avg": round(older_speed, 2),
                            "period": "last 7 days vs prior period",
                        })
                    if older_rpm > 0:
                        rpm_change = ((recent_rpm - older_rpm) / older_rpm) * 100
                        trends.append({
                            "metric": "RPM",
                            "direction": "increased" if rpm_change > 0 else "decreased",
                            "change_percent": round(abs(rpm_change), 1),
                            "recent_avg": round(recent_rpm, 2),
                            "baseline_avg": round(older_rpm, 2),
                            "period": "last 7 days vs prior period",
                        })

                    # Check for speed drop with constant RPM (hull fouling indicator)
                    if recent_points:
                        recent_slips = [p.get("slip_percent") for p in recent_points if p.get("slip_percent") is not None]
                        if recent_slips:
                            avg_slip = sum(recent_slips) / len(recent_slips)
                            if avg_slip > 10:
                                observations.append({
                                    "type": "warning",
                                    "description": f"High propeller slip detected: {round(avg_slip, 1)}% average (normal: 2-8%)",
                                })
        except Exception as e:
            logger.warning(f"[Diagnosis] RPM analysis failed: {e}")

    # Fetch weather context
    if any(m in relevant_metrics for m in ["wind_force", "sea_state", "swell_height"]):
        try:
            weather_data = analytics_engine.get_weather_impact(vessel_id, date_from, date_to)
            beaufort = weather_data.get("by_beaufort_scale", [])
            if beaufort:
                high_wind_reports = [b for b in beaufort if b.get("wind_force", 0) >= 6]
                if high_wind_reports:
                    total_high_wind = sum(b.get("report_count", 0) for b in high_wind_reports)
                    total_all = sum(b.get("report_count", 0) for b in beaufort)
                    if total_all > 0:
                        pct = (total_high_wind / total_all) * 100
                        if pct > 20:
                            observations.append({
                                "type": "context",
                                "description": f"Heavy weather: {round(pct)}% of recent reports had Beaufort 6+ winds",
                            })
        except Exception as e:
            logger.warning(f"[Diagnosis] Weather analysis failed: {e}")

    # Fetch recent raw data for the relevant metrics
    recent_readings = []
    try:
        recent_qs = NoonReport.objects.filter(
            vessel_id=vessel_id, report_date__gte=date_from
        ).order_by("-report_date")[:10]

        for report in recent_qs:
            reading = {"date": report.report_date.isoformat()}
            for metric in relevant_metrics:
                val = getattr(report, metric, None)
                if val is not None:
                    reading[metric] = float(val) if isinstance(val, Decimal) else val
            recent_readings.append(reading)
    except Exception as e:
        logger.warning(f"[Diagnosis] Recent readings fetch failed: {e}")

    return {
        "has_data": bool(observations or trends or anomalies or recent_readings),
        "vessel_name": vessel_name,
        "observations": observations,
        "trends": trends,
        "anomalies": anomalies,
        "recent_readings": recent_readings[:5],
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: KNOWLEDGE RETRIEVAL — Fetch relevant manual/SOP content
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_relevant_knowledge(user_query: str, problem_info: dict) -> dict:
    """
    Search manuals and technical documents for troubleshooting information
    relevant to the diagnosed problem. Uses the RAG pipeline's retrieval.
    """
    knowledge_query = problem_info.get("knowledge_query", user_query)
    components = problem_info.get("affected_components", [])
    symptoms = problem_info.get("symptoms", [])

    # Build expanded search queries
    search_queries = [knowledge_query]
    if components:
        search_queries.append(f"troubleshooting {' '.join(components[:3])}")
    if symptoms:
        search_queries.append(f"causes of {' '.join(symptoms[:3])}")

    # Retrieve from vector store
    all_chunks = {}
    for query in search_queries:
        try:
            matches = query_vectors(query, top_k=6)
            for match in matches:
                text_key = match["metadata"].get("text", match["text"][:80])
                if text_key not in all_chunks or match["score"] > all_chunks[text_key]["score"]:
                    all_chunks[text_key] = match
        except Exception as e:
            logger.warning(f"[Diagnosis] Vector search failed for '{query[:50]}': {e}")

    candidates = list(all_chunks.values())

    if not candidates:
        return {
            "has_knowledge": False,
            "chunks": [],
            "sources": [],
            "citation_map": {},
        }

    # Rerank against the original query
    try:
        reranked = rerank_chunks(
            original_query=user_query,
            chunks=candidates,
            top_n=5,
            relevance_threshold=0.1,
        )
    except Exception:
        reranked = sorted(candidates, key=lambda c: c["score"], reverse=True)[:5]

    # Build sources and citation map
    sources = []
    citation_map = {}
    for i, chunk in enumerate(reranked, 1):
        cite_key = f"doc{i}"
        source_info = chunk["metadata"].get("source", "Unknown")
        entry = {
            "source": source_info,
            "score": round(chunk["score"], 4),
            "rerank_score": round(chunk.get("rerank_score", 0), 4),
            "document_id": chunk["metadata"].get("document_id", ""),
            "chunk_index": chunk["metadata"].get("chunk_index", ""),
            "chunk_text": chunk["text"],
            "page": chunk["metadata"].get("page", None),
            "type": "document",
        }
        sources.append(entry)
        citation_map[cite_key] = entry

    # Resolve document file URLs
    from ingestion.models import Document
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

    return {
        "has_knowledge": bool(reranked),
        "chunks": reranked,
        "sources": sources,
        "citation_map": citation_map,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: HYBRID REASONING — Generate structured diagnosis
# ─────────────────────────────────────────────────────────────────────────────

DIAGNOSIS_SYSTEM_PROMPT = """You are an expert marine engineering diagnostic AI assistant for MarineMind.

You diagnose machinery issues by combining:
1. OBSERVATIONS from vessel performance data (noon reports, trends, anomalies)
2. KNOWLEDGE from ship manuals, SOPs, and technical documents

Your response MUST follow this EXACT structure with these section headers:

PROBLEM SUMMARY
A 2-3 sentence summary of the reported issue and its context.

OBSERVATIONS (Data Insights)
List findings from the vessel's performance data. Include specific numbers, trends, and anomalies.
If no data was available, state that clearly.

POSSIBLE CAUSES
List possible root causes ranked by likelihood. For each cause:
- State the cause
- Explain why it's likely based on the evidence
- Rate: [HIGH LIKELIHOOD] / [MEDIUM LIKELIHOOD] / [LOW LIKELIHOOD]

RECOMMENDED ACTIONS
Provide step-by-step practical recommendations for the marine engineer:
1. Immediate checks to perform
2. Inspections to conduct
3. Adjustments or repairs to make
4. Preventive measures

SOURCES
Briefly note which information came from data analysis vs. manual knowledge.

CITATION RULES (MANDATORY):
- Every statement from manuals/documents MUST have an inline citation: [doc1], [doc2], etc.
- Observations from data should be clearly marked as "Based on noon report data" or similar.
- Do NOT fabricate citations. Only cite sources that were actually provided.

FORMATTING RULES:
- Do NOT use markdown formatting. No **, ##, __, ``` or any markdown symbols.
- Use plain numbered lists (1. 2. 3.) or dash bullet points (- item).
- Use UPPERCASE for section headings on their own line.
- Use blank lines between sections.
- Be precise, technical, and practical — your audience is marine engineers.
- Provide severity levels for causes using brackets: [HIGH LIKELIHOOD], [MEDIUM LIKELIHOOD], [LOW LIKELIHOOD]
"""


def generate_diagnosis(
    user_query: str,
    problem_info: dict,
    data_analysis: dict,
    knowledge: dict,
) -> dict:
    """
    Generate a structured diagnosis combining data analysis and knowledge retrieval.
    """
    # Build data context
    data_context_parts = []
    if data_analysis.get("has_data"):
        vessel_name = data_analysis.get("vessel_name", "Unknown vessel")
        data_context_parts.append(f"Vessel: {vessel_name}")

        for obs in data_analysis.get("observations", []):
            data_context_parts.append(f"- {obs['type'].upper()}: {obs['description']}")
            if obs.get("data"):
                for k, v in obs["data"].items():
                    if v is not None:
                        data_context_parts.append(f"  {k}: {v}")

        for trend in data_analysis.get("trends", []):
            data_context_parts.append(
                f"- TREND: {trend['metric']} has {trend['direction']} by {trend['change_percent']}% "
                f"(recent: {trend['recent_avg']}, baseline: {trend['baseline_avg']}, {trend['period']})"
            )

        for anomaly in data_analysis.get("anomalies", []):
            data_context_parts.append(
                f"- ANOMALY on {anomaly['date']}: {anomaly['label']} — "
                f"{anomaly['field']} = {anomaly['value']} "
                f"(expected range: {anomaly['expected_range']})"
            )

        if data_analysis.get("recent_readings"):
            data_context_parts.append("Recent readings (latest first):")
            for reading in data_analysis["recent_readings"]:
                parts = [f"{k}: {v}" for k, v in reading.items()]
                data_context_parts.append(f"  {', '.join(parts)}")
    else:
        data_context_parts.append("No vessel performance data available for analysis.")

    data_context = "\n".join(data_context_parts)

    # Build knowledge context
    knowledge_context_parts = []
    cite_guide_parts = []
    citation_map = knowledge.get("citation_map", {})

    if knowledge.get("has_knowledge"):
        for key, entry in citation_map.items():
            knowledge_context_parts.append(f"[{key}: {entry['source']}]\n{entry['chunk_text']}")
            cite_guide_parts.append(f"[{key}] = {entry['source']}")
    else:
        knowledge_context_parts.append("No relevant manual or document content found.")

    knowledge_context = "\n\n---\n\n".join(knowledge_context_parts)
    cite_guide = "\n".join(cite_guide_parts) if cite_guide_parts else "No citations available."

    # Build problem context
    problem_context = (
        f"Reported symptoms: {', '.join(problem_info.get('symptoms', ['Not specified']))}\n"
        f"Affected components: {', '.join(problem_info.get('affected_components', ['Not identified']))}\n"
        f"Problem category: {problem_info.get('problem_category', 'Unknown')}\n"
        f"Severity estimate: {problem_info.get('severity_estimate', 'Unknown')}\n"
        f"Time context: {problem_info.get('time_context', 'Unknown')}"
    )

    messages = [
        {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User's issue report: {user_query}\n\n"
                f"--- PROBLEM ANALYSIS ---\n{problem_context}\n\n"
                f"--- VESSEL PERFORMANCE DATA ---\n{data_context}\n\n"
                f"--- TECHNICAL DOCUMENTATION ---\n{knowledge_context}\n\n"
                f"--- CITATION REFERENCE ---\n{cite_guide}\n\n"
                "Provide a comprehensive structured diagnosis with inline citations."
            ),
        },
    ]

    answer = call_llm(messages, temperature=0.3, max_tokens=2000)

    return {
        "answer": answer,
        "citation_map": citation_map,
        "sources": knowledge.get("sources", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE — run_diagnosis_agent
# ─────────────────────────────────────────────────────────────────────────────

def run_diagnosis_agent(user_query: str) -> dict:
    """
    Execute the full machinery issue diagnosis pipeline:
      1. Problem Understanding → extract symptoms, components, metrics
      2. Data Analysis → fetch and analyze relevant noon report data
      3. Knowledge Retrieval → fetch relevant manual/SOP content
      4. Hybrid Reasoning → generate structured diagnosis
    
    Returns:
        dict with "answer", "sources", "citation_map", "agent",
        "diagnosis" (structured metadata), and "pipeline_debug".
    """
    logger.info(f"[Diagnosis Agent] Starting diagnosis for: {user_query[:80]}")

    pipeline_debug = {"original_query": user_query}

    # ── Step 1: Problem Understanding ─────────────────────────────────────
    logger.info("[Diagnosis Agent] Step 1 — Problem Understanding")
    problem_info = extract_problem_info(user_query)
    pipeline_debug["problem_info"] = problem_info
    logger.info(
        f"[Diagnosis Agent] Symptoms: {problem_info.get('symptoms', [])}, "
        f"Components: {problem_info.get('affected_components', [])}, "
        f"Category: {problem_info.get('problem_category')}"
    )

    # ── Step 2: Data Analysis ─────────────────────────────────────────────
    data_analysis = {"has_data": False, "observations": [], "trends": [], "anomalies": []}
    vessel = None

    if problem_info.get("needs_data_analysis", True):
        logger.info("[Diagnosis Agent] Step 2 — Data Analysis")
        vessel = _resolve_vessel(
            problem_info.get("vessel_name"),
            problem_info.get("vessel_imo"),
        )
        data_analysis = analyze_vessel_data(problem_info, vessel)
        pipeline_debug["data_analysis"] = {
            "has_data": data_analysis["has_data"],
            "observation_count": len(data_analysis.get("observations", [])),
            "trend_count": len(data_analysis.get("trends", [])),
            "anomaly_count": len(data_analysis.get("anomalies", [])),
        }
    else:
        logger.info("[Diagnosis Agent] Step 2 — Skipping data analysis (not needed)")

    # ── Step 3: Knowledge Retrieval ───────────────────────────────────────
    knowledge = {"has_knowledge": False, "chunks": [], "sources": [], "citation_map": {}}

    if problem_info.get("needs_manual_lookup", True):
        logger.info("[Diagnosis Agent] Step 3 — Knowledge Retrieval")
        knowledge = retrieve_relevant_knowledge(user_query, problem_info)
        pipeline_debug["knowledge_retrieval"] = {
            "has_knowledge": knowledge["has_knowledge"],
            "chunks_retrieved": len(knowledge.get("chunks", [])),
        }
    else:
        logger.info("[Diagnosis Agent] Step 3 — Skipping knowledge retrieval (not needed)")

    # ── Step 4: Hybrid Reasoning ──────────────────────────────────────────
    logger.info("[Diagnosis Agent] Step 4 — Generating Diagnosis")
    diagnosis_result = generate_diagnosis(
        user_query, problem_info, data_analysis, knowledge,
    )

    # Build structured diagnosis metadata for frontend rendering
    diagnosis_metadata = {
        "symptoms": problem_info.get("symptoms", []),
        "affected_components": problem_info.get("affected_components", []),
        "severity": problem_info.get("severity_estimate", "medium"),
        "category": problem_info.get("problem_category", "other"),
        "time_context": problem_info.get("time_context", "unknown"),
        "data_available": data_analysis.get("has_data", False),
        "knowledge_available": knowledge.get("has_knowledge", False),
        "vessel_name": data_analysis.get("vessel_name"),
        "observations": data_analysis.get("observations", []),
        "trends": data_analysis.get("trends", []),
        "anomalies": data_analysis.get("anomalies", []),
    }

    logger.info("[Diagnosis Agent] Diagnosis complete")

    return {
        "answer": diagnosis_result["answer"],
        "sources": diagnosis_result.get("sources", []),
        "citation_map": diagnosis_result.get("citation_map", {}),
        "agent": "diagnosis",
        "diagnosis": diagnosis_metadata,
        "pipeline_debug": pipeline_debug,
    }
