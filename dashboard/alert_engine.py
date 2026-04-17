"""
Automatic Alert Generation Engine.

Analyses incoming data and creates Alert records when anomalies are detected.
Called from Django signals and service hooks throughout the system.

ALERT TRIGGERS
──────────────
1. Fuel Anomaly       → NoonReport FO consumption > 1.5× vessel 30-day avg
2. Performance        → Speed drop, high exhaust temp, high slip, SFOC spike
3. Ingestion Issue    → Document processing failure
4. Import Issue       → Noon report import with errors
5. Diagnosis Severity → Diagnosis agent flags high/critical severity
"""
import logging
from datetime import timedelta
from decimal import Decimal
from django.db.models import Avg
from django.utils import timezone

logger = logging.getLogger(__name__)


def _create_alert(alert_type, severity, title, message, vessel=None, details=None):
    """Helper to create an Alert and avoid import-time circular refs."""
    from dashboard.models import Alert
    alert = Alert.objects.create(
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        vessel=vessel,
        details=details or {},
    )
    logger.info(f"[AlertEngine] Created alert: [{severity}] {title}")
    return alert


# ─────────────────────────────────────────────────────────────────────────────
# 1. NOON REPORT ANOMALY CHECKS  (called on NoonReport post_save)
# ─────────────────────────────────────────────────────────────────────────────

def check_noon_report(noon_report) -> list:
    """Run all anomaly checks on a newly created/updated NoonReport."""
    alerts = []
    alerts += _check_fuel_anomaly(noon_report)
    alerts += _check_performance_anomaly(noon_report)
    return alerts


def _get_vessel_averages(vessel, exclude_report=None, days=30):
    """Get vessel's rolling averages over the last N days."""
    from administration.models import NoonReport
    cutoff = timezone.now().date() - timedelta(days=days)
    qs = NoonReport.objects.filter(vessel=vessel, report_date__gte=cutoff)
    if exclude_report:
        qs = qs.exclude(pk=exclude_report.pk)
    if qs.count() < 3:
        return None  # Not enough data for meaningful comparison
    return qs.aggregate(
        avg_fo=Avg('fo_consumption'),
        avg_speed=Avg('speed_avg'),
        avg_rpm=Avg('rpm_avg'),
        avg_sfoc=Avg('sfoc'),
        avg_exhaust=Avg('me_exhaust_temp'),
        avg_slip=Avg('slip_percent'),
    )


def _check_fuel_anomaly(report) -> list:
    """Detect abnormal fuel consumption."""
    alerts = []
    if not report.fo_consumption:
        return alerts

    avgs = _get_vessel_averages(report.vessel, exclude_report=report)
    if not avgs or not avgs['avg_fo']:
        return alerts

    ratio = float(report.fo_consumption) / float(avgs['avg_fo'])

    if ratio >= 2.0:
        alerts.append(_create_alert(
            alert_type='fuel',
            severity='error',
            title=f'Critical fuel spike — {report.vessel.name}',
            message=(
                f"Fuel consumption on {report.report_date} is {report.fo_consumption} MT, "
                f"which is {ratio:.1f}× the 30-day average of {avgs['avg_fo']:.2f} MT. "
                f"Investigate possible fuel system malfunction or incorrect reporting."
            ),
            vessel=report.vessel,
            details={
                'report_date': str(report.report_date),
                'current_value': float(report.fo_consumption),
                'average_value': round(float(avgs['avg_fo']), 2),
                'ratio': round(ratio, 2),
                'metric': 'fo_consumption',
            },
        ))
    elif ratio >= 1.5:
        alerts.append(_create_alert(
            alert_type='fuel',
            severity='warning',
            title=f'High fuel consumption — {report.vessel.name}',
            message=(
                f"Fuel consumption on {report.report_date} is {report.fo_consumption} MT, "
                f"which is {ratio:.1f}× the 30-day average of {avgs['avg_fo']:.2f} MT."
            ),
            vessel=report.vessel,
            details={
                'report_date': str(report.report_date),
                'current_value': float(report.fo_consumption),
                'average_value': round(float(avgs['avg_fo']), 2),
                'ratio': round(ratio, 2),
                'metric': 'fo_consumption',
            },
        ))

    # Low fuel ROB warning
    if report.fo_rob is not None and report.fo_rob < Decimal('50'):
        sev = 'critical' if report.fo_rob < Decimal('20') else 'warning'
        alerts.append(_create_alert(
            alert_type='fuel',
            severity=sev,
            title=f'Low fuel remaining — {report.vessel.name}',
            message=(
                f"Fuel oil ROB on {report.report_date} is only {report.fo_rob} MT. "
                f"Arrange bunkering immediately." if sev == 'critical'
                else f"Fuel oil ROB on {report.report_date} is {report.fo_rob} MT. "
                     f"Consider scheduling bunkering."
            ),
            vessel=report.vessel,
            details={
                'report_date': str(report.report_date),
                'fo_rob': float(report.fo_rob),
                'metric': 'fo_rob',
            },
        ))

    return alerts


