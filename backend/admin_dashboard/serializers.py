import json
from django.contrib.auth.models import User
from rest_framework import serializers

from ai.models import PaperChunk, ResearchMessage, ResearchSession
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


def classify_operation(content):
    """
    Classify AI operation type and human-readable label from ResearchMessage content
    without exposing the actual content.
    """
    if not content:
        return "ASK_AI", "Paper Q&A"

    text = content.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if any(k in data for k in [
                    "common_limitations", "methodological_gaps", "dataset_population_gaps",
                    "understudied_areas", "unanswered_research_questions", "future_research_directions",
                    "contradictions_inconsistencies", "gap_analysis"
                ]):
                    return "GAP_ANALYSIS", "Research Gap Analysis"
                if any(k in data for k in [
                    "similarities", "differences", "methodology_comparison",
                    "findings_comparison", "research_gaps", "comparison"
                ]):
                    return "COMPARE_PAPERS", "Paper Comparison"
                if "themes" in data or "thematic_analysis" in data:
                    return "THEMATIC_ANALYSIS", "Thematic Analysis"
                if any(k in data for k in [
                    "research_evolution", "methodological_shifts", "trend_analysis"
                ]):
                    return "RESEARCH_TRENDS", "Research Trend Analysis"
        except Exception:
            pass

    # Quick substring check fallback
    if '"common_limitations"' in text or '"methodological_gaps"' in text or '"gap_analysis"' in text:
        return "GAP_ANALYSIS", "Research Gap Analysis"
    if '"similarities"' in text or '"differences"' in text or '"methodology_comparison"' in text:
        return "COMPARE_PAPERS", "Paper Comparison"
    if '"themes"' in text:
        return "THEMATIC_ANALYSIS", "Thematic Analysis"
    if '"research_evolution"' in text or '"methodological_shifts"' in text:
        return "RESEARCH_TRENDS", "Research Trend Analysis"

    return "ASK_AI", "Paper Q&A"


