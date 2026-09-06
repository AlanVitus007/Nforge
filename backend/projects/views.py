from rest_framework import generics, permissions
from .models import Project
from .serializers import ProjectSerializer


class ProjectListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/   — list all projects owned by the authenticated user.
    POST /api/projects/   — create a new project owned by the authenticated user.
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/projects/<id>/  — retrieve a single project.
    PUT    /api/projects/<id>/  — full update.
    PATCH  /api/projects/<id>/  — partial update.
    DELETE /api/projects/<id>/  — delete.
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only access their own projects
        return Project.objects.filter(owner=self.request.user)
