from rest_framework import serializers
from papers.models import Paper
from .models import ResearchSession, ResearchMessage, ResearchEvidence


class ResearchEvidenceSerializer(serializers.ModelSerializer):
    paper_id = serializers.IntegerField(source="paper.id", read_only=True)
    paper_title = serializers.CharField(source="paper.title", read_only=True)
    chunk_id = serializers.SerializerMethodField()

    class Meta:
        model = ResearchEvidence
        fields = ("id", "paper_id", "paper_title", "chunk_id", "page_number", "text")

    def get_chunk_id(self, obj):
        return obj.chunk_id


class ResearchMessageSerializer(serializers.ModelSerializer):
    evidence = ResearchEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchMessage
        fields = ("id", "role", "content", "created_at", "evidence")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.role == ResearchMessage.ROLE_USER and not ret.get("evidence"):
            ret.pop("evidence", None)
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
    messages = ResearchMessageSerializer(many=True, read_only=True)

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
