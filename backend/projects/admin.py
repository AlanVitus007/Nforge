from django.contrib import admin
from .models import Project, ProjectMember, ProjectInvitation

admin.site.register(Project)


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "user", "role", "created_at", "updated_at")
    list_filter = ("role", "created_at")
    search_fields = ("project__title", "user__username", "user__email")
    raw_id_fields = ("project", "user")


@admin.register(ProjectInvitation)
class ProjectInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "invited_user",
        "invited_by",
        "role",
        "status",
        "created_at",
        "responded_at",
    )
    list_filter = ("role", "status", "created_at", "responded_at")
    search_fields = (
        "project__title",
        "invited_user__username",
        "invited_user__email",
        "invited_by__username",
        "invited_by__email",
    )
    raw_id_fields = ("project", "invited_user", "invited_by")
