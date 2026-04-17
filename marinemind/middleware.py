from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings


class LoginRequiredMiddleware:
    """
    Middleware that redirects unauthenticated users to the login page.
    API endpoints receive a 401 JSON response instead of a redirect.
    Exempts LOGIN_URL, /admin/, static files, and media files.
    """

    EXEMPT_PREFIXES = [
        settings.LOGIN_URL,
        '/admin/',
        '/static/',
        '/media/',
        '/api/auth/',
    ]

    API_PREFIXES = [
        '/api/',
        '/ingestion/api/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
                # Return 401 JSON for API requests instead of redirecting
                if any(path.startswith(prefix) for prefix in self.API_PREFIXES):
                    return JsonResponse({'error': 'Authentication required'}, status=401)
                return redirect(settings.LOGIN_URL)

        return self.get_response(request)
