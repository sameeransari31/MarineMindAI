"""
Graph Agent — Natural language to vessel performance graph pipeline.

Pipeline:
  1. Intent Parsing (LLM) → extract graph type, metrics, vessel, time range
  2. Vessel Resolution → match vessel name/IMO to database
  3. Data Fetching → call analytics engine with extracted parameters
  4. Graph Config Generation → produce chart-ready JSON for the frontend

Handles queries like:
  - "Show fuel consumption trend for Vessel X for the last 30 days"
  - "Compare RPM vs speed for voyage 42"
  - "Plot engine power against fuel consumption"
"""
import json
import logging
from difflib import get_close_matches
from datetime import date, timedelta

from agents.llm_client import call_llm
from administration.models import Vessel, NoonReport
from analytics import analytics as analytics_engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# INTENT PARSING — LLM extracts structured graph intent from natural language
# ─────────────────────────────────────────────────────────────────────────────

GRAPH_INTENT_PROMPT = """You are the Graph Intent Parser for MarineMind, a maritime vessel performance platform.

Your job is to extract structured graph parameters from a user's natural language request.

You MUST respond with ONLY valid JSON in this EXACT format:
{
  "graph_type": "line|bar|scatter|comparison|summary",
  "metric": "fuel_consumption_trend|speed_vs_consumption|rpm_performance|voyage_performance|weather_impact|fleet_comparison|anomaly_detection|vessel_summary|custom_trend",
  "vessel_name": "name of vessel mentioned, or null",
  "vessel_imo": "IMO number if mentioned, or null",
  "time_range": "7d|14d|30d|60d|90d|180d|365d|all|null",
  "date_from": "YYYY-MM-DD or null",
  "date_to": "YYYY-MM-DD or null",
  "voyage_number": "voyage number if mentioned, or null",
  "granularity": "daily|weekly|monthly|null",
  "x_axis": "field name for x-axis or null",
  "y_axis": "field name for y-axis or null",
  "compare_field": "secondary field to compare against, or null",
  "title": "A clear chart title for this graph",
  "interpretation_hint": "Brief note about what the user wants to understand"
}

RULES:
1. If the user says "last 30 days", set time_range to "30d"
2. If the user mentions a specific vessel name, extract it into vessel_name
3. If the user says "show trend" or "over time", prefer graph_type "line"
4. If the user says "compare", "vs", or "against", prefer graph_type "scatter" or "comparison"
5. If the user asks about "fuel" or "consumption", set metric to "fuel_consumption_trend" or "speed_vs_consumption"
6. If the user asks about "RPM vs speed" or "propulsion", set metric to "rpm_performance"
7. If the user asks about "voyage performance", set metric to "voyage_performance"
8. If the user asks about "weather impact" or "sea state", set metric to "weather_impact"
9. If the user asks about "fleet comparison" or "compare vessels", set metric to "fleet_comparison"
10. If the user asks about "anomalies" or "outliers", set metric to "anomaly_detection"
11. If no vessel is mentioned and it's not fleet comparison, set vessel_name to null
12. Default granularity for trends is "daily", for longer ranges use "weekly" or "monthly"
13. For "plot X against Y" or "X vs Y", extract x_axis and y_axis field names

Available metric fields: speed_avg, rpm_avg, fo_consumption, bf_consumption, fo_rob, bf_rob, 
me_load_percent, me_power_kw, sfoc, distance_sailed, slip_percent, wind_force, sea_state, 
draft_mean, me_exhaust_temp, cargo_quantity, hours_steaming

Respond with ONLY the JSON object. No explanation."""


