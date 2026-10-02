from django.db.models import Q
from rest_framework import permissions

from .models import Project, ProjectMember


def is_project_owner(user, project):
    """
    Check if the user is the authoritative owner of the project.
    """
    if not user or not user.is_authenticated or not project:
        return False
    return project.owner_id == user.id


def get_project_role(user, project):
    """
    Return the user's role in the project ('OWNER', 'EDITOR', 'VIEWER', or None).
    """
    if not user or not user.is_authenticated or not project:
        return None

    if project.owner_id == user.id:
        return ProjectMember.ROLE_OWNER

    membership = ProjectMember.objects.filter(project=project, user=user).first()
    if membership:
        return membership.role

    return None


def can_view_project(user, project):
    """
    Check if user can view the project and its read-only content (papers, sessions, evidence).
    Allowed: OWNER, EDITOR, VIEWER.
    """
    role = get_project_role(user, project)
    return role in (
        ProjectMember.ROLE_OWNER,
        ProjectMember.ROLE_EDITOR,
        ProjectMember.ROLE_VIEWER,
    )


def can_edit_project_content(user, project):
    """
    Check if user can upload, modify, or delete papers.
    Allowed: OWNER, EDITOR.
    """
    role = get_project_role(user, project)
    return role in (ProjectMember.ROLE_OWNER, ProjectMember.ROLE_EDITOR)


def can_write_research(user, project):
    """
    Check if user can create/modify research sessions and execute new AI analyses.
    Allowed: OWNER, EDITOR.
    """
    role = get_project_role(user, project)
    return role in (ProjectMember.ROLE_OWNER, ProjectMember.ROLE_EDITOR)


def can_manage_project(user, project):
    """
    Check if user can rename/delete the project or manage collaborators.
    Allowed: OWNER only.
    """
    return is_project_owner(user, project)


def get_projects_for_user(user):
    """
    Return queryset of projects where user is owner OR has an active membership.
    """
    if not user or not user.is_authenticated:
        return Project.objects.none()
    return Project.objects.filter(
        Q(owner=user) | Q(members__user=user)
    ).distinct()


class IsProjectOwnerOrReadOnlyMember(permissions.BasePermission):
    """
    Object-level permission for ProjectDetailView:
    - SAFE_METHODS (GET, HEAD, OPTIONS): allowed for project owner and project members.
    - Non-safe methods (PUT, PATCH, DELETE): allowed for project owner only.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return can_view_project(request.user, obj)
        return is_project_owner(request.user, obj)
