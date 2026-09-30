from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Project, ProjectMember, ProjectInvitation
from .permissions import (
    can_view_project,
    can_edit_project_content,
    can_manage_project,
    get_projects_for_user,
    IsProjectOwnerOrReadOnlyMember,
)
from .serializers import (
    ProjectSerializer,
    ProjectMemberSerializer,
    ProjectInvitationSerializer,
    ProjectInviteSerializer,
)


class ProjectListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/   — list all projects owned by or shared with the authenticated user.
    POST /api/projects/   — create a new project owned by the authenticated user.
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_projects_for_user(self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/projects/<id>/  — retrieve a single project (owner or member).
    PUT    /api/projects/<id>/  — full update (owner only).
    PATCH  /api/projects/<id>/  — partial update (owner only).
    DELETE /api/projects/<id>/  — delete (owner only).
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrReadOnlyMember]

    def get_queryset(self):
        # Users can access projects they own or are members of
        return get_projects_for_user(self.request.user)


class ProjectInviteMemberView(APIView):
    """
    POST /api/projects/<project_id>/members/invite/
    Only the project owner can send invitations.
    Allowed roles: EDITOR, VIEWER.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)

        if project.owner != request.user:
            return Response(
                {"detail": "Only the project owner can send invitations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        role_raw = request.data.get("role")
        if role_raw == "OWNER" or role_raw == ProjectMember.ROLE_OWNER:
            return Response(
                {"detail": "Cannot invite a user as OWNER."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProjectInviteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data["username"].strip()
        role = serializer.validated_data["role"]

        invited_user = User.objects.filter(username=username).first()
        if not invited_user:
            return Response(
                {"detail": f"User '{username}' does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invited_user == request.user or invited_user == project.owner:
            return Response(
                {"detail": "You cannot invite yourself to your own project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ProjectMember.objects.filter(project=project, user=invited_user).exists():
            return Response(
                {"detail": "User is already a member of this project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ProjectInvitation.objects.filter(
            project=project,
            invited_user=invited_user,
            status=ProjectInvitation.STATUS_PENDING,
        ).exists():
            return Response(
                {"detail": "A pending invitation already exists for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation = ProjectInvitation.objects.create(
            project=project,
            invited_user=invited_user,
            invited_by=request.user,
            role=role,
            status=ProjectInvitation.STATUS_PENDING,
        )

        return Response(
            ProjectInvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectMemberListView(APIView):
    """
    GET /api/projects/<project_id>/members/
    Restricted to project owner and existing project members.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)

        is_owner = (project.owner == request.user)
        is_member = ProjectMember.objects.filter(project=project, user=request.user).exists()
        if not (is_owner or is_member):
            return Response(
                {"detail": "You do not have permission to view members of this project."},
                status=status.HTTP_403_FORBIDDEN,
            )

        members = (
            ProjectMember.objects.filter(project=project)
            .select_related("user")
            .order_by("created_at")
        )
        return Response(
            ProjectMemberSerializer(members, many=True).data,
            status=status.HTTP_200_OK,
        )


