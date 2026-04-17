from django.contrib.admin import AdminSite
from django.urls import path
from django.template.response import TemplateResponse
from django.utils import timezone


class MarineMindAdminSite(AdminSite):
    """Custom admin site for MarineMind with a dashboard overview."""

    site_header = 'MarineMind Administration'
    site_title = 'MarineMind Admin'
    index_title = 'Dashboard'
    site_url = '/'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        """Override the default index to inject dashboard stats."""
        extra_context = extra_context or {}
        extra_context.update(self._get_dashboard_context())
        return super().index(request, extra_context=extra_context)

    def dashboard_view(self, request):
        """Dedicated dashboard page with full system overview."""
        context = {
            **self.each_context(request),
            'title': 'MarineMind Dashboard',
            **self._get_dashboard_context(),
        }
        return TemplateResponse(request, 'admin/dashboard.html', context)

    def _get_dashboard_context(self):
        """Gather stats for the dashboard."""
        from django.contrib.auth import get_user_model
        from ingestion.models import Document
        from chatbot.models import ChatSession, ChatMessage
        from administration.models import (
            Vessel, NoonReport, SystemLog, AuditLog, QueryFeedback, SystemConfig,
        )

        User = get_user_model()
        now = timezone.now()
        last_24h = now - timezone.timedelta(hours=24)
        last_7d = now - timezone.timedelta(days=7)

        # User stats
        total_users = User.objects.count()
        active_users_7d = User.objects.filter(last_login__gte=last_7d).count()
        staff_users = User.objects.filter(is_staff=True).count()

        # Vessel stats
        total_vessels = Vessel.objects.count()
        active_vessels = Vessel.objects.filter(operational_status='active').count()

        # Document stats
        total_documents = Document.objects.count()
        docs_completed = Document.objects.filter(status='completed').count()
        docs_processing = Document.objects.filter(status='processing').count()
        docs_failed = Document.objects.filter(status='failed').count()
        docs_pending = Document.objects.filter(status='pending').count()

        # Chat stats
        total_sessions = ChatSession.objects.count()
        sessions_24h = ChatSession.objects.filter(created_at__gte=last_24h).count()
        total_messages = ChatMessage.objects.count()
        messages_24h = ChatMessage.objects.filter(created_at__gte=last_24h).count()

        # Agent usage breakdown
        agent_stats = {}
        for agent in ['rag', 'internet', 'hybrid', 'guardrails']:
            agent_stats[agent] = ChatMessage.objects.filter(
                role='assistant', agent_used=agent,
            ).count()

        # Route breakdown
        route_stats = {}
        for route in ['rag', 'internet', 'hybrid', 'greeting', 'rejected']:
            route_stats[route] = ChatMessage.objects.filter(
                role='assistant', route=route,
            ).count()

        # Noon reports
        total_noon_reports = NoonReport.objects.count()
        validated_noon_reports = NoonReport.objects.filter(is_validated=True).count()

        # System health
        recent_errors = SystemLog.objects.filter(
            level__in=['error', 'critical'], created_at__gte=last_24h,
        ).count()
        recent_logs = SystemLog.objects.filter(created_at__gte=last_24h).count()

        # Feedback
        total_feedbacks = QueryFeedback.objects.count()
        correct_feedbacks = QueryFeedback.objects.filter(rating='correct').count()
        incorrect_feedbacks = QueryFeedback.objects.filter(rating='incorrect').count()

        # Recent activity
        recent_documents = Document.objects.order_by('-uploaded_at')[:5]
        recent_sessions = ChatSession.objects.order_by('-updated_at')[:5]
        recent_system_logs = SystemLog.objects.order_by('-created_at')[:10]
        recent_audit_logs = AuditLog.objects.order_by('-created_at')[:10]

        return {
            # Users
            'total_users': total_users,
            'active_users_7d': active_users_7d,
            'staff_users': staff_users,
            # Vessels
            'total_vessels': total_vessels,
            'active_vessels': active_vessels,
            # Documents
            'total_documents': total_documents,
            'docs_completed': docs_completed,
            'docs_processing': docs_processing,
            'docs_failed': docs_failed,
            'docs_pending': docs_pending,
            # Chat
            'total_sessions': total_sessions,
            'sessions_24h': sessions_24h,
            'total_messages': total_messages,
            'messages_24h': messages_24h,
            'agent_stats': agent_stats,
            'route_stats': route_stats,
            # Noon Reports
            'total_noon_reports': total_noon_reports,
            'validated_noon_reports': validated_noon_reports,
            # System
            'recent_errors': recent_errors,
            'recent_logs': recent_logs,
            'total_feedbacks': total_feedbacks,
            'correct_feedbacks': correct_feedbacks,
            'incorrect_feedbacks': incorrect_feedbacks,
            # Recent activity
            'recent_documents': recent_documents,
            'recent_sessions': recent_sessions,
            'recent_system_logs': recent_system_logs,
            'recent_audit_logs': recent_audit_logs,
        }


marinemind_admin = MarineMindAdminSite(name='marinemind_admin')
