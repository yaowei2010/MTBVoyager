from django.urls import path

from . import views


urlpatterns = [
    path("subject", views.subject),
    path("upload", views.upload),
    path("mondo/search", views.mondo_search),
    path("literature/status", views.literature_status),
    path("jobs", views.jobs),
    path("jobs/<str:analysis_id>", views.job_detail),
    path("jobs/<str:analysis_id>/snv", views.snv_results),
    path("jobs/<str:analysis_id>/sv", views.sv_results),
    path("jobs/<str:analysis_id>/pharmcat", views.pharmcat_results),
    path("jobs/<str:analysis_id>/literature", views.literature_summary),
]
