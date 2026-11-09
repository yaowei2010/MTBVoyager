"""
URL configuration for uploadfunction project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from accounts.access import accessible_job_list, protect_legacy_analysis_patterns
from hw1.urls import urlpatterns as legacy_urlpatterns


urlpatterns = [
    path('admin/', admin.site.urls),
    path('ncku_hospital/wgs-germline/', include('wgs_germline.urls')),
    path('ncku_hospital/wgs-somatic/', include('wgs_somatic.urls')),
    path('ncku_hospital/job_list', accessible_job_list, name='rbac_job_list'),
    path('ncku_hospital/', include((protect_legacy_analysis_patterns(legacy_urlpatterns), 'hw1'))),
    path('ncku_hospital/accounts/', include('accounts.urls')),
]