def _check_performance_anomaly(report) -> list:
    """Detect speed, exhaust temp, slip, and SFOC anomalies."""
    alerts = []
    vessel = report.vessel
    avgs = _get_vessel_averages(vessel, exclude_report=report)

    # ── Speed drop vs ordered speed ──
    if report.speed_avg and report.speed_ordered:
        speed_ratio = float(report.speed_avg) / float(report.speed_ordered)
        if speed_ratio < 0.75:
            alerts.append(_create_alert(
                alert_type='performance',
                severity='error',
                title=f'Significant speed drop — {vessel.name}',
                message=(
                    f"Actual speed {report.speed_avg} kn is only {speed_ratio:.0%} of "
                    f"ordered speed {report.speed_ordered} kn on {report.report_date}. "
                    f"Check hull fouling, weather, or engine issues."
                ),
                vessel=vessel,
                details={
                    'report_date': str(report.report_date),
                    'speed_avg': float(report.speed_avg),
                    'speed_ordered': float(report.speed_ordered),
                    'ratio': round(speed_ratio, 2),
                    'metric': 'speed_avg',
                },
            ))
        elif speed_ratio < 0.85:
            alerts.append(_create_alert(
                alert_type='performance',
                severity='warning',
                title=f'Speed below ordered — {vessel.name}',
                message=(
                    f"Actual speed {report.speed_avg} kn is {speed_ratio:.0%} of "
                    f"ordered speed {report.speed_ordered} kn on {report.report_date}."
                ),
                vessel=vessel,
                details={
                    'report_date': str(report.report_date),
                    'speed_avg': float(report.speed_avg),
                    'speed_ordered': float(report.speed_ordered),
                    'ratio': round(speed_ratio, 2),
                    'metric': 'speed_avg',
                },
            ))

    # ── High exhaust temperature ──
    if report.me_exhaust_temp:
        temp = float(report.me_exhaust_temp)
        if temp > 450:
            alerts.append(_create_alert(
                alert_type='performance',
                severity='critical',
                title=f'Critical exhaust temperature — {vessel.name}',
                message=(
                    f"Main engine exhaust temperature is {temp}°C on {report.report_date}. "
                    f"Exceeds 450°C safety threshold. Risk of turbocharger damage. "
                    f"Reduce load immediately and inspect."
                ),
                vessel=vessel,
                details={'report_date': str(report.report_date), 'value': temp, 'metric': 'me_exhaust_temp'},
            ))
        elif temp > 400:
            alerts.append(_create_alert(
                alert_type='performance',
                severity='warning',
                title=f'High exhaust temperature — {vessel.name}',
                message=(
                    f"Main engine exhaust temperature is {temp}°C on {report.report_date}. "
                    f"Monitor closely and check turbocharger condition."
                ),
                vessel=vessel,
                details={'report_date': str(report.report_date), 'value': temp, 'metric': 'me_exhaust_temp'},
            ))

    # ── High slip percentage ──
    if report.slip_percent:
        slip = float(report.slip_percent)
        if slip > 25:
            alerts.append(_create_alert(
                alert_type='performance',
                severity='error',
                title=f'Excessive propeller slip — {vessel.name}',
                message=(
                    f"Propeller slip is {slip}% on {report.report_date}. "
                    f"Check propeller condition, hull fouling, or shallow water effects."
                ),
                vessel=vessel,
                details={'report_date': str(report.report_date), 'value': slip, 'metric': 'slip_percent'},
            ))
        elif slip > 15:
            alerts.append(_create_alert(
                alert_type='performance',
                severity='warning',
                title=f'High propeller slip — {vessel.name}',
                message=f"Propeller slip is {slip}% on {report.report_date}.",
                vessel=vessel,
                details={'report_date': str(report.report_date), 'value': slip, 'metric': 'slip_percent'},
            ))

    # ── SFOC spike ──
    if avgs and avgs['avg_sfoc'] and report.sfoc:
        sfoc_ratio = float(report.sfoc) / float(avgs['avg_sfoc'])
        if sfoc_ratio >= 1.5:
            alerts.append(_create_alert(
                alert_type='performance',
                severity='warning',
                title=f'SFOC spike — {vessel.name}',
                message=(
                    f"SFOC is {report.sfoc} g/kWh on {report.report_date}, "
                    f"which is {sfoc_ratio:.1f}× the 30-day average of {avgs['avg_sfoc']:.1f} g/kWh."
                ),
                vessel=vessel,
                details={
                    'report_date': str(report.report_date),
                    'current_value': float(report.sfoc),
                    'average_value': round(float(avgs['avg_sfoc']), 1),
                    'ratio': round(sfoc_ratio, 2),
                    'metric': 'sfoc',
                },
            ))

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
# 2. DOCUMENT INGESTION FAILURE  (called from ingestion service)
# ─────────────────────────────────────────────────────────────────────────────

