import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from chatbot.models import ChatSession, ChatMessage
from agents.orchestrator import process_query

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def api_chat(request):
    """
    API endpoint for chat queries.
    
    POST body: {"message": "...", "session_id": "optional-uuid"}
    Returns: {"answer": "...", "agent": "...", "sources": [...], ...}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = body.get("message", "").strip()
    session_id = body.get("session_id")

    if not user_message:
        return JsonResponse({"error": "Message is required"}, status=400)

    if len(user_message) > 5000:
        return JsonResponse({"error": "Message too long (max 5000 characters)"}, status=400)

    # Get or create session
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            session = ChatSession.objects.create(title=user_message[:50], user=request.user)
    else:
        session = ChatSession.objects.create(title=user_message[:50], user=request.user)

    # Save user message
    ChatMessage.objects.create(
        session=session,
        role='user',
        content=user_message,
    )

    # Process through multi-agent pipeline
    try:
        result = process_query(user_message)
    except Exception as e:
        logger.exception(f"[ChatAPI] Query pipeline error: {e}")
        try:
            from dashboard.alert_engine import alert_query_failure
            alert_query_failure(str(e), session_id=session.id)
        except Exception:
            pass
        return JsonResponse({"error": "An error occurred processing your query."}, status=500)

    # Save assistant response
    ChatMessage.objects.create(
        session=session,
        role='assistant',
        content=result["answer"],
        agent_used=result.get("agent", ""),
        route=result.get("route", ""),
        sources=result.get("sources", []),
        citation_map=result.get("citation_map", {}),
        graph=result.get("graph"),
        diagnosis=result.get("diagnosis"),
        processing_time=result.get("processing_time"),
    )

    # Generate alert if diagnosis has high/critical severity
    diagnosis = result.get("diagnosis")
    if diagnosis and isinstance(diagnosis, dict):
        try:
            from dashboard.alert_engine import alert_diagnosis_severity
            alert_diagnosis_severity(diagnosis, session_id=session.id)
        except Exception as alert_err:
            logger.error(f"[ChatAPI] Diagnosis alert failed: {alert_err}")

    return JsonResponse({
        "answer": result["answer"],
        "agent": result.get("agent", ""),
        "route": result.get("route", ""),
        "sources": result.get("sources", []),
        "citation_map": result.get("citation_map", {}),
        "session_id": str(session.id),
        "processing_time": result.get("processing_time", 0),
        "routing_reasoning": result.get("routing_reasoning", ""),
        "graph": result.get("graph"),
        "graph_intent": result.get("intent"),
        "available_vessels": result.get("available_vessels"),
        "diagnosis": result.get("diagnosis"),
    })


@require_http_methods(["GET"])
def api_sessions(request):
    """List recent chat sessions for the authenticated user."""
    sessions = ChatSession.objects.filter(user=request.user)[:20]
    data = [
        {
            "id": str(s.id),
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]
    return JsonResponse({"sessions": data})


@require_http_methods(["GET"])
def api_session_messages(request, session_id):
    """Get all messages in a session."""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    messages = [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "agent_used": m.agent_used,
            "route": m.route,
            "sources": m.sources,
            "citation_map": m.citation_map,
            "graph": m.graph,
            "diagnosis": m.diagnosis,
            "feedback": m.feedback,
            "processing_time": m.processing_time,
            "created_at": m.created_at.isoformat(),
        }
        for m in session.messages.all()
    ]

    return JsonResponse({"session_id": str(session.id), "messages": messages})


@csrf_exempt
@require_http_methods(["POST"])
def api_message_feedback(request, message_id):
    """
    Submit feedback for a diagnosis/assistant message.
    
    POST body: {"feedback": "correct|incorrect|partial", "note": "optional text"}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    feedback = body.get("feedback", "").strip()
    note = body.get("note", "").strip()

    if feedback not in ("correct", "incorrect", "partial"):
        return JsonResponse({"error": "Invalid feedback value"}, status=400)

    if len(note) > 2000:
        return JsonResponse({"error": "Note too long (max 2000 characters)"}, status=400)

    try:
        message = ChatMessage.objects.get(id=message_id)
    except ChatMessage.DoesNotExist:
        return JsonResponse({"error": "Message not found"}, status=404)

    if message.role != 'assistant':
        return JsonResponse({"error": "Can only provide feedback on assistant messages"}, status=400)

    message.feedback = feedback
    message.feedback_note = note
    message.save(update_fields=["feedback", "feedback_note"])

    return JsonResponse({"status": "ok", "message_id": str(message.id), "feedback": feedback})
