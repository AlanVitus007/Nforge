from rest_framework import serializers
from .models import Paper, PaperNote


class PaperSerializer(serializers.ModelSerializer):
    # project is derived from the URL; never accepted from the client
    project = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Paper
        fields = ('id', 'project', 'title', 'file', 'uploaded_at', 'extracted_text')
        read_only_fields = ('id', 'project', 'uploaded_at')

    def validate_file(self, value):
        """Accept only files whose name ends with .pdf."""
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError(
                "Only PDF files are accepted. Please upload a .pdf file."
            )
        return value


class PaperNoteSerializer(serializers.ModelSerializer):
    paper_id = serializers.IntegerField(source="paper.id", read_only=True)
    paper_title = serializers.CharField(source="paper.title", read_only=True)
    title = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="Untitled note",
        error_messages={
            'max_length': 'Note title cannot exceed 200 characters.'
        }
    )
    content = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )

    class Meta:
        model = PaperNote
        fields = (
            'id',
            'paper_id',
            'paper_title',
            'title',
            'content',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'paper_id', 'paper_title', 'created_at', 'updated_at')

    def validate_title(self, value):
        if value is None:
            return "Untitled note"
        trimmed = value.strip()
        if not trimmed:
            return "Untitled note"
        if len(trimmed) > 200:
            raise serializers.ValidationError("Note title cannot exceed 200 characters.")
        return trimmed