def alert_ingestion_failure(document):
    """Create an alert when document processing fails."""
    return _create_alert(
        alert_type='ingestion',
        severity='error',
        title=f'Document processing failed — {document.title}',
        message=(
            f"Document \"{document.title}\" failed to process. "
            f"Error: {document.error_message or 'Unknown error'}"
        ),
        details={
            'document_id': str(document.id),
            'document_title': document.title,
            'error': document.error_message or '',
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. NOON REPORT IMPORT ISSUES  (called from analytics service)
# ─────────────────────────────────────────────────────────────────────────────

def alert_import_issues(import_job):
    """Create an alert when a noon report import has failures."""
    if import_job.status == 'failed':
        return _create_alert(
            alert_type='ingestion',
            severity='error',
            title=f'Noon report import failed — {import_job.original_filename}',
            message=(
                f"Import of \"{import_job.original_filename}\" for vessel "
                f"{import_job.vessel.name} failed completely. "
                f"Errors: {'; '.join(import_job.error_summary[:3]) if import_job.error_summary else 'Unknown'}"
            ),
            vessel=import_job.vessel,
            details={
                'import_id': str(import_job.id),
                'filename': import_job.original_filename,
                'errors': import_job.error_summary[:5] if import_job.error_summary else [],
            },
        )
    elif import_job.status == 'completed_with_errors' and import_job.failed_rows:
        return _create_alert(
            alert_type='ingestion',
            severity='warning',
            title=f'Import partially failed — {import_job.original_filename}',
            message=(
                f"Import of \"{import_job.original_filename}\" for {import_job.vessel.name}: "
                f"{import_job.successful_rows} succeeded, {import_job.failed_rows} failed, "
                f"{import_job.skipped_rows} skipped out of {import_job.total_rows} rows."
            ),
            vessel=import_job.vessel,
            details={
                'import_id': str(import_job.id),
                'filename': import_job.original_filename,
                'successful': import_job.successful_rows,
                'failed': import_job.failed_rows,
                'skipped': import_job.skipped_rows,
                'errors': import_job.error_summary[:5] if import_job.error_summary else [],
            },
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 4. DIAGNOSIS SEVERITY ALERT  (called from chatbot api_views)
# ─────────────────────────────────────────────────────────────────────────────

def alert_diagnosis_severity(diagnosis_data, session_id=None):
    """Create an alert when the diagnosis agent detects a high/critical issue."""
    severity = diagnosis_data.get('severity', '').lower()
    if severity not in ('high', 'critical'):
        return None

    category = diagnosis_data.get('category', 'unknown')
    symptoms = diagnosis_data.get('symptoms', [])
    components = diagnosis_data.get('affected_components', [])
    vessel_name = diagnosis_data.get('vessel_name', '')

    # Try to find the vessel object
    vessel = None
    if vessel_name:
        from administration.models import Vessel
        vessel = Vessel.objects.filter(name__icontains=vessel_name).first()

    alert_severity = 'critical' if severity == 'critical' else 'error'

    return _create_alert(
        alert_type='performance',
        severity=alert_severity,
        title=f'{severity.upper()} severity diagnosis — {category}',
        message=(
            f"Diagnosis agent detected a {severity}-severity issue in "
            f"{category.replace('_', ' ')}. "
            f"Symptoms: {', '.join(symptoms[:3]) if symptoms else 'N/A'}. "
            f"Affected components: {', '.join(components[:3]) if components else 'N/A'}."
        ),
        vessel=vessel,
        details={
            'diagnosis_severity': severity,
            'category': category,
            'symptoms': symptoms,
            'affected_components': components,
            'vessel_name': vessel_name,
            'session_id': str(session_id) if session_id else None,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. QUERY PIPELINE FAILURE  (called from chatbot api_views on exception)
# ─────────────────────────────────────────────────────────────────────────────

def alert_query_failure(error_message, session_id=None):
    """Create an alert when the query pipeline encounters an error."""
    return _create_alert(
        alert_type='query',
        severity='error',
        title='Query pipeline error',
        message=f"A user query failed to process. Error: {str(error_message)[:500]}",
        details={
            'error': str(error_message)[:1000],
            'session_id': str(session_id) if session_id else None,
        },
    )