def parse_graph_intent(user_query: str) -> dict:
    """
    Use LLM to extract structured graph parameters from a natural language query.
    """
    messages = [
        {"role": "system", "content": GRAPH_INTENT_PROMPT},
        {"role": "user", "content": user_query},
    ]

    raw = call_llm(messages, temperature=0.0, max_tokens=500)

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        intent = json.loads(cleaned)

        # Validate required fields with defaults
        intent.setdefault('graph_type', 'line')
        intent.setdefault('metric', 'fuel_consumption_trend')
        intent.setdefault('vessel_name', None)
        intent.setdefault('vessel_imo', None)
        intent.setdefault('time_range', '30d')
        intent.setdefault('date_from', None)
        intent.setdefault('date_to', None)
        intent.setdefault('voyage_number', None)
        intent.setdefault('granularity', None)
        intent.setdefault('x_axis', None)
        intent.setdefault('y_axis', None)
        intent.setdefault('compare_field', None)
        intent.setdefault('title', 'Vessel Performance')
        intent.setdefault('interpretation_hint', '')

        return intent

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse graph intent: {e}. Raw: {raw[:200]}")
        return {
            'graph_type': 'line',
            'metric': 'fuel_consumption_trend',
            'vessel_name': None,
            'vessel_imo': None,
            'time_range': '30d',
            'date_from': None,
            'date_to': None,
            'voyage_number': None,
            'granularity': 'daily',
            'x_axis': None,
            'y_axis': None,
            'compare_field': None,
            'title': 'Vessel Performance',
            'interpretation_hint': '',
        }


# ─────────────────────────────────────────────────────────────────────────────
# VESSEL RESOLUTION — match name/IMO to a database Vessel
# ─────────────────────────────────────────────────────────────────────────────

def resolve_vessel(vessel_name: str | None, vessel_imo: str | None) -> Vessel | None:
    """
    Fuzzy-match a vessel by name or exact-match by IMO number.
    Returns the Vessel instance or None.
    """
    if vessel_imo:
        try:
            return Vessel.objects.get(imo_number=vessel_imo)
        except Vessel.DoesNotExist:
            pass

    if vessel_name:
        # Exact match first
        try:
            return Vessel.objects.get(name__iexact=vessel_name)
        except Vessel.DoesNotExist:
            pass

        # Partial match
        matches = Vessel.objects.filter(name__icontains=vessel_name)
        if matches.count() == 1:
            return matches.first()
        if matches.count() > 1:
            return matches.first()  # best effort

        # Fuzzy match to tolerate minor typos in vessel names.
        all_vessel_names = list(Vessel.objects.values_list('name', flat=True))
        close = get_close_matches(vessel_name, all_vessel_names, n=1, cutoff=0.65)
        if close:
            try:
                return Vessel.objects.get(name=close[0])
            except Vessel.DoesNotExist:
                pass

    # If only one vessel exists, use it as default
    if Vessel.objects.count() == 1:
        return Vessel.objects.first()

    return None


# ─────────────────────────────────────────────────────────────────────────────
# DATE RANGE RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def resolve_date_range(intent: dict) -> tuple[date | None, date | None]:
    """Convert time_range or explicit dates from intent to (date_from, date_to)."""
    date_to = date.today()

    # Explicit dates take priority
    if intent.get('date_from'):
        try:
            from datetime import datetime
            df = datetime.strptime(intent['date_from'], '%Y-%m-%d').date()
            dt = date_to
            if intent.get('date_to'):
                dt = datetime.strptime(intent['date_to'], '%Y-%m-%d').date()
            return df, dt
        except (ValueError, TypeError):
            pass

    # Parse time_range like "30d", "90d"
    time_range = intent.get('time_range', '30d')
    if time_range and time_range != 'all' and time_range != 'null':
        try:
            days = int(time_range.rstrip('d'))
            return date_to - timedelta(days=days), date_to
        except (ValueError, TypeError):
            pass

    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHING — calls analytics engine based on parsed intent
# ─────────────────────────────────────────────────────────────────────────────

