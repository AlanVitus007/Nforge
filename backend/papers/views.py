import fitz

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from projects.models import Project
from .models import Paper
from .serializers import PaperSerializer


def get_project_for_user(project_id, user):
    """Return the Project only if it belongs to the requesting user."""
    return get_object_or_404(
        Project,
        pk=project_id,
        owner=user,
    )


class PaperListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/<project_id>/papers/
    POST /api/projects/<project_id>/papers/
    """

    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project = get_project_for_user(
            self.kwargs["project_id"],
            self.request.user,
        )

        return Paper.objects.filter(
            project=project
        ).order_by("-uploaded_at")

    def perform_create(self, serializer):
        project = get_project_for_user(
            self.kwargs["project_id"],
            self.request.user,
        )

        # Important: assign the project while saving the paper
        paper = serializer.save(project=project)

        try:
            document = fitz.open(paper.file.path)

            extracted_text = ""

            for page in document:
                extracted_text += page.get_text()

            document.close()

            paper.extracted_text = extracted_text
            paper.save(update_fields=["extracted_text"])

            # Import here to avoid loading the AI model during login/server startup
            from ai.services import create_paper_chunks

            create_paper_chunks(paper)

        except Exception as error:
            print(f"PDF processing failed: {error}")


class PaperDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/projects/<project_id>/papers/<paper_id>/
    DELETE /api/projects/<project_id>/papers/<paper_id>/
    """

    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        project = get_project_for_user(
            self.kwargs["project_id"],
            self.request.user,
        )

        return get_object_or_404(
            Paper,
            pk=self.kwargs["paper_id"],
            project=project,
        )