"""
Import service — orchestrates file parsing, validation, and NoonReport creation.
"""
import logging
from django.db import transaction
from django.utils import timezone

from administration.models import NoonReport
from analytics.models import NoonReportImport, ImportRow
from analytics.validators import validate_noon_report_row
from analytics.parsers import parse_csv, parse_excel

logger = logging.getLogger(__name__)


def process_noon_report_import(import_job: NoonReportImport) -> NoonReportImport:
    """
    Process an uploaded CSV/Excel file, validate each row, and create NoonReport records.
    Supports partial success — valid rows are saved even if some fail.

    Args:
        import_job: The NoonReportImport instance with the uploaded file.

    Returns:
        Updated NoonReportImport with results.
    """
    import_job.status = 'processing'
    import_job.save(update_fields=['status'])

    try:
        # ── Parse the file ──
        file_type = import_job.file_type.lower()
        if file_type == 'csv':
            rows, unmapped_cols, parse_errors = parse_csv(import_job.file)
        elif file_type in ('xlsx', 'xls'):
            rows, unmapped_cols, parse_errors = parse_excel(import_job.file)
        else:
            import_job.status = 'failed'
            import_job.error_summary = [f'Unsupported file type: {file_type}']
            import_job.completed_at = timezone.now()
            import_job.save()
            return import_job

        if parse_errors:
            import_job.status = 'failed'
            import_job.error_summary = parse_errors
            import_job.completed_at = timezone.now()
            import_job.save()
            return import_job

        if not rows:
            import_job.status = 'failed'
            import_job.error_summary = ['No data rows found in the file.']
            import_job.completed_at = timezone.now()
            import_job.save()
            return import_job

        # ── Process each row ──
        import_job.total_rows = len(rows)
        successful = 0
        failed = 0
        skipped = 0
        error_summary = []

        if unmapped_cols:
            error_summary.append(f"Unmapped columns (ignored): {', '.join(unmapped_cols)}")

        for idx, raw_row in enumerate(rows, start=1):
            cleaned, errors = validate_noon_report_row(raw_row)

            if errors:
                # Row has validation errors
                failed += 1
                row_errors = [f"Row {idx}: {e}" for e in errors]
                error_summary.extend(row_errors)
                ImportRow.objects.create(
                    import_job=import_job,
                    row_number=idx,
                    status='error',
                    raw_data=_sanitize_for_json(raw_row),
                    errors=errors,
                )
                continue

            # Check for duplicate report
            report_date = cleaned.get('report_date')
            report_time = cleaned.pop('report_time', None) or '12:00:00'
            if not report_date:
                failed += 1
                error_summary.append(f"Row {idx}: report_date is required but missing.")
                ImportRow.objects.create(
                    import_job=import_job,
                    row_number=idx,
                    status='error',
                    raw_data=_sanitize_for_json(raw_row),
                    errors=['report_date is required but missing.'],
                )
                continue

            exists = NoonReport.objects.filter(
                vessel=import_job.vessel,
                report_date=report_date,
                report_time=report_time,
            ).exists()

            if exists:
                skipped += 1
                ImportRow.objects.create(
                    import_job=import_job,
                    row_number=idx,
                    status='skipped',
                    raw_data=_sanitize_for_json(raw_row),
                    errors=[f"Duplicate: NoonReport for {report_date} {report_time} already exists."],
                )
                continue

            # Create NoonReport
            try:
                report_data = {k: v for k, v in cleaned.items() if v is not None and k != 'report_date'}
                with transaction.atomic():
                    noon_report = NoonReport.objects.create(
                        vessel=import_job.vessel,
                        report_date=report_date,
                        report_time=report_time,
                        uploaded_by=import_job.uploaded_by,
                        is_validated=False,
                        **report_data,
                    )
                successful += 1
                ImportRow.objects.create(
                    import_job=import_job,
                    row_number=idx,
                    status='success',
                    raw_data=_sanitize_for_json(raw_row),
                    noon_report=noon_report,
                )
            except Exception as e:
                failed += 1
                error_msg = f"Row {idx}: Database error — {str(e)}"
                error_summary.append(error_msg)
                ImportRow.objects.create(
                    import_job=import_job,
                    row_number=idx,
                    status='error',
                    raw_data=_sanitize_for_json(raw_row),
                    errors=[str(e)],
                )
                logger.exception(f"Error saving NoonReport from import row {idx}")

        # ── Finalize ──
        import_job.successful_rows = successful
        import_job.failed_rows = failed
        import_job.skipped_rows = skipped
        import_job.error_summary = error_summary

        if failed == 0 and skipped == 0:
            import_job.status = 'completed'
        elif successful > 0:
            import_job.status = 'completed_with_errors'
        else:
            import_job.status = 'failed'

        import_job.completed_at = timezone.now()
        import_job.save()

        # Generate alert if import had issues
        try:
            from dashboard.alert_engine import alert_import_issues
            alert_import_issues(import_job)
        except Exception as alert_err:
            logger.error(f"Alert generation failed: {alert_err}")

        logger.info(
            f"Import {import_job.id}: {successful} success, "
            f"{failed} failed, {skipped} skipped out of {len(rows)} rows"
        )
        return import_job

    except Exception as e:
        import_job.status = 'failed'
        import_job.error_summary = [f'Unexpected error: {str(e)}']
        import_job.completed_at = timezone.now()
        import_job.save()
        logger.exception(f"Import {import_job.id} failed with unexpected error")
        return import_job


def _sanitize_for_json(data: dict) -> dict:
    """Convert all values to JSON-safe types."""
    sanitized = {}
    for key, value in data.items():
        if value is None:
            sanitized[key] = None
        else:
            sanitized[key] = str(value)
    return sanitized
