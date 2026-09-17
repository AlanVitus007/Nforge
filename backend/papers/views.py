import fitz
import unicodedata

from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from projects.models import Project
from .models import Paper
from .serializers import PaperSerializer

from ai.services import semantic_search


def get_project_for_user(project_id, user):
    """
    Return the project only if it belongs to the requesting user.
    """
    return get_object_or_404(
        Project,
        pk=project_id,
        owner=user,
    )


def clean_extracted_text(text):
    """
    Remove unwanted characters extracted from PDF files.
    Preserve normal text, spaces, newlines, and tabs.
    """

    cleaned = []

    for char in text:
        category = unicodedata.category(char)

        # Remove common square/replacement characters
        if char in {
            "□",
            "�",
            "\uf0a7",
            "\uf0b7",
            "\uf0d8",
        }:
            continue

        # Remove private-use, surrogate, and formatting characters
        if category in {"Co", "Cs", "Cf"}:
            continue

        # Remove control characters except newline and tab
        if category == "Cc" and char not in {"\n", "\t"}:
            continue

        cleaned.append(char)

    return "".join(cleaned)


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

        paper = serializer.save(project=project)

        try:
            document = fitz.open(paper.file.path)

            extracted_text = ""

            for page in document:
                extracted_text += page.get_text()

            document.close()

            # Clean unwanted characters from extracted PDF text
            extracted_text = clean_extracted_text(extracted_text)

            paper.extracted_text = extracted_text
            paper.save(update_fields=["extracted_text"])

            # Generate chunks and embeddings
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
    """
    Search for relevant sections inside a specific paper.
    """

    query = request.query_params.get("q", "").strip()

    if not query:
        return Response(
            {
                "error": "A search query is required."
            },
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
        top_k=3,
    )

    response_data = []

    for result in results:
        response_data.append(
            {
                "text": result["chunk"].text,
                "similarity": result["similarity"],
                "chunk_index": result["chunk"].chunk_index,
            }
        )

    return Response(
        {
            "query": query,
            "results": response_data,
        }
    )