def fetch_graph_data(intent: dict, vessel: Vessel | None) -> dict:
    """
    Fetch the appropriate analytics data based on the parsed intent.
    """
    metric = intent.get('metric', 'fuel_consumption_trend')
    date_from, date_to = resolve_date_range(intent)
    granularity = intent.get('granularity') or 'daily'

    # Fleet comparison doesn't need a vessel
    if metric == 'fleet_comparison':
        return analytics_engine.get_fleet_comparison(
            vessel_ids=None, date_from=date_from, date_to=date_to,
        )

    # All other metrics need a vessel
    if not vessel:
        return {'error': 'no_vessel', 'message': 'Could not identify which vessel to analyze.'}

    vessel_id = str(vessel.id)

    METRIC_HANDLERS = {
        'fuel_consumption_trend': lambda: analytics_engine.get_fuel_consumption_trend(
            vessel_id, date_from, date_to, granularity,
        ),
        'speed_vs_consumption': lambda: analytics_engine.get_speed_vs_consumption(
            vessel_id, date_from, date_to,
        ),
        'rpm_performance': lambda: analytics_engine.get_rpm_performance(
            vessel_id, date_from, date_to,
        ),
        'voyage_performance': lambda: analytics_engine.get_voyage_performance(
            vessel_id, date_from, date_to,
        ),
        'weather_impact': lambda: analytics_engine.get_weather_impact(
            vessel_id, date_from, date_to,
        ),
        'anomaly_detection': lambda: analytics_engine.get_anomaly_flags(
            vessel_id, date_from, date_to,
        ),
        'vessel_summary': lambda: analytics_engine.get_vessel_summary(vessel_id),
        'custom_trend': lambda: _fetch_custom_trend(vessel_id, intent, date_from, date_to),
    }

    handler = METRIC_HANDLERS.get(metric)
    if handler:
        return handler()

    # Default to fuel consumption trend
    return analytics_engine.get_fuel_consumption_trend(
        vessel_id, date_from, date_to, granularity,
    )


