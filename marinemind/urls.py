from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from chatbot.auth_views import api_login, api_logout, api_session_check, api_csrf_token
from administration.sites import marinemind_admin

urlpatterns = [
    path('admin/dashboard/', admin.site.admin_view(marinemind_admin.dashboard_view), name='admin_dashboard'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Auth API for React frontend
    path('api/auth/login/', api_login, name='api_login'),
    path('api/auth/logout/', api_logout, name='api_logout'),
    path('api/auth/session/', api_session_check, name='api_session_check'),
    path('api/auth/csrf/', api_csrf_token, name='api_csrf_token'),
    path('', include('chatbot.urls')),
    path('api/', include('chatbot.api_urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('ingestion/', include('ingestion.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
