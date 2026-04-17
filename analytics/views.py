"""
API views for vessel analytics, noon report management, and data import.
"""
import csv
import io
import os
import threading
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from administration.models import Vessel, NoonReport
from analytics.models import NoonReportImport
from analytics.serializers import (
    VesselListSerializer, VesselDetailSerializer, VesselCreateSerializer,
    NoonReportListSerializer, NoonReportDetailSerializer,
    NoonReportCreateSerializer,
    NoonReportImportSerializer, NoonReportImportDetailSerializer,
)
from analytics import analytics as analytics_engine
from analytics.services import process_noon_report_import


# ═════════════════════════════════════════════════════════════════════════════
# VESSEL ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def vessel_list(request):
    """List all vessels with summary counts."""
    vessels = Vessel.objects.all()

    # Optional filters
    vessel_type = request.query_params.get('type')
    fleet = request.query_params.get('fleet')
    status_filter = request.query_params.get('status')

    if vessel_type:
        vessels = vessels.filter(vessel_type=vessel_type)
    if fleet:
        vessels = vessels.filter(fleet_name__icontains=fleet)
    if status_filter:
        vessels = vessels.filter(operational_status=status_filter)

    serializer = VesselListSerializer(vessels, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def vessel_create(request):
    """Create a new vessel."""
    serializer = VesselCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {'errors': {'imo_number': ['A vessel with this IMO number already exists.']}},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def vessel_detail(request, vessel_id):
    """Get detailed vessel information."""
    vessel = get_object_or_404(Vessel, pk=vessel_id)
    serializer = VesselDetailSerializer(vessel)
    return Response(serializer.data)


@api_view(['DELETE'])
def vessel_delete(request, vessel_id):
    """Delete a vessel and all its associated data."""
    vessel = get_object_or_404(Vessel, pk=vessel_id)
    name = vessel.name
    vessel.delete()
    return Response({'message': f'Vessel "{name}" deleted successfully.'}, status=status.HTTP_200_OK)


# ═════════════════════════════════════════════════════════════════════════════
# NOON REPORT ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def noon_report_list(request, vessel_id):
    """List noon reports for a vessel with optional date filters."""
    vessel = get_object_or_404(Vessel, pk=vessel_id)
    reports = NoonReport.objects.filter(vessel=vessel)

    # Date filters
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    voyage = request.query_params.get('voyage')

    if date_from:
        reports = reports.filter(report_date__gte=date_from)
    if date_to:
        reports = reports.filter(report_date__lte=date_to)
    if voyage:
        reports = reports.filter(voyage_number=voyage)

    # Pagination
    page_size = min(int(request.query_params.get('page_size', 50)), 200)
    page = int(request.query_params.get('page', 1))
    offset = (page - 1) * page_size

    total = reports.count()
    reports = reports[offset:offset + page_size]
    serializer = NoonReportListSerializer(reports, many=True)

    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data,
    })


@api_view(['GET'])
def noon_report_detail(request, vessel_id, report_id):
    """Get full details of a single noon report."""
    report = get_object_or_404(NoonReport, pk=report_id, vessel_id=vessel_id)
    serializer = NoonReportDetailSerializer(report)
    return Response(serializer.data)


