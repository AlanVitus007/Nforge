from rest_framework import serializers
from papers.models import Paper
from .models import ResearchSession, ResearchMessage, ResearchEvidence


class ResearchEvidenceSerializer(serializers.ModelSerializer):
    paper_id = serializers.IntegerField(source="paper.id", read_only=True)
    paper_title = serializers.CharField(source="paper.title", read_only=True)
    chunk_id = serializers.SerializerMethodField()
    citation_id = serializers.CharField(read_only=True)

    class Meta:
        model = ResearchEvidence
        fields = ("id", "paper_id", "paper_title", "chunk_id", "page_number", "text", "citation_id")

    def get_chunk_id(self, obj):
        return obj.chunk_id


class ResearchMessageSerializer(serializers.ModelSerializer):
    evidence = ResearchEvidenceSerializer(many=True, read_only=True)
    notes_used = serializers.SerializerMethodField()
    notes_used_count = serializers.SerializerMethodField()

    class Meta:
        model = ResearchMessage
        fields = ("id", "role", "content", "created_at", "evidence", "notes_used", "notes_used_count")

    def get_notes_used(self, obj):
        metadata = obj.metadata or {}
        if not isinstance(metadata, dict):
            return []
        notes_used = metadata.get("notes_used", [])
        if not notes_used:
            return []

        # Privacy check: only expose notes_used if requesting user matches author user_id
        request = self.context.get("request")
        user = getattr(request, "user", None)
        owner_id = metadata.get("user_id")

        if owner_id is not None:
            if not user or not user.is_authenticated or user.id != owner_id:
                return []

        return notes_used

    def get_notes_used_count(self, obj):
        metadata = obj.metadata or {}
        if not isinstance(metadata, dict):
            return 0
        count = metadata.get("notes_used_count", 0)
        if not count:
            return 0

        # Privacy check: only expose count if requesting user matches author user_id
        request = self.context.get("request")
        user = getattr(request, "user", None)
        owner_id = metadata.get("user_id")

        if owner_id is not None:
            if not user or not user.is_authenticated or user.id != owner_id:
                return 0

        return count

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.role == ResearchMessage.ROLE_USER:
            if not ret.get("evidence"):
                ret.pop("evidence", None)
            ret.pop("notes_used", None)
            ret.pop("notes_used_count", None)
        return ret


class ResearchSessionListSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    papers = serializers.SerializerMethodField()

    class Meta:
        model = ResearchSession
        fields = ("id", "project_id", "title", "papers", "created_at", "updated_at")
        read_only_fields = ("id", "project_id", "created_at", "updated_at")

    def get_papers(self, obj):
        paper_dict = {p.id: p for p in obj.papers.all()}
        evidence_papers = Paper.objects.filter(research_evidence__message__session=obj).distinct()
        for p in evidence_papers:
            if p.id not in paper_dict:
                paper_dict[p.id] = p
        return [{"id": p.id, "title": p.title} for p in sorted(paper_dict.values(), key=lambda x: x.id)]


class ResearchSessionDetailSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    papers = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()

    class Meta:
        model = ResearchSession
        fields = ("id", "project_id", "title", "papers", "messages", "created_at", "updated_at")
        read_only_fields = ("id", "project_id", "created_at", "updated_at")

    def get_papers(self, obj):
        paper_dict = {p.id: p for p in obj.papers.all()}
        evidence_papers = Paper.objects.filter(research_evidence__message__session=obj).distinct()
        for p in evidence_papers:
            if p.id not in paper_dict:
                paper_dict[p.id] = p
        return [{"id": p.id, "title": p.title} for p in sorted(paper_dict.values(), key=lambda x: x.id)]

    def get_messages(self, obj):
        messages_qs = obj.messages.all()
        serializer = ResearchMessageSerializer(messages_qs, many=True, context=self.context)
        return serializer.data
