from functools import wraps

from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

from .roles import get_permissions


def require_capability(capability, methods=None):
    protected_methods = {method.upper() for method in methods} if methods else None

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if protected_methods is not None and request.method.upper() not in protected_methods:
                return view(request, *args, **kwargs)
            authenticated = JWTAuthentication().authenticate(request)
            if authenticated is None:
                return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
            request.user, request.auth = authenticated
            if capability not in get_permissions(request.user):
                return JsonResponse({"detail": "You do not have permission to perform this action."}, status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


LEGACY_ANALYSIS_WRITE_NAMES = {
    "save_info",
    "react_send_page1",
    "react_send_page2",
    "react_send_page3",
    "react_send_page3_hg38",
    "react_send_page4",
    "react_send_page2_trio",
    "react_send_page3_trio",
    "react_send_page3_trio_shortcut",
    "delete_job",
}


def protect_legacy_analysis_patterns(patterns):
    for pattern in patterns:
        if getattr(pattern, "name", None) in LEGACY_ANALYSIS_WRITE_NAMES:
            pattern._callback = require_capability("analysis.run")(pattern.callback)
    return patterns