def _fetch_custom_trend(vessel_id: str, intent: dict, date_from, date_to) -> dict:
    """
    Build a custom time-series from raw noon report data for non-standard metric requests.
    """
    from django.db.models.functions import Trunc
    from django.db.models import Avg, Count

    x_field = intent.get('x_axis') or 'report_date'
    y_field = intent.get('y_axis') or 'fo_consumption'
    compare = intent.get('compare_field')

    # Validate field names against NoonReport model fields
    valid_fields = {f.name for f in NoonReport._meta.get_fields()}
    if y_field not in valid_fields:
        y_field = 'fo_consumption'
    if compare and compare not in valid_fields:
        compare = None

    qs = NoonReport.objects.filter(vessel_id=vessel_id)
    if date_from:
        qs = qs.filter(report_date__gte=date_from)
    if date_to:
        qs = qs.filter(report_date__lte=date_to)

    # Time-series trend
    if x_field == 'report_date':
        fields_to_avg = {f'avg_{y_field}': Avg(y_field)}
        if compare:
            fields_to_avg[f'avg_{compare}'] = Avg(compare)

        data = (
            qs.annotate(period=Trunc('report_date', 'day'))
            .values('period')
            .annotate(report_count=Count('id'), **fields_to_avg)
            .order_by('period')
        )

        datasets = {f'avg_{y_field}': []}
        if compare:
            datasets[f'avg_{compare}'] = []

        labels = []
        for d in data:
            labels.append(d['period'].isoformat())
            datasets[f'avg_{y_field}'].append(
                round(float(d[f'avg_{y_field}']), 2) if d[f'avg_{y_field}'] else None
            )
            if compare:
                datasets[f'avg_{compare}'].append(
                    round(float(d[f'avg_{compare}']), 2) if d.get(f'avg_{compare}') else None
                )

        return {
            'metric': 'custom_trend',
            'labels': labels,
            'datasets': datasets,
            'y_field': y_field,
            'compare_field': compare,
        }

    # Scatter X vs Y
    values_fields = ['report_date', x_field, y_field]
    if compare:
        values_fields.append(compare)

    qs = qs.filter(**{f'{x_field}__isnull': False, f'{y_field}__isnull': False})
    rows = qs.values(*values_fields)

    data_points = []
    for r in rows:
        point = {
            'date': r['report_date'].isoformat(),
            x_field: round(float(r[x_field]), 2) if r.get(x_field) is not None else None,
            y_field: round(float(r[y_field]), 2) if r.get(y_field) is not None else None,
        }
        if compare and r.get(compare) is not None:
            point[compare] = round(float(r[compare]), 2)
        data_points.append(point)

    return {
        'metric': 'custom_trend',
        'x_field': x_field,
        'y_field': y_field,
        'compare_field': compare,
        'data_points': data_points,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH CONFIG GENERATOR — produces chart.js-compatible config for the frontend
# ─────────────────────────────────────────────────────────────────────────────

# Color palette for chart series
CHART_COLORS = [
    {'bg': 'rgba(0, 180, 216, 0.2)', 'border': '#00b4d8'},
    {'bg': 'rgba(255, 152, 0, 0.2)', 'border': '#ff9800'},
    {'bg': 'rgba(76, 175, 80, 0.2)', 'border': '#4caf50'},
    {'bg': 'rgba(244, 67, 54, 0.2)', 'border': '#f44336'},
    {'bg': 'rgba(156, 39, 176, 0.2)', 'border': '#9c27b0'},
    {'bg': 'rgba(255, 235, 59, 0.2)', 'border': '#ffeb3b'},
]

FIELD_LABELS = {
    'fo_consumption': 'FO Consumption (MT)',
    'bf_consumption': 'BF Consumption (MT)',
    'speed_avg': 'Average Speed (knots)',
    'rpm_avg': 'Average RPM',
    'me_load_percent': 'ME Load (%)',
    'me_power_kw': 'ME Power (kW)',
    'sfoc': 'SFOC (g/kWh)',
    'distance_sailed': 'Distance (NM)',
    'slip_percent': 'Slip (%)',
    'wind_force': 'Wind Force (Beaufort)',
    'sea_state': 'Sea State (Douglas)',
    'draft_mean': 'Mean Draft (m)',
    'me_exhaust_temp': 'Exhaust Temp (°C)',
    'cargo_quantity': 'Cargo (MT)',
    'hours_steaming': 'Steaming Hours',
    'avg_fo_consumption': 'Avg FO Consumption (MT)',
    'avg_bf_consumption': 'Avg BF Consumption (MT)',
    'total_fo_consumption': 'Total FO Consumption (MT)',
    'total_bf_consumption': 'Total BF Consumption (MT)',
}


def generate_graph_config(intent: dict, data: dict, vessel: Vessel | None) -> dict:
    """
    Transform analytics data + intent into a chart-ready configuration
    that the frontend can render directly with Chart.js or Recharts.
    """
    metric = intent.get('metric', 'fuel_consumption_trend')
    graph_type = intent.get('graph_type', 'line')
    vessel_name = vessel.name if vessel else 'Fleet'

    # Handle error case
    if 'error' in data:
        return {
            'type': 'error',
            'title': intent.get('title', 'Error'),
            'message': data.get('message', 'Unable to generate graph.'),
        }

    # Handle no data
    if metric == 'vessel_summary':
        if not data.get('has_data'):
            return {
                'type': 'error',
                'title': f'{vessel_name} — Summary',
                'message': 'No noon report data available for this vessel.',
            }
        return {
            'type': 'summary',
            'title': f'{vessel_name} — Performance Summary',
            'data': data,
        }

    # ── Time-series chart (fuel_consumption_trend, custom_trend with labels) ──
    if 'labels' in data and 'datasets' in data:
        datasets = []
        for idx, (key, values) in enumerate(data['datasets'].items()):
            color = CHART_COLORS[idx % len(CHART_COLORS)]
            datasets.append({
                'label': FIELD_LABELS.get(key, key.replace('_', ' ').title()),
                'data': values,
                'borderColor': color['border'],
                'backgroundColor': color['bg'],
                'fill': graph_type == 'bar',
                'tension': 0.3,
                'pointRadius': 3,
            })

        chart_type = 'bar' if graph_type == 'bar' else 'line'
        return {
            'type': 'chart',
            'chart_type': chart_type,
            'title': intent.get('title', f'{vessel_name} — {metric.replace("_", " ").title()}'),
            'chart_config': {
                'type': chart_type,
                'data': {
                    'labels': data['labels'],
                    'datasets': datasets,
                },
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': intent.get('title', ''),
                            'color': '#e3f2fd',
                        },
                        'legend': {
                            'labels': {'color': '#90caf9'},
                        },
                    },
                    'scales': {
                        'x': {
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                        'y': {
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                    },
                },
            },
            'raw_data': data,
        }

    # ── Scatter chart (speed_vs_consumption, rpm_performance, custom_trend with data_points) ──
    if 'data_points' in data:
        points = data['data_points']

        if metric == 'speed_vs_consumption':
            x_key, y_key = 'speed', 'fo_consumption'
        elif metric == 'rpm_performance':
            x_key, y_key = 'rpm', 'speed'
        elif metric == 'custom_trend':
            x_key = data.get('x_field', 'speed_avg')
            y_key = data.get('y_field', 'fo_consumption')
        else:
            x_key = 'speed'
            y_key = 'fo_consumption'

        scatter_data = [
            {'x': p.get(x_key), 'y': p.get(y_key)}
            for p in points
            if p.get(x_key) is not None and p.get(y_key) is not None
        ]

        color = CHART_COLORS[0]
        datasets = [{
            'label': f'{FIELD_LABELS.get(y_key, y_key)} vs {FIELD_LABELS.get(x_key, x_key)}',
            'data': scatter_data,
            'backgroundColor': color['border'],
            'borderColor': color['border'],
            'pointRadius': 5,
            'pointHoverRadius': 7,
        }]

        # If there's a compare field, add second dataset
        compare = data.get('compare_field') or intent.get('compare_field')
        if compare and any(p.get(compare) is not None for p in points):
            color2 = CHART_COLORS[1]
            scatter_data_2 = [
                {'x': p.get(x_key), 'y': p.get(compare)}
                for p in points
                if p.get(x_key) is not None and p.get(compare) is not None
            ]
            datasets.append({
                'label': f'{FIELD_LABELS.get(compare, compare)} vs {FIELD_LABELS.get(x_key, x_key)}',
                'data': scatter_data_2,
                'backgroundColor': color2['border'],
                'borderColor': color2['border'],
                'pointRadius': 5,
                'pointHoverRadius': 7,
            })

        return {
            'type': 'chart',
            'chart_type': 'scatter',
            'title': intent.get('title', f'{vessel_name} — {x_key} vs {y_key}'),
            'chart_config': {
                'type': 'scatter',
                'data': {'datasets': datasets},
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': intent.get('title', ''),
                            'color': '#e3f2fd',
                        },
                        'legend': {
                            'labels': {'color': '#90caf9'},
                        },
                    },
                    'scales': {
                        'x': {
                            'title': {
                                'display': True,
                                'text': FIELD_LABELS.get(x_key, x_key),
                                'color': '#90caf9',
                            },
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                        'y': {
                            'title': {
                                'display': True,
                                'text': FIELD_LABELS.get(y_key, y_key),
                                'color': '#90caf9',
                            },
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                    },
                },
            },
            'raw_data': data,
        }

    # ── Bar chart for voyage performance ──
    if 'voyages' in data:
        voyages = data['voyages']
        if not voyages:
            return {
                'type': 'error',
                'title': intent.get('title', 'Voyage Performance'),
                'message': 'No voyage data found for the given filters.',
            }

        labels = [v['voyage_number'] for v in voyages]
        datasets = [
            {
                'label': 'Total FO (MT)',
                'data': [v.get('total_fo_consumption') for v in voyages],
                'backgroundColor': CHART_COLORS[0]['bg'],
                'borderColor': CHART_COLORS[0]['border'],
                'borderWidth': 2,
            },
            {
                'label': 'Avg Speed (knots)',
                'data': [v.get('avg_speed') for v in voyages],
                'backgroundColor': CHART_COLORS[1]['bg'],
                'borderColor': CHART_COLORS[1]['border'],
                'borderWidth': 2,
            },
        ]

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'title': intent.get('title', f'{vessel_name} — Voyage Performance'),
            'chart_config': {
                'type': 'bar',
                'data': {'labels': labels, 'datasets': datasets},
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': intent.get('title', 'Voyage Performance'),
                            'color': '#e3f2fd',
                        },
                        'legend': {'labels': {'color': '#90caf9'}},
                    },
                    'scales': {
                        'x': {
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                        'y': {
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                    },
                },
            },
            'raw_data': data,
        }

    # ── Bar chart for weather impact ──
    if 'by_beaufort_scale' in data:
        items = data['by_beaufort_scale']
        if not items:
            return {
                'type': 'error',
                'title': intent.get('title', 'Weather Impact'),
                'message': 'No weather data available.',
            }

        labels = [f'BF {w["wind_force"]}' for w in items]
        datasets = [
            {
                'label': 'Avg Speed (knots)',
                'data': [w.get('avg_speed') for w in items],
                'backgroundColor': CHART_COLORS[0]['bg'],
                'borderColor': CHART_COLORS[0]['border'],
                'borderWidth': 2,
            },
            {
                'label': 'Avg FO Consumption (MT)',
                'data': [w.get('avg_fo_consumption') for w in items],
                'backgroundColor': CHART_COLORS[1]['bg'],
                'borderColor': CHART_COLORS[1]['border'],
                'borderWidth': 2,
            },
        ]

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'title': intent.get('title', f'{vessel_name} — Weather Impact on Performance'),
            'chart_config': {
                'type': 'bar',
                'data': {'labels': labels, 'datasets': datasets},
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': intent.get('title', ''),
                            'color': '#e3f2fd',
                        },
                        'legend': {'labels': {'color': '#90caf9'}},
                    },
                    'scales': {
                        'x': {
                            'title': {
                                'display': True,
                                'text': 'Wind Force (Beaufort Scale)',
                                'color': '#90caf9',
                            },
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                        'y': {
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                    },
                },
            },
            'raw_data': data,
        }

    # ── Fleet comparison bar chart ──
    if 'vessels' in data:
        vessels_data = data['vessels']
        if not vessels_data:
            return {
                'type': 'error',
                'title': 'Fleet Comparison',
                'message': 'No fleet data available.',
            }

        labels = [v['vessel_name'] for v in vessels_data]
        datasets = [
            {
                'label': 'Avg FO Consumption (MT)',
                'data': [v.get('avg_fo_consumption') for v in vessels_data],
                'backgroundColor': CHART_COLORS[0]['bg'],
                'borderColor': CHART_COLORS[0]['border'],
                'borderWidth': 2,
            },
            {
                'label': 'Avg Speed (knots)',
                'data': [v.get('avg_speed') for v in vessels_data],
                'backgroundColor': CHART_COLORS[1]['bg'],
                'borderColor': CHART_COLORS[1]['border'],
                'borderWidth': 2,
            },
        ]

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'title': intent.get('title', 'Fleet Performance Comparison'),
            'chart_config': {
                'type': 'bar',
                'data': {'labels': labels, 'datasets': datasets},
                'options': {
                    'responsive': True,
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': intent.get('title', 'Fleet Comparison'),
                            'color': '#e3f2fd',
                        },
                        'legend': {'labels': {'color': '#90caf9'}},
                    },
                    'scales': {
                        'x': {
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                        'y': {
                            'ticks': {'color': '#64b5f6'},
                            'grid': {'color': 'rgba(100,181,246,0.1)'},
                        },
                    },
                },
            },
            'raw_data': data,
        }

    # ── Anomaly table ──
    if 'flags' in data:
        return {
            'type': 'table',
            'title': intent.get('title', f'{vessel_name} — Anomaly Detection'),
            'columns': ['Date', 'Field', 'Value', 'Expected Range', 'Label'],
            'rows': [
                [f['report_date'], f['field'], f['value'],
                 f"{f['expected_range'][0]} – {f['expected_range'][1]}", f['label']]
                for f in data.get('flags', [])[:50]
            ],
            'total_flags': data.get('total_flags', 0),
            'raw_data': data,
        }

    # Fallback
    return {
        'type': 'error',
        'title': intent.get('title', 'Graph'),
        'message': 'Unable to generate a graph from the available data.',
    }


