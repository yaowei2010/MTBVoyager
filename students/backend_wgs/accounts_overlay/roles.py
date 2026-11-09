from .models import UserProfile


ROLE_PERMISSIONS = {
    UserProfile.Role.ADMIN: {
        "analysis.create",
        "analysis.run",
        "analysis.rerun",
        "analysis.view_all",
        "analysis.download",
        "analysis.delete_any",
        "report.edit",
        "report.generate_ai",
        "account.manage",
        "audit.view",
    },
    UserProfile.Role.USER: {
        "analysis.create",
        "analysis.run",
        "analysis.rerun",
        "analysis.view_own",
        "analysis.download",
        "analysis.delete_own",
        "report.edit",
        "report.generate_ai",
    },
    UserProfile.Role.VIEWER: {
        "analysis.view_assigned",
        "analysis.download",
    },
}


def get_role(user):
    if user.is_superuser:
        return UserProfile.Role.ADMIN
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.role


def get_permissions(user):
    return sorted(ROLE_PERMISSIONS[get_role(user)])


def has_role(user, *roles):
    return bool(user and user.is_authenticated and get_role(user) in roles)
