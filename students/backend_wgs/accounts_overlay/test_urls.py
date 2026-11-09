from django.http import JsonResponse
from django.urls import include, path

from .access import require_capability


@require_capability("analysis.run")
def run_job(request):
    return JsonResponse({"status": "accepted"}, status=202)


urlpatterns = [
    path("ncku_hospital/accounts/", include("accounts.urls")),
    path("ncku_hospital/test/run-job", run_job),
]
