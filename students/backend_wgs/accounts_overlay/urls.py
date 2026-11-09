from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .token_views import AuditedTokenObtainPairView


urlpatterns = [
    path("token/", AuditedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", views.me, name="account_me"),
    path("me/password/", views.change_own_password, name="change_own_password"),
    path("user-info", views.me, name="user_info"),
    path("register/", views.users, name="register"),
    path("users/", views.users, name="account_users"),
    path("users/<int:user_id>/", views.user_detail, name="account_user_detail"),
    path("users/<int:user_id>/reset-password/", views.reset_password, name="account_reset_password"),
    path("audit-logs/", views.audit_logs, name="account_audit_logs"),
    path("cases/", views.case_access_list, name="case_access_list"),
    path("cases/<str:analysis_id>/access/", views.case_access_detail, name="case_access_detail"),
]
