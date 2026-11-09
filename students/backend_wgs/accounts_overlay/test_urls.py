from django.http import JsonResponse
from django.urls import include, path

from .access import require_analysis_access, require_capability


@require_capability("analysis.run")
def run_job(request):
    return JsonResponse({"status": "accepted"}, status=202)


@require_analysis_access
def result(request, analysis_id):
    return JsonResponse({"analysis_id": analysis_id})


urlpatterns = [
    path("ncku_hospital/accounts/", include("accounts.urls")),
    path("ncku_hospital/test/run-job", run_job),
    path("ncku_hospital/test/results/<str:analysis_id>", result),
]
