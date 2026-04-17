"""
Performance analytics engine for vessel noon report data.
Provides aggregated metrics, trends, and graph-ready data.
"""
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Avg, Sum, Min, Max, Count, F, Q, StdDev
from django.db.models.functions import Trunc

from administration.models import NoonReport, Vessel


# ─────────────────────────────────────────────────────────────────────────────
# VESSEL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def get_vessel_summary(vessel_id: str) -> dict:
    """
    Overall performance summary for a vessel: totals, averages, date range.
    """
    qs = NoonReport.objects.filter(vessel_id=vessel_id)
    if not qs.exists():
        return {'vessel_id': str(vessel_id), 'has_data': False}

    stats = qs.aggregate(
        total_reports=Count('id'),
        date_from=Min('report_date'),
        date_to=Max('report_date'),
        avg_speed=Avg('speed_avg'),
        avg_rpm=Avg('rpm_avg'),
        avg_fo_consumption=Avg('fo_consumption'),
        total_fo_consumption=Sum('fo_consumption'),
        total_bf_consumption=Sum('bf_consumption'),
        total_distance=Sum('distance_sailed'),
        avg_me_load=Avg('me_load_percent'),
        avg_sfoc=Avg('sfoc'),
        avg_slip=Avg('slip_percent'),
    )

    return {
        'vessel_id': str(vessel_id),
        'has_data': True,
        'total_reports': stats['total_reports'],
        'date_from': stats['date_from'],
        'date_to': stats['date_to'],
        'avg_speed_knots': _round_decimal(stats['avg_speed']),
        'avg_rpm': _round_decimal(stats['avg_rpm']),
        'avg_fo_consumption_mt': _round_decimal(stats['avg_fo_consumption']),
        'total_fo_consumption_mt': _round_decimal(stats['total_fo_consumption']),
        'total_bf_consumption_mt': _round_decimal(stats['total_bf_consumption']),
        'total_distance_nm': _round_decimal(stats['total_distance']),
        'avg_me_load_percent': _round_decimal(stats['avg_me_load']),
        'avg_sfoc': _round_decimal(stats['avg_sfoc']),
        'avg_slip_percent': _round_decimal(stats['avg_slip']),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUEL CONSUMPTION TRENDS
# ─────────────────────────────────────────────────────────────────────────────

def get_fuel_consumption_trend(
    vessel_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
    granularity: str = 'daily',
) -> dict:
    """
    Fuel consumption trend over time (daily, weekly, or monthly aggregation).
    Returns graph-ready data with labels and datasets.
    """
    qs = _filtered_qs(vessel_id, date_from, date_to)
    trunc_fn = _get_trunc_fn(granularity)

    data = (
        qs.annotate(period=trunc_fn('report_date'))
        .values('period')
        .annotate(
            avg_fo=Avg('fo_consumption'),
            avg_bf=Avg('bf_consumption'),
            total_fo=Sum('fo_consumption'),
            total_bf=Sum('bf_consumption'),
            report_count=Count('id'),
        )
        .order_by('period')
    )

    return {
        'metric': 'fuel_consumption',
        'granularity': granularity,
        'labels': [d['period'].isoformat() for d in data],
        'datasets': {
            'avg_fo_consumption': [_to_float(d['avg_fo']) for d in data],
            'avg_bf_consumption': [_to_float(d['avg_bf']) for d in data],
            'total_fo_consumption': [_to_float(d['total_fo']) for d in data],
            'total_bf_consumption': [_to_float(d['total_bf']) for d in data],
        },
        'report_counts': [d['report_count'] for d in data],
    }


# ─────────────────────────────────────────────────────────────────────────────
# SPEED VS FUEL EFFICIENCY
# ─────────────────────────────────────────────────────────────────────────────

def get_speed_vs_consumption(
    vessel_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    Scatter data: speed vs FO consumption for efficiency analysis.
    Each point is one noon report.
    """
    qs = _filtered_qs(vessel_id, date_from, date_to).filter(
        speed_avg__isnull=False,
        fo_consumption__isnull=False,
    ).values('report_date', 'speed_avg', 'fo_consumption', 'distance_sailed', 'cargo_condition')

    return {
        'metric': 'speed_vs_consumption',
        'data_points': [
            {
                'date': d['report_date'].isoformat(),
                'speed': _to_float(d['speed_avg']),
                'fo_consumption': _to_float(d['fo_consumption']),
                'distance': _to_float(d.get('distance_sailed')),
                'cargo_condition': d.get('cargo_condition') or 'unknown',
            }
            for d in qs
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# RPM VS PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

def get_rpm_performance(
    vessel_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    RPM vs speed, consumption, and load — for propulsion analysis.
    """
    qs = _filtered_qs(vessel_id, date_from, date_to).filter(
        rpm_avg__isnull=False,
    ).values(
        'report_date', 'rpm_avg', 'speed_avg', 'fo_consumption',
        'me_load_percent', 'slip_percent', 'sfoc',
    )

    return {
        'metric': 'rpm_performance',
        'data_points': [
            {
                'date': d['report_date'].isoformat(),
                'rpm': _to_float(d['rpm_avg']),
                'speed': _to_float(d.get('speed_avg')),
                'fo_consumption': _to_float(d.get('fo_consumption')),
                'me_load_percent': _to_float(d.get('me_load_percent')),
                'slip_percent': _to_float(d.get('slip_percent')),
                'sfoc': _to_float(d.get('sfoc')),
            }
            for d in qs
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# VOYAGE PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

def get_voyage_performance(
    vessel_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    Aggregated performance per voyage number.
    """
    qs = _filtered_qs(vessel_id, date_from, date_to).exclude(
        voyage_number='',
    )

    voyages = (
        qs.values('voyage_number')
        .annotate(
            report_count=Count('id'),
            date_from=Min('report_date'),
            date_to=Max('report_date'),
            avg_speed=Avg('speed_avg'),
            avg_rpm=Avg('rpm_avg'),
            total_fo=Sum('fo_consumption'),
            total_bf=Sum('bf_consumption'),
            total_distance=Sum('distance_sailed'),
            avg_sfoc=Avg('sfoc'),
            avg_me_load=Avg('me_load_percent'),
        )
        .order_by('-date_from')
    )

    return {
        'metric': 'voyage_performance',
        'voyages': [
            {
                'voyage_number': v['voyage_number'],
                'report_count': v['report_count'],
                'date_from': v['date_from'].isoformat() if v['date_from'] else None,
                'date_to': v['date_to'].isoformat() if v['date_to'] else None,
                'avg_speed': _to_float(v['avg_speed']),
                'avg_rpm': _to_float(v['avg_rpm']),
                'total_fo_consumption': _to_float(v['total_fo']),
                'total_bf_consumption': _to_float(v['total_bf']),
                'total_distance': _to_float(v['total_distance']),
                'avg_sfoc': _to_float(v['avg_sfoc']),
                'avg_me_load': _to_float(v['avg_me_load']),
            }
            for v in voyages
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER IMPACT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def get_weather_impact(
    vessel_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    Average performance grouped by wind force (Beaufort scale) to show weather impact.
    """
    qs = _filtered_qs(vessel_id, date_from, date_to).filter(
        wind_force__isnull=False,
    )

    by_wind = (
        qs.values('wind_force')
        .annotate(
            report_count=Count('id'),
            avg_speed=Avg('speed_avg'),
            avg_fo_consumption=Avg('fo_consumption'),
            avg_slip=Avg('slip_percent'),
        )
        .order_by('wind_force')
    )

    return {
        'metric': 'weather_impact',
        'by_beaufort_scale': [
            {
                'wind_force': w['wind_force'],
                'report_count': w['report_count'],
                'avg_speed': _to_float(w['avg_speed']),
                'avg_fo_consumption': _to_float(w['avg_fo_consumption']),
                'avg_slip': _to_float(w['avg_slip']),
            }
            for w in by_wind
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ANOMALY FLAGS (placeholder for future ML integration)
# ─────────────────────────────────────────────────────────────────────────────

def get_anomaly_flags(
    vessel_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    Simple statistical anomaly detection based on deviations from vessel averages.
    Flags reports where key metrics deviate > 2 standard deviations from the mean.
    """
    qs = _filtered_qs(vessel_id, date_from, date_to)
    if qs.count() < 10:
        return {'metric': 'anomaly_flags', 'flags': [], 'message': 'Insufficient data (need at least 10 reports).'}

    # Calculate stats for key fields
    stats = qs.aggregate(
        avg_fo=Avg('fo_consumption'), std_fo=StdDev('fo_consumption'),
        avg_speed=Avg('speed_avg'), std_speed=StdDev('speed_avg'),
        avg_rpm=Avg('rpm_avg'), std_rpm=StdDev('rpm_avg'),
        avg_sfoc=Avg('sfoc'), std_sfoc=StdDev('sfoc'),
    )

    flags = []
    check_fields = [
        ('fo_consumption', 'avg_fo', 'std_fo', 'High fuel consumption'),
        ('speed_avg', 'avg_speed', 'std_speed', 'Abnormal speed'),
        ('rpm_avg', 'avg_rpm', 'std_rpm', 'Abnormal RPM'),
        ('sfoc', 'avg_sfoc', 'std_sfoc', 'Abnormal SFOC'),
    ]

    for field, avg_key, std_key, label in check_fields:
        avg_val = stats.get(avg_key)
        std_val = stats.get(std_key)
        if avg_val is None or std_val is None or std_val == 0:
            continue

        threshold = 2
        lower = float(avg_val) - threshold * float(std_val)
        upper = float(avg_val) + threshold * float(std_val)

        anomalous = qs.filter(
            **{f'{field}__isnull': False}
        ).exclude(
            **{f'{field}__gte': Decimal(str(lower)), f'{field}__lte': Decimal(str(upper))}
        ).values('id', 'report_date', field)

        for a in anomalous:
            flags.append({
                'report_id': str(a['id']),
                'report_date': a['report_date'].isoformat(),
                'field': field,
                'value': _to_float(a[field]),
                'expected_range': [round(lower, 2), round(upper, 2)],
                'label': label,
            })

    # Sort by date
    flags.sort(key=lambda x: x['report_date'], reverse=True)

    return {
        'metric': 'anomaly_flags',
        'total_flags': len(flags),
        'flags': flags[:100],  # cap at 100
    }


# ─────────────────────────────────────────────────────────────────────────────
# FLEET COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def get_fleet_comparison(
    vessel_ids: list[str] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """
    Compare key metrics across multiple vessels (or entire fleet).
    """
    qs = NoonReport.objects.all()
    if vessel_ids:
        qs = qs.filter(vessel_id__in=vessel_ids)
    if date_from:
        qs = qs.filter(report_date__gte=date_from)
    if date_to:
        qs = qs.filter(report_date__lte=date_to)

    by_vessel = (
        qs.values('vessel__name', 'vessel_id')
        .annotate(
            report_count=Count('id'),
            avg_speed=Avg('speed_avg'),
            avg_fo_consumption=Avg('fo_consumption'),
            total_distance=Sum('distance_sailed'),
            avg_sfoc=Avg('sfoc'),
            avg_me_load=Avg('me_load_percent'),
        )
        .order_by('vessel__name')
    )

    return {
        'metric': 'fleet_comparison',
        'vessels': [
            {
                'vessel_id': str(v['vessel_id']),
                'vessel_name': v['vessel__name'],
                'report_count': v['report_count'],
                'avg_speed': _to_float(v['avg_speed']),
                'avg_fo_consumption': _to_float(v['avg_fo_consumption']),
                'total_distance': _to_float(v['total_distance']),
                'avg_sfoc': _to_float(v['avg_sfoc']),
                'avg_me_load': _to_float(v['avg_me_load']),
            }
            for v in by_vessel
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _filtered_qs(vessel_id, date_from=None, date_to=None):
    qs = NoonReport.objects.filter(vessel_id=vessel_id)
    if date_from:
        qs = qs.filter(report_date__gte=date_from)
    if date_to:
        qs = qs.filter(report_date__lte=date_to)
    return qs


def _get_trunc_fn(granularity):
    """Return a Trunc expression factory compatible with DateField on SQLite."""
    kind_map = {'weekly': 'week', 'monthly': 'month'}
    kind = kind_map.get(granularity, 'day')
    return lambda field: Trunc(field, kind)


def _round_decimal(val, places=2):
    if val is None:
        return None
    return round(float(val), places)


def _to_float(val):
    if val is None:
        return None
    return round(float(val), 2)
