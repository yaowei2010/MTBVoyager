from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AnalysisAccess, AuditLog, UserProfile
from .permissions import IsAdminRole
from .roles import get_permissions, get_role


VALID_ROLES = {choice for choice, _ in UserProfile.Role.choices}


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",", 1)[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


def _audit(request, action, target=None, detail=None):
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        target_type="user" if target else "",
        target_id=str(target.pk) if target else "",
        detail=detail or {},
        ip_address=_client_ip(request),
    )


def _serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": get_role(user),
        "permissions": get_permissions(user),
        "is_active": user.is_active,
        "last_login": user.last_login,
        "date_joined": user.date_joined,
    }


def _validate_role(role):
    if role not in VALID_ROLES:
        raise ValidationError({"role": "Role must be admin, user, or viewer."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(_serialize_user(request.user))


# Backward-compatible endpoint used by the current UI.
get_user_info = me


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminRole])
def users(request):
    if request.method == "GET":
        queryset = User.objects.select_related("mtb_profile").order_by("username")
        return Response([_serialize_user(user) for user in queryset])

    data = request.data
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    role = str(data.get("role", UserProfile.Role.USER)).strip().lower()
    if not username or not password:
        return Response({"detail": "username and password are required"}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({"username": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        _validate_role(role)
        validate_password(password)
    except ValidationError as exc:
        detail = exc.message_dict if hasattr(exc, "message_dict") else {"password": exc.messages}
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            password=password,
            email=str(data.get("email", "")).strip(),
            first_name=str(data.get("first_name", "")).strip(),
            last_name=str(data.get("last_name", "")).strip(),
        )
        UserProfile.objects.update_or_create(user=user, defaults={"role": role})
        _audit(request, "account.created", user, {"role": role})
    return Response(_serialize_user(user), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsAdminRole])
def user_detail(request, user_id):
    try:
        target = User.objects.select_related("mtb_profile").get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(_serialize_user(target))

    data = request.data
    old_role = get_role(target)
    new_role = str(data.get("role", old_role)).strip().lower()
    try:
        _validate_role(new_role)
    except ValidationError as exc:
        return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)

    new_active = bool(data.get("is_active", target.is_active))
    if target.pk == request.user.pk and (new_role != UserProfile.Role.ADMIN or not new_active):
        return Response(
            {"detail": "Administrators cannot remove their own admin access or disable themselves."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        target.email = str(data.get("email", target.email)).strip()
        target.first_name = str(data.get("first_name", target.first_name)).strip()
        target.last_name = str(data.get("last_name", target.last_name)).strip()
        target.is_active = new_active
        target.save(update_fields=["email", "first_name", "last_name", "is_active"])
        UserProfile.objects.update_or_create(user=target, defaults={"role": new_role})
        _audit(request, "account.updated", target, {"role": new_role, "is_active": new_active})
    return Response(_serialize_user(target))


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminRole])
def reset_password(request, user_id):
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    password = str(request.data.get("password", ""))
    try:
        validate_password(password, user=target)
    except ValidationError as exc:
        return Response({"password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
    target.set_password(password)
    target.save(update_fields=["password"])
    _audit(request, "account.password_reset", target)
    return Response({"detail": "Password updated."})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminRole])
def audit_logs(request):
    limit = min(max(int(request.query_params.get("limit", 100)), 1), 500)
    rows = AuditLog.objects.select_related("actor")[:limit]
    return Response([
        {
            "id": row.id,
            "actor": row.actor.username if row.actor else None,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "detail": row.detail,
            "ip_address": row.ip_address,
            "created_at": row.created_at,
        }
        for row in rows
    ])


def _serialize_access(row):
    return {
        "analysis_id": row.analysis_id,
        "owner": (
            {"id": row.owner_id, "username": row.owner.username}
            if row.owner_id else None
        ),
        "assigned_users": [
            {"id": user.id, "username": user.username, "role": get_role(user)}
            for user in row.assigned_users.all().order_by("username")
        ],
        "updated_at": row.updated_at,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminRole])
def case_access_list(request):
    rows = AnalysisAccess.objects.select_related("owner").prefetch_related("assigned_users").order_by("-updated_at")
    query = str(request.query_params.get("q", "")).strip()
    if query:
        rows = rows.filter(analysis_id__icontains=query)
    return Response([_serialize_access(row) for row in rows[:500]])


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsAdminRole])
def case_access_detail(request, analysis_id):
    try:
        row = AnalysisAccess.objects.select_related("owner").prefetch_related("assigned_users").get(
            analysis_id=analysis_id
        )
    except AnalysisAccess.DoesNotExist:
        return Response({"detail": "Analysis not found."}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response(_serialize_access(row))

    assigned_ids = request.data.get("assigned_user_ids", [])
    if not isinstance(assigned_ids, list):
        return Response({"assigned_user_ids": "Expected a list of user IDs."}, status=status.HTTP_400_BAD_REQUEST)
    assigned = list(User.objects.filter(id__in=assigned_ids, is_active=True))
    if len(assigned) != len(set(assigned_ids)):
        return Response({"assigned_user_ids": "One or more users are invalid or inactive."}, status=status.HTTP_400_BAD_REQUEST)
    row.assigned_users.set(assigned)
    _audit(
        request,
        "analysis.assignment_updated",
        detail={"analysis_id": row.analysis_id, "assigned_user_ids": sorted(assigned_ids)},
    )
    return Response(_serialize_access(row))


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminRole])
def register(request):
    # Preserve the old URL while enforcing the new admin-only creation policy.
    return users(request._request)