class ProjectMemberDetailView(APIView):
    """
    DELETE /api/projects/<project_id>/members/<user_id>/
    Only the project owner can remove a member.
    Owner cannot remove themselves.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id, user_id):
        project = get_object_or_404(Project, pk=project_id)
        is_owner = (project.owner == request.user)
        is_member = ProjectMember.objects.filter(project=project, user=request.user).exists()
        if not (is_owner or is_member):
            return Response(
                {"detail": "You do not have permission to view this project's members."},
                status=status.HTTP_403_FORBIDDEN,
            )
        member = get_object_or_404(ProjectMember, project=project, user_id=user_id)
        return Response(ProjectMemberSerializer(member).data, status=status.HTTP_200_OK)

    def delete(self, request, project_id, user_id):
        project = get_object_or_404(Project, pk=project_id)

        if project.owner != request.user:
            return Response(
                {"detail": "Only the project owner can remove members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user_id == project.owner.id:
            return Response(
                {"detail": "Project owner cannot be removed from the project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member = ProjectMember.objects.filter(project=project, user_id=user_id).first()
        if not member:
            return Response(
                {"detail": "Project member not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectLeaveView(APIView):
    """
    POST /api/projects/<project_id>/leave/
    Authenticated user must be a ProjectMember.
    Project owner cannot leave.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)

        if project.owner == request.user:
            return Response(
                {"detail": "Project owner cannot leave the project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member = ProjectMember.objects.filter(project=project, user=request.user).first()
        if not member:
            return Response(
                {"detail": "You are not a member of this project."},
                status=status.HTTP_403_FORBIDDEN,
            )

        member.delete()
        return Response(
            {"detail": "You have left the project successfully."},
            status=status.HTTP_200_OK,
        )


class UserInvitationListView(APIView):
    """
    GET /api/projects/invitations/
    Returns pending invitations for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        status_param = request.query_params.get("status")
        queryset = ProjectInvitation.objects.filter(invited_user=request.user).select_related(
            "project", "invited_by"
        )
        if status_param and status_param.upper() == "ALL":
            queryset = queryset.order_by("-created_at")
        elif status_param:
            queryset = queryset.filter(status=status_param.upper()).order_by("-created_at")
        else:
            queryset = queryset.filter(status=ProjectInvitation.STATUS_PENDING).order_by("-created_at")

        return Response(
            ProjectInvitationSerializer(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )


class InvitationAcceptView(APIView):
    """
    POST /api/projects/invitations/<invitation_id>/accept/
    Only the invited_user can accept.
    Must be PENDING.
    Atomic operation: creates ProjectMember and marks invitation ACCEPTED.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invitation_id):
        invitation = get_object_or_404(ProjectInvitation, pk=invitation_id)

        if invitation.invited_user != request.user:
            return Response(
                {"detail": "You do not have permission to accept this invitation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.status != ProjectInvitation.STATUS_PENDING:
            return Response(
                {"detail": "Invitation is not pending."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            member, created = ProjectMember.objects.get_or_create(
                project=invitation.project,
                user=invitation.invited_user,
                defaults={"role": invitation.role},
            )
            if not created and member.role != invitation.role:
                member.role = invitation.role
                member.save(update_fields=["role", "updated_at"])

            invitation.status = ProjectInvitation.STATUS_ACCEPTED
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=["status", "responded_at", "updated_at"])

        data = ProjectInvitationSerializer(invitation).data
        data["detail"] = "Invitation accepted successfully."
        return Response(data, status=status.HTTP_200_OK)


class InvitationDeclineView(APIView):
    """
    POST /api/projects/invitations/<invitation_id>/decline/
    Only the invited_user can decline.
    Must be PENDING.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invitation_id):
        invitation = get_object_or_404(ProjectInvitation, pk=invitation_id)

        if invitation.invited_user != request.user:
            return Response(
                {"detail": "You do not have permission to decline this invitation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.status != ProjectInvitation.STATUS_PENDING:
            return Response(
                {"detail": "Invitation is not pending."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation.status = ProjectInvitation.STATUS_DECLINED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at", "updated_at"])

        data = ProjectInvitationSerializer(invitation).data
        data["detail"] = "Invitation declined successfully."
        return Response(data, status=status.HTTP_200_OK)


class InvitationCancelView(APIView):
    """
    POST /api/projects/invitations/<invitation_id>/cancel/
    Only the project owner can cancel.
    Must be PENDING.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invitation_id):
        invitation = get_object_or_404(ProjectInvitation, pk=invitation_id)

        if invitation.project.owner != request.user:
            return Response(
                {"detail": "Only the project owner can cancel invitations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.status != ProjectInvitation.STATUS_PENDING:
            return Response(
                {"detail": "Invitation is not pending."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation.status = ProjectInvitation.STATUS_CANCELLED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at", "updated_at"])

        data = ProjectInvitationSerializer(invitation).data
        data["detail"] = "Invitation cancelled successfully."
        return Response(data, status=status.HTTP_200_OK)
