from django.urls import path
from analytics import views

app_name = 'analytics'

urlpatterns = [
    # ── Vessels ──
    path('vessels/', views.vessel_list, name='vessel_list'),
    path('vessels/create/', views.vessel_create, name='vessel_create'),
    path('vessels/export/csv/', views.vessel_export_csv, name='vessel_export_csv'),
    path('vessels/import/csv/', views.vessel_import_csv, name='vessel_import_csv'),
    path('vessels/template/csv/', views.vessel_csv_template, name='vessel_csv_template'),
    path('vessels/<uuid:vessel_id>/', views.vessel_detail, name='vessel_detail'),
    path('vessels/<uuid:vessel_id>/delete/', views.vessel_delete, name='vessel_delete'),

    # ── Noon Reports (per vessel) ──
    path('vessels/<uuid:vessel_id>/noon-reports/', views.noon_report_list, name='noon_report_list'),
    path('vessels/<uuid:vessel_id>/noon-reports/create/', views.noon_report_create, name='noon_report_create'),
    path('vessels/<uuid:vessel_id>/noon-reports/export/csv/', views.noon_report_export_csv, name='noon_report_export_csv'),
    path('vessels/<uuid:vessel_id>/noon-reports/import/csv/', views.noon_report_import_csv, name='noon_report_import_csv'),
    path('vessels/<uuid:vessel_id>/noon-reports/<uuid:report_id>/', views.noon_report_detail, name='noon_report_detail'),
    path('vessels/<uuid:vessel_id>/noon-reports/<uuid:report_id>/delete/', views.noon_report_delete, name='noon_report_delete'),

    # ── CSV Templates ──
    path('templates/noon-reports/csv/', views.noon_report_csv_template, name='noon_report_csv_template'),

    # ── Data Import ──
    path('imports/upload/', views.noon_report_import, name='noon_report_import'),
    path('imports/', views.noon_report_import_list, name='noon_report_import_list'),
    path('imports/<uuid:import_id>/', views.noon_report_import_detail, name='noon_report_import_detail'),

    # ── Analytics (per vessel) ──
    path('vessels/<uuid:vessel_id>/analytics/summary/', views.vessel_summary, name='vessel_summary'),
    path('vessels/<uuid:vessel_id>/analytics/fuel-trend/', views.fuel_consumption_trend, name='fuel_consumption_trend'),
    path('vessels/<uuid:vessel_id>/analytics/speed-consumption/', views.speed_vs_consumption, name='speed_vs_consumption'),
    path('vessels/<uuid:vessel_id>/analytics/rpm-performance/', views.rpm_performance, name='rpm_performance'),
    path('vessels/<uuid:vessel_id>/analytics/voyage-performance/', views.voyage_performance, name='voyage_performance'),
    path('vessels/<uuid:vessel_id>/analytics/weather-impact/', views.weather_impact, name='weather_impact'),
    path('vessels/<uuid:vessel_id>/analytics/anomalies/', views.anomaly_flags, name='anomaly_flags'),

    # ── Fleet-level Analytics ──
    path('analytics/fleet-comparison/', views.fleet_comparison, name='fleet_comparison'),
]