# ─────────────────────────────────────────────────────────────────────────────
# INTERPRETATION — LLM generates a brief analysis of the graph data
# ─────────────────────────────────────────────────────────────────────────────

INTERPRET_PROMPT = """You are a marine performance analyst for MarineMind.

Given graph data from vessel noon reports, provide a brief 2-3 sentence interpretation.
Focus on: trends, anomalies, efficiency insights, or operational recommendations.

RULES:
- Be concise and technical
- Do NOT use markdown formatting
- Speak as a professional maritime analyst
- If data is sparse, note that more data would improve accuracy"""


def generate_interpretation(intent: dict, data: dict, vessel: Vessel | None) -> str:
    """Generate a brief LLM interpretation of the graph results."""
    vessel_name = vessel.name if vessel else 'Fleet'

    # Build a compact data summary for the LLM
    summary = f"Vessel: {vessel_name}\n"
    summary += f"Metric: {intent.get('metric', 'unknown')}\n"

    if 'labels' in data and 'datasets' in data:
        count = len(data['labels'])
        summary += f"Data points: {count}\n"
        if count > 0:
            summary += f"Period: {data['labels'][0]} to {data['labels'][-1]}\n"
            for key, values in data['datasets'].items():
                non_null = [v for v in values if v is not None]
                if non_null:
                    summary += f"{key}: min={min(non_null)}, max={max(non_null)}, avg={round(sum(non_null)/len(non_null), 2)}\n"
    elif 'data_points' in data:
        summary += f"Scatter points: {len(data['data_points'])}\n"
    elif 'voyages' in data:
        summary += f"Voyages: {len(data['voyages'])}\n"
    elif 'by_beaufort_scale' in data:
        summary += f"Weather groups: {len(data['by_beaufort_scale'])}\n"

    summary += f"User intent: {intent.get('interpretation_hint', 'general analysis')}\n"

    messages = [
        {"role": "system", "content": INTERPRET_PROMPT},
        {"role": "user", "content": summary},
    ]

    return call_llm(messages, temperature=0.3, max_tokens=200)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT — run_graph_agent
