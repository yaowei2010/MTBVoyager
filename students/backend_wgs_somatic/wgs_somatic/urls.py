from django.urls import path
from . import views
urlpatterns=[
 path('subjects',views.subject),path('uploads',views.upload),path('jobs',views.jobs),
 path('jobs/<str:analysis_id>',views.job_detail),path('jobs/<str:analysis_id>/results',views.results),path('jobs/<str:analysis_id>/summary',views.summary),
 path('legacy-oncogenicity',views.legacy_oncogenicity),
]
