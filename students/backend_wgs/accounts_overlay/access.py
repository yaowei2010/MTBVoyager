from functools import wraps
import json

from django.http import JsonResponse
from django.core import serializers
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import AnalysisAccess, UserProfile
from .roles import get_permissions, get_role


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


def authenticate_request(request):
    authenticated = JWTAuthentication().authenticate(request)
    if authenticated is None:
        return None
    request.user, request.auth = authenticated
    return request.user


def register_analysis(analysis_id, owner):
    if analysis_id and owner and owner.is_authenticated:
        return AnalysisAccess.objects.update_or_create(
            analysis_id=str(analysis_id), defaults={"owner": owner}
        )[0]
    return None


def can_access_analysis(user, analysis_id):
    if not user or not user.is_authenticated:
        return False
    if get_role(user) == UserProfile.Role.ADMIN:
        return True
    query = AnalysisAccess.objects.filter(analysis_id=str(analysis_id))
    if get_role(user) == UserProfile.Role.VIEWER:
        return query.filter(assigned_users=user).exists()
    return query.filter(models.Q(owner=user) | models.Q(assigned_users=user)).exists()


def _analysis_id_from_request(request, kwargs):
    for key in ("analysis_id", "job_id"):
        if kwargs.get(key):
            return str(kwargs[key])
    for key in ("analysis_id", "analysis_ID", "newjobid", "newjobID", "jobID"):
        value = request.GET.get(key) or request.POST.get(key)
        if value:
            return str(value)
    if request.body:
        try:
            body = json.loads(request.body)
            for key in ("analysis_id", "analysis_ID", "newjobid", "newjobID", "jobID"):
                if body.get(key):
                    return str(body[key])
        except (TypeError, ValueError):
            pass
    return ""


def require_analysis_access(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user = authenticate_request(request)
        if user is None:
            return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
        analysis_id = _analysis_id_from_request(request, kwargs)
        if not analysis_id or not can_access_analysis(user, analysis_id):
            return JsonResponse({"detail": "Analysis not found or not assigned to this account."}, status=404)
        return view(request, *args, **kwargs)
    return wrapped


@csrf_exempt
def accessible_job_list(request):
    user = authenticate_request(request)
    if user is None:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
    from hw1.models import existJobs
    if get_role(user) == UserProfile.Role.ADMIN:
        jobs = existJobs.jobs.all()
    else:
        access_rows = AnalysisAccess.objects.filter(assigned_users=user)
        if get_role(user) != UserProfile.Role.VIEWER:
            access_rows = AnalysisAccess.objects.filter(models.Q(owner=user) | models.Q(assigned_users=user))
        analysis_ids = access_rows.values_list("analysis_id", flat=True)
        jobs = existJobs.jobs.filter(jobID__in=analysis_ids)
    jobs = jobs.order_by("-date")
    finished = jobs.filter(status="finished")
    return JsonResponse({
        "jobs": serializers.serialize("json", jobs),
        "running_jobs_cnt": jobs.filter(status="running").count(),
        "finished_jobs": serializers.serialize("json", finished),
    })


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
            original = pattern.callback
            protected = require_capability("analysis.run")(original)
            if pattern.name == "react_send_page1":
                @wraps(protected)
                def protected_and_register(request, *args, _view=protected, **kwargs):
                    response = _view(request, *args, **kwargs)
                    try:
                        payload = json.loads(response.content)
                        register_analysis(payload.get("newJobID"), request.user)
                    except (AttributeError, TypeError, ValueError):
                        pass
                    return response
                protected = protected_and_register
            pattern._callback = protected
    return patterns
