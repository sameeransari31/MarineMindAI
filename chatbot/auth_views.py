import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods


@require_http_methods(["POST"])
def api_login(request):
    """Authenticate user and create session."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = body.get("email", "").strip()
    password = body.get("password", "")

    if not email or not password:
        return JsonResponse({"error": "Email and password are required"}, status=400)

    user = authenticate(request, username=email, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({
            "success": True,
            "user": {"username": user.username, "email": user.email},
        })
    return JsonResponse({"error": "Invalid credentials"}, status=401)


@require_http_methods(["POST"])
def api_logout(request):
    """Log out the current user."""
    logout(request)
    return JsonResponse({"success": True})


@require_http_methods(["GET"])
def api_session_check(request):
    """Check if the current user is authenticated."""
    if request.user.is_authenticated:
        role = 'viewer'
        try:
            role = request.user.profile.role
        except Exception:
            pass
        return JsonResponse({
            "authenticated": True,
            "user": {
                "username": request.user.username,
                "email": request.user.email,
                "role": role,
            },
        })
    return JsonResponse({"authenticated": False}, status=401)


@require_http_methods(["GET"])
def api_csrf_token(request):
    """Return a CSRF token for the frontend."""
    return JsonResponse({"csrfToken": get_token(request)})
