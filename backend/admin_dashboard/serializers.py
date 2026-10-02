from django.contrib.auth.models import User
from rest_framework import serializers

from ai.models import PaperChunk, ResearchSession
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


class AdminPaperProjectSerializer(serializers.ModelSerializer):
    owner = AdminProjectOwnerSerializer(read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'title', 'owner', 'owner_username']
        read_only_fields = fields


class AdminPaperChunkSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperChunk
        fields = ['id', 'chunk_index', 'page_number', 'created_at']
        read_only_fields = fields


class AdminPaperListSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    project = AdminPaperProjectSerializer(read_only=True)
    project_id = serializers.IntegerField(source='project.id', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    project_owner = serializers.CharField(source='project.owner.username', read_only=True)
    project_owner_id = serializers.IntegerField(source='project.owner.id', read_only=True)
    chunk_count = serializers.IntegerField(read_only=True, default=0)
    page_count = serializers.IntegerField(read_only=True, default=None, allow_null=True)
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = [
            'id',
            'title',
            'file_name',
            'project',
            'project_id',
            'project_title',
            'project_owner',
            'project_owner_id',
            'uploaded_at',
            'processing_status',
            'page_count',
            'chunk_count',
        ]
        read_only_fields = fields

    def get_file_name(self, obj):
        return obj.file.name if obj.file else ''

    def get_processing_status(self, obj):
        chunk_count = getattr(obj, 'chunk_count', None)
        if chunk_count is not None and chunk_count > 0:
            return 'PROCESSED'
        if bool(obj.extracted_text):
            return 'PROCESSED'
        return 'PENDING'


class AdminPaperDetailSerializer(AdminPaperListSerializer):
    has_extracted_text = serializers.SerializerMethodField()
    extracted_text_length = serializers.SerializerMethodField()
    chunks = AdminPaperChunkSummarySerializer(many=True, read_only=True, default=list)

    class Meta(AdminPaperListSerializer.Meta):
        fields = AdminPaperListSerializer.Meta.fields + [
            'has_extracted_text',
            'extracted_text_length',
            'chunks',
        ]
        read_only_fields = fields

    def get_has_extracted_text(self, obj):
        return bool(obj.extracted_text)

    def get_extracted_text_length(self, obj):
        return len(obj.extracted_text) if obj.extracted_text else 0


class AdminRecentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined', 'is_active']
        read_only_fields = fields


class AdminRecentPaperSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    project_id = serializers.IntegerField(source='project.id', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    owner_username = serializers.CharField(source='project.owner.username', read_only=True)

    class Meta:
        model = Paper
        fields = [
            'id',
            'title',
            'file_name',
            'project_id',
            'project_title',
            'owner_username',
            'uploaded_at',
        ]
        read_only_fields = fields

    def get_file_name(self, obj):
        return obj.file.name if obj.file else ''


class AdminRecentResearchSessionSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source='project.id', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    message_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ResearchSession
        fields = [
            'id',
            'title',
            'project_id',
            'project_title',
            'created_at',
            'updated_at',
            'message_count',
        ]
        read_only_fields = fields



