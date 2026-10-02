from rest_framework import serializers
from .models import Project, ProjectMember, ProjectInvitation


class ProjectSerializer(serializers.ModelSerializer):
    # owner is read-only; set from request.user in the view
    owner = serializers.ReadOnlyField(source='owner.username')
    paper_count = serializers.IntegerField(source='papers.count', read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'owner', 'title', 'description', 'paper_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'owner', 'paper_count', 'created_at', 'updated_at')


class ProjectMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ProjectMember
        fields = (
            "id",
            "project",
            "user",
            "user_id",
            "username",
            "role",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProjectInvitationSerializer(serializers.ModelSerializer):
    invitation_id = serializers.IntegerField(source="id", read_only=True)
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)
    inviter_username = serializers.CharField(source="invited_by.username", read_only=True)
    invited_by = serializers.CharField(source="invited_by.username", read_only=True)
    invited_user_id = serializers.IntegerField(source="invited_user.id", read_only=True)
    invited_username = serializers.CharField(source="invited_user.username", read_only=True)

    class Meta:
        model = ProjectInvitation
        fields = (
            "id",
            "invitation_id",
            "project",
            "project_id",
            "project_title",
            "inviter_username",
            "invited_by",
            "invited_user",
            "invited_user_id",
            "invited_username",
            "role",
            "status",
            "created_at",
            "responded_at",
            "updated_at",
        )
        read_only_fields = fields


class ProjectInviteSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    role = serializers.ChoiceField(
        choices=[ProjectInvitation.ROLE_EDITOR, ProjectInvitation.ROLE_VIEWER],
        default=ProjectInvitation.ROLE_VIEWER,
    )
