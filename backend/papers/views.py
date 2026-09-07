import fitz

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from projects.models import Project
from .models import Paper
from .serializers import PaperSerializer


def get_project_for_user(project_id, user):
    """Return the Project only if it belongs to the requesting user."""
    return get_object_or_404(Project, pk=project_id, owner=user)


class PaperListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/<project_id>/papers/   — list papers in the project.
    POST /api/projects/<project_id>/papers/   — upload a new paper (multipart/form-data).
    """
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project = get_project_for_user(
            self.kwargs['project_id'],
            self.request.user
        )
        return Paper.objects.filter(
            project=project
        ).order_by('-uploaded_at')

    def perform_create(self, serializer):
        project = get_project_for_user(
            self.kwargs['project_id'],
            self.request.user
        )

        paper = serializer.save(project=project)

        try:
            document = fitz.open(paper.file.path)

            extracted_text = ""

            for page in document:
                extracted_text += page.get_text()

            document.close()

            paper.extracted_text = extracted_text
            paper.save(update_fields=["extracted_text"])

        except Exception as e:
            print(f"PDF text extraction failed: {e}")


class PaperDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/projects/<project_id>/papers/<paper_id>/  — retrieve a paper.
    DELETE /api/projects/<project_id>/papers/<paper_id>/  — delete a paper.
    """
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        project = get_project_for_user(
            self.kwargs['project_id'],
            self.request.user
        )

        return get_object_or_404(
            Paper,
            pk=self.kwargs['paper_id'],
            project=project
        )