@api_view(['DELETE'])
def noon_report_delete(request, vessel_id, report_id):
    """Delete a single noon report."""
    report = get_object_or_404(NoonReport, pk=report_id, vessel_id=vessel_id)
    report.delete()
    return Response({'message': 'Noon report deleted successfully.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def noon_report_create(request, vessel_id):
    """Manually create a noon report via API."""
    vessel = get_object_or_404(Vessel, pk=vessel_id)
    data = request.data.copy()
    data['vessel'] = vessel.id

    serializer = NoonReportCreateSerializer(data=data)
    if serializer.is_valid():
        uploaded_by = request.user if getattr(request.user, 'is_authenticated', False) else None
        try:
            serializer.save(vessel=vessel, uploaded_by=uploaded_by, is_validated=False)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {'errors': {'non_field_errors': [
                    'A noon report already exists for this vessel at the same date and time. '
                    'Please change report time or edit the existing report.'
                ]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# ═════════════════════════════════════════════════════════════════════════════
# DATA IMPORT ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10 MB


@api_view(['POST'])
def noon_report_import(request):
    """
    Upload a CSV/Excel file to import noon report data.
    Requires: file, vessel_id in the request.
    Processing runs in a background thread.
    """
    uploaded_file = request.FILES.get('file')
    vessel_id = request.data.get('vessel_id') or request.data.get('vessel')

    if not uploaded_file:
        return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)
    if not vessel_id:
        return Response({'error': 'vessel_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    vessel = get_object_or_404(Vessel, pk=vessel_id)

    # Validate file extension
    _, ext = os.path.splitext(uploaded_file.name)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return Response(
            {'error': f'Unsupported file type: {ext}. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate file size
    if uploaded_file.size > MAX_IMPORT_SIZE:
        return Response(
            {'error': f'File too large. Maximum size: {MAX_IMPORT_SIZE // (1024*1024)} MB.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Create import record
    import_job = NoonReportImport.objects.create(
        file=uploaded_file,
        original_filename=uploaded_file.name,
        file_type=ext.lstrip('.'),
        vessel=vessel,
        uploaded_by=request.user,
    )

    # Process in background thread
    thread = threading.Thread(
        target=process_noon_report_import,
        args=(import_job,),
        daemon=True,
    )
    thread.start()

    serializer = NoonReportImportSerializer(import_job)
    return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
def noon_report_import_list(request):
    """List all import jobs, most recent first."""
    imports = NoonReportImport.objects.all()

    vessel_id = request.query_params.get('vessel_id')
    if vessel_id:
        imports = imports.filter(vessel_id=vessel_id)

    imports = imports[:50]
    serializer = NoonReportImportSerializer(imports, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def noon_report_import_detail(request, import_id):
    """Get detailed import results including per-row status."""
    import_job = get_object_or_404(NoonReportImport, pk=import_id)
    serializer = NoonReportImportDetailSerializer(import_job)
    return Response(serializer.data)


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

def _parse_date_param(param_value):
    """Parse a date string from query parameters."""
    if not param_value:
        return None
    try:
        return datetime.strptime(param_value, '%Y-%m-%d').date()
    except ValueError:
        return None


@api_view(['GET'])
def vessel_summary(request, vessel_id):
    """Get aggregated performance summary for a vessel."""
    get_object_or_404(Vessel, pk=vessel_id)
    data = analytics_engine.get_vessel_summary(str(vessel_id))
    return Response(data)


@api_view(['GET'])
def fuel_consumption_trend(request, vessel_id):
    """Get fuel consumption trend (daily/weekly/monthly)."""
    get_object_or_404(Vessel, pk=vessel_id)
    date_from = _parse_date_param(request.query_params.get('date_from'))
    date_to = _parse_date_param(request.query_params.get('date_to'))
    granularity = request.query_params.get('granularity', 'daily')

    if granularity not in ('daily', 'weekly', 'monthly'):
        return Response({'error': 'granularity must be daily, weekly, or monthly'},
                        status=status.HTTP_400_BAD_REQUEST)

    data = analytics_engine.get_fuel_consumption_trend(
        str(vessel_id), date_from, date_to, granularity,
    )
    return Response(data)


@api_view(['GET'])
def speed_vs_consumption(request, vessel_id):
    """Get speed vs fuel consumption scatter data."""
    get_object_or_404(Vessel, pk=vessel_id)
    date_from = _parse_date_param(request.query_params.get('date_from'))
    date_to = _parse_date_param(request.query_params.get('date_to'))

    data = analytics_engine.get_speed_vs_consumption(str(vessel_id), date_from, date_to)
    return Response(data)


@api_view(['GET'])
def rpm_performance(request, vessel_id):
    """Get RPM vs performance metrics."""
    get_object_or_404(Vessel, pk=vessel_id)
    date_from = _parse_date_param(request.query_params.get('date_from'))
    date_to = _parse_date_param(request.query_params.get('date_to'))

    data = analytics_engine.get_rpm_performance(str(vessel_id), date_from, date_to)
    return Response(data)


@api_view(['GET'])
def voyage_performance(request, vessel_id):
    """Get performance aggregated per voyage."""
    get_object_or_404(Vessel, pk=vessel_id)
    date_from = _parse_date_param(request.query_params.get('date_from'))
    date_to = _parse_date_param(request.query_params.get('date_to'))

    data = analytics_engine.get_voyage_performance(str(vessel_id), date_from, date_to)
    return Response(data)


@api_view(['GET'])
def weather_impact(request, vessel_id):
    """Get weather impact on performance."""
    get_object_or_404(Vessel, pk=vessel_id)
    date_from = _parse_date_param(request.query_params.get('date_from'))
    date_to = _parse_date_param(request.query_params.get('date_to'))

    data = analytics_engine.get_weather_impact(str(vessel_id), date_from, date_to)
    return Response(data)


@api_view(['GET'])
def anomaly_flags(request, vessel_id):
    """Get statistical anomaly flags for a vessel."""
    get_object_or_404(Vessel, pk=vessel_id)
    date_from = _parse_date_param(request.query_params.get('date_from'))
    date_to = _parse_date_param(request.query_params.get('date_to'))

    data = analytics_engine.get_anomaly_flags(str(vessel_id), date_from, date_to)
    return Response(data)


@api_view(['GET'])
def fleet_comparison(request):
    """Compare key metrics across multiple vessels."""
    vessel_ids = request.query_params.getlist('vessel_ids')
    date_from = _parse_date_param(request.query_params.get('date_from'))
    date_to = _parse_date_param(request.query_params.get('date_to'))

    data = analytics_engine.get_fleet_comparison(
        vessel_ids if vessel_ids else None,
        date_from, date_to,
    )
    return Response(data)


# ═════════════════════════════════════════════════════════════════════════════
# CSV EXPORT / IMPORT ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

# ── Vessel CSV ────────────────────────────────────────────────

VESSEL_CSV_FIELDS = [
    'name', 'vessel_type', 'imo_number', 'call_sign', 'flag_state',
    'classification_society', 'year_built', 'dwt', 'grt',
    'main_engine_type', 'main_engine_maker', 'main_engine_power_kw',
    'auxiliary_engine_details', 'propeller_type',
    'fleet_name', 'owner', 'manager', 'operational_status', 'notes',
]


@api_view(['GET'])
def vessel_export_csv(request):
    """Export all vessels as a CSV file."""
    vessels = Vessel.objects.all()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vessels.csv"'

    writer = csv.writer(response)
    writer.writerow(VESSEL_CSV_FIELDS)

    for v in vessels:
        writer.writerow([getattr(v, f, '') or '' for f in VESSEL_CSV_FIELDS])

    return response


@api_view(['GET'])
def vessel_csv_template(request):
    """Download an empty vessel CSV template."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vessels_template.csv"'

    writer = csv.writer(response)
    writer.writerow(VESSEL_CSV_FIELDS)
    return response


@api_view(['POST'])
def vessel_import_csv(request):
    """Import vessels from a CSV file. Skips rows with duplicate IMO numbers."""
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

    _, ext = os.path.splitext(uploaded_file.name)
    if ext.lower() != '.csv':
        return Response({'error': 'Only CSV files are supported.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        return Response({'error': 'Could not read CSV file.'}, status=status.HTTP_400_BAD_REQUEST)

    created = 0
    skipped = 0
    errors_list = []
    row_num = 1

    for row in reader:
        row_num += 1
        imo = (row.get('imo_number') or '').strip()
        name = (row.get('name') or '').strip()

        if not imo or not name:
            errors_list.append(f'Row {row_num}: missing required name or imo_number')
            skipped += 1
            continue

        if Vessel.objects.filter(imo_number=imo).exists():
            skipped += 1
            continue

        try:
            data = {}
            for f in VESSEL_CSV_FIELDS:
                val = (row.get(f) or '').strip()
                if not val:
                    continue
                field_obj = Vessel._meta.get_field(f)
                if isinstance(field_obj, (
                    type(Vessel._meta.get_field('year_built')),
                    type(Vessel._meta.get_field('dwt')),
                )):
                    data[f] = int(val) if val else None
                else:
                    data[f] = val
            Vessel.objects.create(**data)
            created += 1
        except Exception as e:
            errors_list.append(f'Row {row_num}: {str(e)}')
            skipped += 1

    return Response({
        'created': created,
        'skipped': skipped,
        'errors': errors_list[:20],
    })


# ── Noon Report CSV ──────────────────────────────────────────

NOON_REPORT_CSV_FIELDS = [
    'report_date', 'report_time', 'latitude', 'longitude',
    'voyage_number', 'port_of_departure', 'port_of_arrival',
    'speed_avg', 'speed_ordered', 'distance_sailed', 'distance_to_go',
    'rpm_avg', 'slip_percent',
    'fo_consumption', 'bf_consumption', 'fo_rob', 'bf_rob',
    'me_load_percent', 'me_power_kw', 'me_exhaust_temp', 'sfoc',
    'me_cylinder_oil_consumption', 'me_system_oil_consumption',
    'ae_lub_oil_consumption',
    'draft_fore', 'draft_aft', 'draft_mean',
    'cargo_condition', 'cargo_quantity', 'cargo_type',
    'ae_running_hours', 'ae_fo_consumption', 'boiler_fo_consumption',
    'fw_consumption', 'fw_produced',
    'wind_force', 'wind_direction', 'sea_state', 'swell_height',
    'current_knots', 'current_direction', 'visibility',
    'air_temp', 'sea_water_temp', 'barometric_pressure',
    'hours_steaming', 'hours_stopped',
    'remarks',
]


@api_view(['GET'])
def noon_report_export_csv(request, vessel_id):
    """Export noon reports for a vessel as CSV."""
    vessel = get_object_or_404(Vessel, pk=vessel_id)
    reports = NoonReport.objects.filter(vessel=vessel).order_by('report_date', 'report_time')

    # Optional date filters
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    if date_from:
        reports = reports.filter(report_date__gte=date_from)
    if date_to:
        reports = reports.filter(report_date__lte=date_to)

    safe_name = vessel.name.replace(' ', '_').replace('"', '')
    filename = f'noon_reports_{safe_name}.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(NOON_REPORT_CSV_FIELDS)

    for r in reports:
        writer.writerow([getattr(r, f, '') or '' for f in NOON_REPORT_CSV_FIELDS])

    return response


@api_view(['GET'])
def noon_report_csv_template(request):
    """Download an empty noon report CSV template."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="noon_reports_template.csv"'

    writer = csv.writer(response)
    writer.writerow(NOON_REPORT_CSV_FIELDS)
    return response


@api_view(['POST'])
def noon_report_import_csv(request, vessel_id):
    """Import noon reports from CSV for a specific vessel."""
    vessel = get_object_or_404(Vessel, pk=vessel_id)
    uploaded_file = request.FILES.get('file')

    if not uploaded_file:
        return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

    _, ext = os.path.splitext(uploaded_file.name)
    if ext.lower() != '.csv':
        return Response({'error': 'Only CSV files are supported.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        return Response({'error': 'Could not read CSV file.'}, status=status.HTTP_400_BAD_REQUEST)

    created = 0
    skipped = 0
    errors_list = []
    row_num = 1

    for row in reader:
        row_num += 1
        report_date = (row.get('report_date') or '').strip()
        if not report_date:
            errors_list.append(f'Row {row_num}: missing report_date')
            skipped += 1
            continue

        try:
            data = {'vessel': vessel, 'uploaded_by': request.user}
            for f in NOON_REPORT_CSV_FIELDS:
                val = (row.get(f) or '').strip()
                if not val:
                    continue
                field_obj = NoonReport._meta.get_field(f)
                from django.db.models import DecimalField, IntegerField, PositiveIntegerField
                if isinstance(field_obj, DecimalField):
                    data[f] = float(val)
                elif isinstance(field_obj, (IntegerField, PositiveIntegerField)):
                    data[f] = int(val)
                else:
                    data[f] = val
            NoonReport.objects.create(**data)
            created += 1
        except Exception as e:
            errors_list.append(f'Row {row_num}: {str(e)}')
            skipped += 1

    return Response({
        'created': created,
        'skipped': skipped,
        'errors': errors_list[:20],
    })
