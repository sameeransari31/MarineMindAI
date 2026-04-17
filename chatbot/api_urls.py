from django.urls import path
from chatbot import api_views

urlpatterns = [
    path('chat/', api_views.api_chat, name='api_chat'),
    path('sessions/', api_views.api_sessions, name='api_sessions'),
    path('sessions/<uuid:session_id>/messages/', api_views.api_session_messages, name='api_session_messages'),
    path('messages/<uuid:message_id>/feedback/', api_views.api_message_feedback, name='api_message_feedback'),
]
