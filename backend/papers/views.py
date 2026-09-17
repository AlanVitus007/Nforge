import fitz

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from projects.models import Project
from .models import Paper
from .serializers import PaperSerializer

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions

from ai.services import semantic_search


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


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def paper_semantic_search(request, project_id, paper_id):
    query = request.query_params.get("q", "").strip()

    if not query:
        return Response(
            {"error": "A search query is required."},
            status=400,
        )

    project = get_project_for_user(
        project_id,
        request.user,
    )

    paper = get_object_or_404(
        Paper,
        pk=paper_id,
        project=project,
    )

    results = semantic_search(
        query,
        paper=paper,
        top_k=5,
    )

    response_data = []

    for result in results:
        response_data.append({
            "text": result["chunk"].text,
            "similarity": result["similarity"],
            "chunk_index": result["chunk"].chunk_index,
        })

    return Response({
        "query": query,
        "results": response_data,
    })