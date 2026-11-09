from django.urls import include, path


urlpatterns = [path("ncku_hospital/accounts/", include("accounts.urls"))]
