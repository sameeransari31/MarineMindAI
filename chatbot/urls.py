from django.urls import path
from chatbot import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('chat/<uuid:session_id>/', views.chat_view, name='chat_session'),
]
