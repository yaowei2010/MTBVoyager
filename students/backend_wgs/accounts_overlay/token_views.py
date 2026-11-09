from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.views import TokenObtainPairView

from .postgres_audit import record_login, sync_account
from .roles import get_role


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",", 1)[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


class AuditedTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        username = str(request.data.get("username", "")).strip()
        user = User.objects.filter(username=username).first()
        common = {
            "user": user,
            "username": username,
            "role": get_role(user) if user else None,
            "ip_address": _client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed as exc:
            record_login(**common, success=False, failure_reason="invalid_credentials_or_inactive")
            raise exc

        if user:
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            common["role"] = get_role(user)
            sync_account(user, common["role"])
        record_login(**common, success=True, failure_reason="")
        return response
