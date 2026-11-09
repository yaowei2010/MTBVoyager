from django.contrib import admin

from .models import AnalysisAccess, AuditLog, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "updated_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_id")
    list_filter = ("action",)
    search_fields = ("actor__username", "target_id")
    readonly_fields = (
        "actor", "action", "target_type", "target_id", "detail", "ip_address", "created_at"
    )


@admin.register(AnalysisAccess)
class AnalysisAccessAdmin(admin.ModelAdmin):
    list_display = ("analysis_id", "owner", "updated_at")
    search_fields = ("analysis_id", "owner__username")
    filter_horizontal = ("assigned_users",)
