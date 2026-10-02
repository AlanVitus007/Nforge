from django.contrib.auth.models import User
from rest_framework import serializers

from ai.models import ResearchSession
from papers.models import Paper
from projects.models import Project


class AdminUserListSerializer(serializers.ModelSerializer):
    project_count = serializers.IntegerField(read_only=True, default=0)
    membership_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'is_active',
            'is_staff',
            'is_superuser',
            'project_count',
            'membership_count',
        ]
        read_only_fields = fields


class AdminUserProjectMembershipSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)
    role = serializers.CharField(read_only=True)
    paper_count = serializers.IntegerField(read_only=True, default=0)
    created_at = serializers.DateTimeField(read_only=True)


class AdminUserDetailSerializer(AdminUserListSerializer):
    projects = AdminUserProjectMembershipSerializer(many=True, read_only=True, default=list)

    class Meta(AdminUserListSerializer.Meta):
        fields = AdminUserListSerializer.Meta.fields + ['projects']
        read_only_fields = fields


class AdminProjectOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = fields


class AdminPaperSummarySerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = ['id', 'title', 'file_name', 'uploaded_at']
        read_only_fields = fields

    def get_file_name(self, obj):
        return obj.file.name if obj.file else ''


class AdminResearchSessionSummarySerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ResearchSession
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count']
        read_only_fields = fields


class AdminProjectMemberSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, allow_null=True)
    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class AdminProjectListSerializer(serializers.ModelSerializer):
    owner = AdminProjectOwnerSerializer(read_only=True)
    owner_id = serializers.IntegerField(source='owner.id', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    paper_count = serializers.IntegerField(read_only=True, default=0)
    member_count = serializers.IntegerField(read_only=True, default=0)
    research_session_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'description',
            'owner',
            'owner_id',
            'owner_username',
            'created_at',
            'updated_at',
            'paper_count',
            'member_count',
            'research_session_count',
        ]
        read_only_fields = fields


class AdminProjectDetailSerializer(AdminProjectListSerializer):
    members = AdminProjectMemberSerializer(many=True, read_only=True, default=list)
    papers = AdminPaperSummarySerializer(many=True, read_only=True, default=list)
    research_sessions = AdminResearchSessionSummarySerializer(many=True, read_only=True, default=list)

    class Meta(AdminProjectListSerializer.Meta):
        fields = AdminProjectListSerializer.Meta.fields + ['members', 'papers', 'research_sessions']
        read_only_fields = fields

