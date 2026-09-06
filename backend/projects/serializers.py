from rest_framework import serializers
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    # owner is read-only; set from request.user in the view
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Project
        fields = ('id', 'owner', 'title', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')
