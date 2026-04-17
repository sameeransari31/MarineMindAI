from django.urls import path
from ingestion import views

app_name = 'ingestion'

urlpatterns = [
    path('', views.upload_page, name='upload_page'),
    path('api/upload/', views.api_upload, name='api_upload'),
    path('api/documents/', views.api_documents, name='api_documents'),
    path('api/documents/<uuid:document_id>/status/', views.api_document_status, name='api_document_status'),
    path('api/documents/<uuid:document_id>/delete/', views.api_delete_document, name='api_delete_document'),
]
