from django.shortcuts import render, get_object_or_404
from chatbot.models import ChatSession


def chat_view(request, session_id=None):
    """Main chat interface."""
    sessions = ChatSession.objects.all()[:20]

    if session_id:
        session = get_object_or_404(ChatSession, id=session_id)
    else:
        session = None

    messages = []
    if session:
        messages = session.messages.all()

    return render(request, 'chatbot/chat.html', {
        'sessions': sessions,
        'current_session': session,
        'messages': messages,
    })
