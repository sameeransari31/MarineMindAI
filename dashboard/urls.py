from django.urls import path
from dashboard import views

urlpatterns = [
    # Overview
    path('overview/', views.overview, name='dashboard_overview'),

    # Query monitoring
    path('queries/', views.query_list, name='dashboard_queries'),
    path('queries/<uuid:message_id>/', views.query_detail, name='dashboard_query_detail'),

    # RAG monitoring
    path('rag/', views.rag_status, name='dashboard_rag'),
    path('rag/<uuid:document_id>/reindex/', views.rag_reindex, name='dashboard_rag_reindex'),

    # Analytics monitoring
    path('analytics-monitor/', views.analytics_monitor, name='dashboard_analytics_monitor'),

    # Diagnosis monitoring
    path('diagnosis/', views.diagnosis_monitor, name='dashboard_diagnosis_monitor'),

    # System logs
    path('logs/', views.system_logs, name='dashboard_logs'),

    # Alerts
    path('alerts/', views.alert_list, name='dashboard_alerts'),
    path('alerts/read-all/', views.alert_mark_all_read, name='dashboard_alerts_read_all'),
    path('alerts/<uuid:alert_id>/read/', views.alert_mark_read, name='dashboard_alert_read'),

    # Vessel performance
    path('vessels/', views.vessel_list_simple, name='dashboard_vessels'),
    path('vessels/<uuid:vessel_id>/performance/', views.vessel_performance, name='dashboard_vessel_performance'),
]