class AdminAIUsageItemSerializer(serializers.ModelSerializer):
    """
    Safe serializer for AI activity log items without exposing user prompts,
    assistant answers, message content, extracted text, or embeddings.
    """
    session_id = serializers.IntegerField(source='session.id', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    project_id = serializers.IntegerField(source='session.project.id', read_only=True)
    project_title = serializers.CharField(source='session.project.title', read_only=True)
    user_id = serializers.IntegerField(source='session.project.owner.id', read_only=True)
    username = serializers.CharField(source='session.project.owner.username', read_only=True)
    operation = serializers.SerializerMethodField()
    operation_name = serializers.SerializerMethodField()
    evidence_count = serializers.SerializerMethodField()
    has_evidence = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ResearchMessage
        fields = [
            'id',
            'session_id',
            'session_title',
            'project_id',
            'project_title',
            'user_id',
            'username',
            'role',
            'operation',
            'operation_name',
            'evidence_count',
            'has_evidence',
            'status',
            'created_at',
        ]
        read_only_fields = fields

    def get_operation(self, obj):
        op_code, _ = classify_operation(obj.content)
        return op_code

    def get_operation_name(self, obj):
        _, op_name = classify_operation(obj.content)
        return op_name

    def get_evidence_count(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'evidence' in obj._prefetched_objects_cache:
            return len(obj.evidence.all())
        return obj.evidence.count()

    def get_has_evidence(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'evidence' in obj._prefetched_objects_cache:
            return len(obj.evidence.all()) > 0
        return obj.evidence.exists()

    def get_status(self, obj):
        return "SUCCESS"


class AdminActivityPaperSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = ['id', 'title', 'file_name', 'uploaded_at']
        read_only_fields = fields

    def get_file_name(self, obj):
        return obj.file.name if obj.file else ''


class AdminActivityDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a single activity/message event.
    Provides complete structural context (user, role, session, project, papers, citations)
    with strict exclusion of message body, prompts, evidence text, and extracted text.
    """
    session_id = serializers.IntegerField(source='session.id', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    project_id = serializers.IntegerField(source='session.project.id', read_only=True)
    project_title = serializers.CharField(source='session.project.title', read_only=True)
    project_owner = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='session.project.owner.id', read_only=True)
    username = serializers.CharField(source='session.project.owner.username', read_only=True)
    user_role = serializers.SerializerMethodField()
    operation = serializers.SerializerMethodField()
    operation_name = serializers.SerializerMethodField()
    operation_type = serializers.SerializerMethodField()
    operation_display_name = serializers.SerializerMethodField()
    message_role = serializers.CharField(source='role', read_only=True)
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    evidence_count = serializers.SerializerMethodField()
    has_evidence = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    related_papers = serializers.SerializerMethodField()
    citations = serializers.SerializerMethodField()
    privacy_notice = serializers.SerializerMethodField()

    class Meta:
        model = ResearchMessage
        fields = [
            'id',
            'session_id',
            'session_title',
            'project_id',
            'project_title',
            'project_owner',
            'user_id',
            'username',
            'user_role',
            'role',
            'message_role',
            'operation',
            'operation_name',
            'operation_type',
            'operation_display_name',
            'evidence_count',
            'has_evidence',
            'status',
            'related_papers',
            'citations',
            'privacy_notice',
            'created_at',
            'timestamp',
        ]
        read_only_fields = fields

    def get_project_owner(self, obj):
        owner = getattr(obj.session.project, 'owner', None)
        if owner:
            return {
                'id': owner.id,
                'username': owner.username,
                'email': owner.email,
            }
        return None

    def get_user_role(self, obj):
        return "OWNER"

    def get_operation(self, obj):
        op_code, _ = classify_operation(obj.content)
        return op_code

    def get_operation_name(self, obj):
        _, op_name = classify_operation(obj.content)
        return op_name

    def get_operation_type(self, obj):
        return self.get_operation(obj)

    def get_operation_display_name(self, obj):
        return self.get_operation_name(obj)

    def get_evidence_count(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'evidence' in obj._prefetched_objects_cache:
            return len(obj.evidence.all())
        return obj.evidence.count()

    def get_has_evidence(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'evidence' in obj._prefetched_objects_cache:
            return len(obj.evidence.all()) > 0
        return obj.evidence.exists()

    def get_status(self, obj):
        return "COMPLETED"

    def get_related_papers(self, obj):
        papers_dict = {}
        if hasattr(obj.session, 'papers'):
            for p in obj.session.papers.all():
                papers_dict[p.id] = p

        if hasattr(obj, '_prefetched_objects_cache') and 'evidence' in obj._prefetched_objects_cache:
            for ev in obj.evidence.all():
                if ev.paper_id and ev.paper:
                    papers_dict[ev.paper_id] = ev.paper
        else:
            for ev in obj.evidence.select_related('paper').all():
                if ev.paper:
                    papers_dict[ev.paper.id] = ev.paper

        return AdminActivityPaperSerializer(list(papers_dict.values()), many=True).data

    def get_citations(self, obj):
        evidences = (
            obj.evidence.all()
            if (hasattr(obj, '_prefetched_objects_cache') and 'evidence' in obj._prefetched_objects_cache)
            else obj.evidence.select_related('paper').all()
        )
        citations = []
        for ev in evidences:
            citations.append({
                'citation_id': getattr(ev, 'citation_id', f"cite_p{ev.paper_id}_c{ev.chunk_id}"),
                'paper_id': ev.paper_id,
                'paper_title': ev.paper.title if ev.paper else '',
                'page_number': ev.page_number,
            })
        return citations

    def get_privacy_notice(self, obj):
        return "Private research dialogue content, user prompts, assistant answers, and evidence texts are intentionally excluded to protect researcher intellectual property."





