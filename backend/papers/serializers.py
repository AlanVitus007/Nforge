from rest_framework import serializers
from .models import Paper


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
