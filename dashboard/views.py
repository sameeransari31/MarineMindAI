"""
Dashboard API views — overview stats, query monitoring, RAG/analytics/diagnosis
monitoring, system logs, alerts, and vessel performance.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg, Sum, F
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from administration.models import (
    Vessel, NoonReport, SystemLog, AuditLog, UserProfile,
)
from chatbot.models import ChatSession, ChatMessage
from ingestion.models import Document
from analytics.models import NoonReportImport
from dashboard.models import Alert


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _parse_date_range(request):
    """Extract date range from query params."""
    days = request.query_params.get('days')
    date_from = request.query_params.get('from')
    date_to = request.query_params.get('to')

    now = timezone.now()
    if days:
        start = now - timedelta(days=int(days))
        end = now
    elif date_from:
        from django.utils.dateparse import parse_datetime, parse_date
        start = parse_datetime(date_from) or timezone.make_aware(
            timezone.datetime.combine(parse_date(date_from), timezone.datetime.min.time())
        )
        end = (parse_datetime(date_to) if date_to else now) or now
    else:
        start = now - timedelta(days=30)
        end = now

    return start, end


def _paginate(queryset, request, default_size=25):
    """Simple offset pagination."""
    page = max(int(request.query_params.get('page', 1)), 1)
    page_size = min(int(request.query_params.get('page_size', default_size)), 100)
    total = queryset.count()
    offset = (page - 1) * page_size
    items = queryset[offset:offset + page_size]
    return items, {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1. OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def overview(request):
    """Dashboard overview with key metrics and recent activity."""
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    # Vessel stats
    vessels = Vessel.objects.all()
    total_vessels = vessels.count()
    active_vessels = vessels.filter(operational_status='active').count()

    # User stats
    total_users = User.objects.filter(is_active=True).count()
    active_users_7d = User.objects.filter(
        is_active=True, last_login__gte=seven_days_ago
    ).count()

    # Document stats
    total_documents = Document.objects.count()
    docs_by_status = dict(
        Document.objects.values_list('status').annotate(c=Count('id')).values_list('status', 'c')
    )
    docs_by_embedding = dict(
        Document.objects.values_list('embedding_status').annotate(c=Count('id')).values_list('embedding_status', 'c')
    )
    total_chunks = Document.objects.aggregate(s=Sum('total_chunks'))['s'] or 0

    # Query stats
    total_queries = ChatMessage.objects.filter(role='user').count()
    queries_7d = ChatMessage.objects.filter(role='user', created_at__gte=seven_days_ago).count()

    route_distribution = dict(
        ChatMessage.objects.filter(role='assistant', route__gt='')
        .values_list('route')
        .annotate(c=Count('id'))
        .values_list('route', 'c')
    )

    # Noon report stats
    total_noon_reports = NoonReport.objects.count()

    # Average processing time
    avg_processing_time = ChatMessage.objects.filter(
        role='assistant', processing_time__isnull=False
    ).aggregate(avg=Avg('processing_time'))['avg']

    # Recent activity: last 10 user queries paired with their assistant response
    recent_queries = ChatMessage.objects.filter(
        role='user'
    ).select_related('session').order_by('-created_at')[:10]

    recent_activity = []
    for msg in recent_queries:
        assistant_msg = ChatMessage.objects.filter(
            session=msg.session, role='assistant', created_at__gt=msg.created_at
        ).first()
        recent_activity.append({
            'id': str(msg.id),
            'query': msg.content[:200],
            'route': assistant_msg.route if assistant_msg else '',
            'agent_used': assistant_msg.agent_used if assistant_msg else '',
            'processing_time': assistant_msg.processing_time if assistant_msg else None,
            'timestamp': msg.created_at.isoformat(),
            'session_id': str(msg.session_id),
        })

    # Unread alerts count
    unread_alerts = Alert.objects.filter(is_read=False).count()

    # System health — errors in last 24h
    errors_24h = SystemLog.objects.filter(
        level__in=['error', 'critical'], created_at__gte=now - timedelta(hours=24)
    ).count()

    return Response({
        'vessels': {
            'total': total_vessels,
            'active': active_vessels,
        },
        'users': {
            'total': total_users,
            'active_7d': active_users_7d,
        },
        'documents': {
            'total': total_documents,
            'by_status': docs_by_status,
            'by_embedding': docs_by_embedding,
            'total_chunks': total_chunks,
        },
        'queries': {
            'total': total_queries,
            'last_7d': queries_7d,
            'route_distribution': route_distribution,
            'avg_processing_time': round(avg_processing_time, 2) if avg_processing_time else None,
        },
        'noon_reports': {
            'total': total_noon_reports,
        },
        'alerts': {
            'unread': unread_alerts,
        },
        'system_health': {
            'errors_24h': errors_24h,
        },
        'recent_activity': recent_activity,
    })


# ═════════════════════════════════════════════════════════════════════════════
# 2. QUERY MONITORING
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def query_list(request):
    """Paginated list of all user queries with their assistant responses."""
    qs = ChatMessage.objects.filter(role='user').select_related('session').order_by('-created_at')

    # Filters
    route = request.query_params.get('route')
    feedback = request.query_params.get('feedback')
    search = request.query_params.get('search')
    start, end = _parse_date_range(request)

    qs = qs.filter(created_at__range=(start, end))

    # We need to filter by route/feedback on the assistant message
    if route or feedback:
        assistant_filter = Q()
        if route:
            assistant_filter &= Q(route=route)
        if feedback:
            assistant_filter &= Q(feedback=feedback)
        matching_sessions_ids = ChatMessage.objects.filter(
            role='assistant'
        ).filter(assistant_filter).values_list('session_id', flat=True)
        qs = qs.filter(session_id__in=matching_sessions_ids)

    if search:
        qs = qs.filter(content__icontains=search)

    items, pagination = _paginate(qs, request)

    results = []
    for msg in items:
        assistant_msg = ChatMessage.objects.filter(
            session=msg.session, role='assistant', created_at__gt=msg.created_at
        ).first()
        results.append({
            'id': str(msg.id),
            'assistant_id': str(assistant_msg.id) if assistant_msg else None,
            'query': msg.content[:300],
            'response_preview': assistant_msg.content[:300] if assistant_msg else '',
            'route': assistant_msg.route if assistant_msg else '',
            'agent_used': assistant_msg.agent_used if assistant_msg else '',
            'processing_time': assistant_msg.processing_time if assistant_msg else None,
            'feedback': assistant_msg.feedback if assistant_msg else '',
            'has_graph': bool(assistant_msg.graph) if assistant_msg else False,
            'has_diagnosis': bool(assistant_msg.diagnosis) if assistant_msg else False,
            'timestamp': msg.created_at.isoformat(),
            'session_id': str(msg.session_id),
        })

    return Response({'results': results, **pagination})


@api_view(['GET'])
def query_detail(request, message_id):
    """Full pipeline detail for a specific query."""
    user_msg = get_object_or_404(ChatMessage, pk=message_id, role='user')
    assistant_msg = ChatMessage.objects.filter(
        session=user_msg.session, role='assistant', created_at__gt=user_msg.created_at
    ).first()

    # Related system logs
    logs = SystemLog.objects.filter(
        session=user_msg.session,
        created_at__range=(
            user_msg.created_at - timedelta(seconds=1),
            (assistant_msg.created_at if assistant_msg else user_msg.created_at) + timedelta(seconds=5),
        ),
    ).order_by('created_at').values('level', 'category', 'message', 'duration_ms', 'created_at')

    data = {
        'user_message': {
            'id': str(user_msg.id),
            'content': user_msg.content,
            'timestamp': user_msg.created_at.isoformat(),
        },
        'assistant_message': None,
        'pipeline_logs': list(logs),
    }

    if assistant_msg:
        data['assistant_message'] = {
            'id': str(assistant_msg.id),
            'content': assistant_msg.content,
            'route': assistant_msg.route,
            'agent_used': assistant_msg.agent_used,
            'sources': assistant_msg.sources,
            'citation_map': assistant_msg.citation_map,
            'graph': assistant_msg.graph,
            'diagnosis': assistant_msg.diagnosis,
            'feedback': assistant_msg.feedback,
            'feedback_note': assistant_msg.feedback_note,
            'processing_time': assistant_msg.processing_time,
            'timestamp': assistant_msg.created_at.isoformat(),
        }

    return Response(data)


# ═════════════════════════════════════════════════════════════════════════════
# 3. RAG MONITORING
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def rag_status(request):
    """RAG document status — documents, chunks, embedding status."""
    docs = Document.objects.all().order_by('-uploaded_at')

    # Filters
    doc_status = request.query_params.get('status')
    embedding = request.query_params.get('embedding_status')
    search = request.query_params.get('search')

    if doc_status:
        docs = docs.filter(status=doc_status)
    if embedding:
        docs = docs.filter(embedding_status=embedding)
    if search:
        docs = docs.filter(title__icontains=search)

    items, pagination = _paginate(docs, request, default_size=20)

    results = []
    for doc in items:
        results.append({
            'id': str(doc.id),
            'title': doc.title,
            'file_type': doc.file_type,
            'file_size': doc.file_size,
            'total_pages': doc.total_pages,
            'total_chunks': doc.total_chunks,
            'status': doc.status,
            'embedding_status': doc.embedding_status,
            'document_type': doc.document_type,
            'vessel_id': str(doc.vessel_id) if doc.vessel_id else None,
            'uploaded_at': doc.uploaded_at.isoformat(),
            'processed_at': doc.processed_at.isoformat() if doc.processed_at else None,
            'error_message': doc.error_message,
        })

    # Aggregates
    aggregates = {
        'total': Document.objects.count(),
        'by_status': dict(
            Document.objects.values_list('status').annotate(c=Count('id')).values_list('status', 'c')
        ),
        'by_embedding': dict(
            Document.objects.values_list('embedding_status').annotate(c=Count('id')).values_list('embedding_status', 'c')
        ),
        'total_chunks': Document.objects.aggregate(s=Sum('total_chunks'))['s'] or 0,
    }

    return Response({'results': results, 'aggregates': aggregates, **pagination})


@api_view(['POST'])
def rag_reindex(request, document_id):
    """Trigger re-indexing for a single document."""
    doc = get_object_or_404(Document, pk=document_id)

    if doc.status != 'completed':
        return Response(
            {'error': 'Only completed documents can be re-indexed.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    doc.embedding_status = 'not_started'
    doc.status = 'pending'
    doc.save(update_fields=['embedding_status', 'status'])

    # Trigger async processing
    import threading
    from ingestion.services import process_document
    threading.Thread(target=process_document, args=(str(doc.id),), daemon=True).start()

    return Response({
        'message': f'Re-indexing triggered for "{doc.title}".',
        'document_id': str(doc.id),
    })


# ═════════════════════════════════════════════════════════════════════════════
# 4. ANALYTICS MONITORING
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def analytics_monitor(request):
    """Analytics monitoring — imports, graph generation history, top metrics."""
    start, end = _parse_date_range(request)

    # Noon report import history
    imports = NoonReportImport.objects.filter(
        created_at__range=(start, end)
    ).order_by('-created_at')[:20]

    import_list = []
    for imp in imports:
        import_list.append({
            'id': str(imp.id),
            'filename': imp.original_filename,
            'vessel': imp.vessel.name,
            'vessel_id': str(imp.vessel_id),
            'status': imp.status,
            'total_rows': imp.total_rows,
            'successful_rows': imp.successful_rows,
            'failed_rows': imp.failed_rows,
            'skipped_rows': imp.skipped_rows,
            'created_at': imp.created_at.isoformat(),
            'completed_at': imp.completed_at.isoformat() if imp.completed_at else None,
        })

    # Graph generation history — assistant messages with route='graph'
    graph_msgs = ChatMessage.objects.filter(
        role='assistant', route='graph', created_at__range=(start, end)
    ).order_by('-created_at')[:20]

    graph_history = []
    for msg in graph_msgs:
        user_msg = ChatMessage.objects.filter(
            session=msg.session, role='user', created_at__lt=msg.created_at
        ).order_by('-created_at').first()
        graph_history.append({
            'id': str(msg.id),
            'query': user_msg.content[:200] if user_msg else '',
            'chart_type': msg.graph.get('chart_type', '') if msg.graph else '',
            'title': msg.graph.get('title', '') if msg.graph else '',
            'processing_time': msg.processing_time,
            'timestamp': msg.created_at.isoformat(),
        })

    # Most requested metrics — extract from graph configs
    metric_counts = {}
    graph_messages = ChatMessage.objects.filter(
        role='assistant', route='graph', graph__isnull=False,
    )
    for gm in graph_messages:
        if gm.graph and isinstance(gm.graph, dict):
            title = gm.graph.get('title', '')
            if title:
                # Normalize to a simple metric name
                metric_counts[title] = metric_counts.get(title, 0) + 1
    top_metrics = sorted(metric_counts.items(), key=lambda x: -x[1])[:10]

    # Import aggregates
    import_aggregates = {
        'total': NoonReportImport.objects.count(),
        'by_status': dict(
            NoonReportImport.objects.values_list('status').annotate(c=Count('id')).values_list('status', 'c')
        ),
        'total_noon_reports': NoonReport.objects.count(),
    }

    return Response({
        'imports': import_list,
        'graph_history': graph_history,
        'top_metrics': [{'metric': m, 'count': c} for m, c in top_metrics],
        'aggregates': import_aggregates,
    })


# ═════════════════════════════════════════════════════════════════════════════
# 5. DIAGNOSIS MONITORING
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def diagnosis_monitor(request):
    """Diagnosis monitoring — issues, feedback stats, trends."""
    start, end = _parse_date_range(request)

    # Diagnosis messages
    diag_msgs = ChatMessage.objects.filter(
        role='assistant', route='diagnosis', created_at__range=(start, end)
    ).order_by('-created_at')

    severity_filter = request.query_params.get('severity')
    category_filter = request.query_params.get('category')

    items, pagination = _paginate(diag_msgs, request, default_size=20)

    results = []
    for msg in items:
        diag = msg.diagnosis or {}

        # Apply post-fetch filters on JSON fields
        if severity_filter and diag.get('severity') != severity_filter:
            continue
        if category_filter and diag.get('category') != category_filter:
            continue

        user_msg = ChatMessage.objects.filter(
            session=msg.session, role='user', created_at__lt=msg.created_at
        ).order_by('-created_at').first()

        results.append({
            'id': str(msg.id),
            'query': user_msg.content[:200] if user_msg else '',
            'severity': diag.get('severity', ''),
            'category': diag.get('category', ''),
            'symptoms': diag.get('symptoms', []),
            'affected_components': diag.get('affected_components', []),
            'vessel_name': diag.get('vessel_name', ''),
            'feedback': msg.feedback,
            'processing_time': msg.processing_time,
            'timestamp': msg.created_at.isoformat(),
        })

    # Feedback stats
    total_diag = ChatMessage.objects.filter(role='assistant', route='diagnosis').count()
    feedback_counts = dict(
        ChatMessage.objects.filter(role='assistant', route='diagnosis', feedback__gt='')
        .values_list('feedback')
        .annotate(c=Count('id'))
        .values_list('feedback', 'c')
    )

    # Severity distribution
    severity_dist = {}
    for msg in ChatMessage.objects.filter(role='assistant', route='diagnosis', diagnosis__isnull=False):
        sev = (msg.diagnosis or {}).get('severity', 'unknown')
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    return Response({
        'results': results,
        'feedback_stats': {
            'total': total_diag,
            **feedback_counts,
        },
        'severity_distribution': severity_dist,
        **pagination,
    })


# ═════════════════════════════════════════════════════════════════════════════
# 6. SYSTEM LOGS
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def system_logs(request):
    """Paginated system logs with filters."""
    qs = SystemLog.objects.all().order_by('-created_at')

    # Filters
    level = request.query_params.get('level')
    category = request.query_params.get('category')
    search = request.query_params.get('search')
    start, end = _parse_date_range(request)

    qs = qs.filter(created_at__range=(start, end))

    if level:
        qs = qs.filter(level=level)
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(message__icontains=search)

    items, pagination = _paginate(qs, request, default_size=50)

    results = []
    for log in items:
        results.append({
            'id': str(log.id),
            'level': log.level,
            'category': log.category,
            'message': log.message,
            'details': log.details,
            'duration_ms': log.duration_ms,
            'document_id': str(log.document_id) if log.document_id else None,
            'session_id': str(log.session_id) if log.session_id else None,
            'user': log.user.username if log.user else None,
            'created_at': log.created_at.isoformat(),
        })

    # Aggregates
    now = timezone.now()
    aggregates = {
        'errors_24h': SystemLog.objects.filter(
            level__in=['error', 'critical'], created_at__gte=now - timedelta(hours=24)
        ).count(),
        'warnings_24h': SystemLog.objects.filter(
            level='warning', created_at__gte=now - timedelta(hours=24)
        ).count(),
        'errors_7d': SystemLog.objects.filter(
            level__in=['error', 'critical'], created_at__gte=now - timedelta(days=7)
        ).count(),
        'by_category': dict(
            SystemLog.objects.filter(created_at__range=(start, end))
            .values_list('category')
            .annotate(c=Count('id'))
            .values_list('category', 'c')
        ),
        'by_level': dict(
            SystemLog.objects.filter(created_at__range=(start, end))
            .values_list('level')
            .annotate(c=Count('id'))
            .values_list('level', 'c')
        ),
    }

    return Response({'results': results, 'aggregates': aggregates, **pagination})


# ═════════════════════════════════════════════════════════════════════════════
# 7. ALERTS
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def alert_list(request):
    """List alerts with optional filters."""
    qs = Alert.objects.all()

    severity = request.query_params.get('severity')
    alert_type = request.query_params.get('type')
    is_read = request.query_params.get('is_read')

    if severity:
        qs = qs.filter(severity=severity)
    if alert_type:
        qs = qs.filter(alert_type=alert_type)
    if is_read is not None:
        qs = qs.filter(is_read=is_read.lower() == 'true')

    items, pagination = _paginate(qs, request, default_size=25)

    results = []
    for alert in items:
        results.append({
            'id': str(alert.id),
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'title': alert.title,
            'message': alert.message,
            'details': alert.details,
            'vessel_id': str(alert.vessel_id) if alert.vessel_id else None,
            'vessel_name': alert.vessel.name if alert.vessel else None,
            'is_read': alert.is_read,
            'created_at': alert.created_at.isoformat(),
        })

    return Response({'results': results, **pagination})


@api_view(['POST'])
def alert_mark_read(request, alert_id):
    """Mark an alert as read."""
    alert = get_object_or_404(Alert, pk=alert_id)
    alert.is_read = True
    alert.save(update_fields=['is_read'])
    return Response({'message': 'Alert marked as read.', 'id': str(alert.id)})


@api_view(['POST'])
def alert_mark_all_read(request):
    """Mark all alerts as read."""
    count = Alert.objects.filter(is_read=False).update(is_read=True)
    return Response({'message': f'{count} alerts marked as read.'})


# ═════════════════════════════════════════════════════════════════════════════
# 8. VESSEL PERFORMANCE
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def vessel_performance(request, vessel_id):
    """Vessel performance overview — fuel, RPM, speed trends over time."""
    vessel = get_object_or_404(Vessel, pk=vessel_id)
    start, end = _parse_date_range(request)

    reports = NoonReport.objects.filter(
        vessel=vessel,
        report_date__range=(start.date(), end.date()),
    ).order_by('report_date')

    # Build trend data
    dates = []
    fuel_data = []
    rpm_data = []
    speed_data = []
    distance_data = []

    for r in reports:
        dates.append(r.report_date.isoformat())
        fuel_data.append(float(r.fo_consumption) if r.fo_consumption else None)
        rpm_data.append(float(r.rpm_avg) if r.rpm_avg else None)
        speed_data.append(float(r.speed_avg) if r.speed_avg else None)
        distance_data.append(float(r.distance_sailed) if r.distance_sailed else None)

    # Summary stats
    agg = reports.aggregate(
        avg_speed=Avg('speed_avg'),
        avg_rpm=Avg('rpm_avg'),
        avg_fuel=Avg('fo_consumption'),
        total_distance=Sum('distance_sailed'),
        total_fuel=Sum('fo_consumption'),
        report_count=Count('id'),
    )

    return Response({
        'vessel': {
            'id': str(vessel.id),
            'name': vessel.name,
            'vessel_type': vessel.vessel_type,
            'imo_number': vessel.imo_number,
            'operational_status': vessel.operational_status,
        },
        'period': {
            'from': start.date().isoformat(),
            'to': end.date().isoformat(),
        },
        'trends': {
            'dates': dates,
            'fuel': fuel_data,
            'rpm': rpm_data,
            'speed': speed_data,
            'distance': distance_data,
        },
        'summary': {
            'avg_speed': round(float(agg['avg_speed']), 2) if agg['avg_speed'] else None,
            'avg_rpm': round(float(agg['avg_rpm']), 2) if agg['avg_rpm'] else None,
            'avg_fuel': round(float(agg['avg_fuel']), 2) if agg['avg_fuel'] else None,
            'total_distance': round(float(agg['total_distance']), 2) if agg['total_distance'] else None,
            'total_fuel': round(float(agg['total_fuel']), 2) if agg['total_fuel'] else None,
            'report_count': agg['report_count'],
        },
    })


# ═════════════════════════════════════════════════════════════════════════════
# 9. VESSEL LIST (for dropdown selectors)
# ═════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def vessel_list_simple(request):
    """Simple vessel list for dashboard dropdowns."""
    vessels = Vessel.objects.all().order_by('name')
    data = [
        {
            'id': str(v.id),
            'name': v.name,
            'imo_number': v.imo_number,
            'operational_status': v.operational_status,
        }
        for v in vessels
    ]
    return Response(data)