# ─────────────────────────────────────────────────────────────────────────────

def run_graph_agent(user_query: str) -> dict:
    """
    Full graph generation pipeline:
      1. Parse intent (LLM)
      2. Resolve vessel
      3. Fetch data (analytics engine)
      4. Generate graph config
      5. Generate interpretation (LLM)

    Returns:
        dict with: graph_config, interpretation, intent, agent info
    """
    logger.info(f"[Graph Agent] Processing: {user_query[:80]}")

    # Step 1: Parse intent
    intent = parse_graph_intent(user_query)
    query_lower = user_query.lower()

    # Bias to monthly granularity for "month breakdown"/"monthly" language.
    if (
        not intent.get('granularity')
        and ('month breakdown' in query_lower or 'monthly' in query_lower)
    ):
        intent['granularity'] = 'monthly'

    logger.info(f"[Graph Agent] Intent: metric={intent['metric']}, "
                f"vessel={intent.get('vessel_name')}, range={intent.get('time_range')}")

    # Step 2: Resolve vessel
    vessel = resolve_vessel(intent.get('vessel_name'), intent.get('vessel_imo'))
    if vessel:
        logger.info(f"[Graph Agent] Resolved vessel: {vessel.name} (IMO: {vessel.imo_number})")

    # Step 3: Fetch data
    data = fetch_graph_data(intent, vessel)

    # Step 4: Generate graph config
    graph_config = generate_graph_config(intent, data, vessel)

    # Step 5: Generate interpretation
    interpretation = ''
    if graph_config.get('type') != 'error':
        try:
            interpretation = generate_interpretation(intent, data, vessel)
        except Exception as e:
            logger.warning(f"[Graph Agent] Interpretation failed: {e}")
            interpretation = ''

    # Build the response
    available_vessels = list(
        Vessel.objects.values_list('name', flat=True).order_by('name')
    )

    answer_text = interpretation or intent.get('title', 'Graph generated.')
    if graph_config.get('type') == 'error':
        answer_text = graph_config.get('message') or answer_text

    return {
        'answer': answer_text,
        'graph': graph_config,
        'intent': {
            'metric': intent.get('metric'),
            'graph_type': intent.get('graph_type'),
            'vessel': vessel.name if vessel else None,
            'time_range': intent.get('time_range'),
            'granularity': intent.get('granularity'),
            'title': intent.get('title'),
        },
        'available_vessels': available_vessels,
        'agent': 'graph',
        'sources': [],
        'citation_map': {},
    }
