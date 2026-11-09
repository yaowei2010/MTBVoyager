from rest_framework.permissions import BasePermission

from .models import UserProfile
from .roles import get_permissions, has_role


class IsAdminRole(BasePermission):
    message = "Administrator role is required."

    def has_permission(self, request, view):
        return has_role(request.user, UserProfile.Role.ADMIN)


class IsAnalysisWriter(BasePermission):
    message = "This account has read-only access."

    def has_permission(self, request, view):
        return "analysis.run" in get_permissions(request.user)
