from django.urls import path
from . import views
urlpatterns=[
 path('subjects',views.subject),path('uploads',views.upload),path('jobs',views.jobs),
 path('jobs/<str:analysis_id>',views.job_detail),path('jobs/<str:analysis_id>/results',views.results),path('jobs/<str:analysis_id>/summary',views.summary),path('jobs/<str:analysis_id>/downstream',views.downstream),
 path('jobs/<str:analysis_id>/mtb-report',views.mtb_report),
 path('legacy-oncogenicity',views.legacy_oncogenicity),
 path('legacy-jobs/<str:analysis_id>/mtb-report',views.legacy_mtb_report),
]
