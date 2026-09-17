import fitz
import unicodedata

from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from projects.models import Project

from .models import Paper
from .serializers import PaperSerializer

from ai.services import (
    semantic_search,
    generate_ai_answer,
    create_paper_chunks,
)


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
    query = request.GET.get("q", "").strip()

    if not query:
        return Response(
            {"detail": "A search query is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    paper = get_object_or_404(
        Paper,
        pk=paper_id,
        project_id=project_id,
        project__owner=request.user,
    )

    search_results = semantic_search(
        query,
        paper=paper,
        top_k=5,
    )

    try:
        answer = generate_ai_answer(
            query,
            search_results,
        )

    except Exception as error:
        return Response(
            {
                "detail": "AI answer generation failed.",
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "query": query,
            "answer": answer,
        },
        status=status.HTTP_200_OK,
    )