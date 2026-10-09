import pymupdf as fitz
import unicodedata

from django.http import Http404
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from projects.models import Project
from projects.permissions import can_view_project, can_edit_project_content

from .models import Paper, PaperNote
from .serializers import PaperSerializer, PaperNoteSerializer

from ai.services import (
    semantic_search,
    generate_ai_answer,
    create_paper_chunks,
)


def get_project_for_user(project_id, user, require_edit=False):
    """
    Return the project only if the user has appropriate access.
    - If require_edit is True, user must be OWNER or EDITOR.
    - If require_edit is False, user can be OWNER, EDITOR, or VIEWER.
    - If user has no view access to project, raise Http404.
    - If user has view access but lacks edit permissions, raise PermissionDenied.
    """
    project = get_object_or_404(Project, pk=project_id)
    if not can_view_project(user, project):
        raise Http404("Project not found.")
    if require_edit and not can_edit_project_content(user, project):
        raise PermissionDenied("You do not have permission to modify papers in this project.")
    return project


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


import re


def clean_block_text(text):
    """
    Clean text within a block:
    - remove unwanted control/private characters using clean_extracted_text()
    - join hyphenated word breaks at line ends (e.g. 'oper-\\nating' -> 'operating')
    - convert single newlines inside paragraph to space
    - return list of clean paragraph strings
    """
    raw_clean = clean_extracted_text(text)
    if not raw_clean or not raw_clean.strip():
        return []

    # Split block into paragraphs by double newlines if present
    raw_paras = [p for p in re.split(r'\n\s*\n', raw_clean) if p.strip()]
    cleaned_paras = []

    for para in raw_paras:
        # Join hyphenated words across line wraps
        para = re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', para)
        # Convert single newlines inside paragraph to space
        para = re.sub(r'(?<!\n)\n(?!\n)', ' ', para)
        # Normalize multiple spaces
        para = re.sub(r'[ \t]+', ' ', para).strip()
        if para:
            cleaned_paras.append(para)

    return cleaned_paras


def extract_page_texts(pdf_path):
    """
    Open a PDF and return:
      - page_structures: list of (page_number, list_of_paragraphs) tuples (1-based page numbers)
      - full_text:  all pages concatenated (for Paper.extracted_text storage)
    """
    document = fitz.open(pdf_path)

    page_structures = []
    full_text_parts = []

    for page_index, page in enumerate(document):
        page_number = page_index + 1  # 1-based for users
        # get_text("blocks", sort=True) extracts layout blocks in reading order
        blocks = page.get_text("blocks", sort=True)
        page_paras = []

        for b in blocks:
            # b: (x0, y0, x1, y1, text, block_no, block_type)
            # block_type == 0 is text
            if len(b) >= 7 and b[6] == 0:
                block_text = b[4]
                paras = clean_block_text(block_text)
                page_paras.extend(paras)

        page_structures.append((page_number, page_paras))
        if page_paras:
            full_text_parts.append("\n\n".join(page_paras))

    document.close()

    full_text = "\n\n".join(full_text_parts)
    return page_structures, full_text


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
            require_edit=False,
        )

        return Paper.objects.filter(
            project=project
        ).order_by("-uploaded_at")

    def create(self, request, *args, **kwargs):
        # Ensure user has edit permission before creating/uploading paper
        get_project_for_user(
            self.kwargs["project_id"],
            self.request.user,
            require_edit=True,
        )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        project = get_project_for_user(
            self.kwargs["project_id"],
            self.request.user,
            require_edit=True,
        )

        paper = serializer.save(project=project)

        try:
            page_texts, full_text = extract_page_texts(paper.file.path)

            paper.extracted_text = full_text
            paper.save(update_fields=["extracted_text"])

            # Generate page-aware chunks and embeddings
            create_paper_chunks(paper, page_texts=page_texts)

        except Exception as error:
            print(f"PDF processing failed: {error}")


class PaperDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/projects/<project_id>/papers/<paper_id>/
    PUT    /api/projects/<project_id>/papers/<paper_id>/
    PATCH  /api/projects/<project_id>/papers/<paper_id>/
    DELETE /api/projects/<project_id>/papers/<paper_id>/
    """

    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        require_edit = self.request.method not in permissions.SAFE_METHODS
        project = get_project_for_user(
            self.kwargs["project_id"],
            self.request.user,
            require_edit=require_edit,
        )

        return get_object_or_404(
            Paper,
            pk=self.kwargs["paper_id"],
            project=project,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reprocess_paper(request, project_id, paper_id):
    """
    POST /api/projects/<project_id>/papers/<paper_id>/reprocess/

    Regenerates PaperChunk records from the stored PDF file so that existing
    papers gain page_number metadata without requiring a re-upload.

    The PDF file itself is not modified or deleted.
    """
    project = get_project_for_user(project_id, request.user, require_edit=True)
    paper = get_object_or_404(
        Paper,
        pk=paper_id,
        project=project,
    )

    if not paper.file:
        return Response(
            {"error": "This paper has no associated PDF file."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        page_texts, full_text = extract_page_texts(paper.file.path)

        # Update the stored full text as well (no-op if unchanged)
        paper.extracted_text = full_text
        paper.save(update_fields=["extracted_text"])

        chunks = create_paper_chunks(paper, page_texts=page_texts)

        return Response(
            {
                "status": "ok",
                "chunks_created": len(chunks),
                "pages_processed": len(page_texts),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "error": f"Reprocessing failed: {error}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

    project = get_project_for_user(project_id, request.user, require_edit=False)
    paper = get_object_or_404(
        Paper,
        pk=paper_id,
        project=project,
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


class PaperNoteListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/papers/<paper_id>/notes/
    POST /api/papers/<paper_id>/notes/
    Also supports:
    GET  /api/projects/<project_id>/papers/<paper_id>/notes/
    POST /api/projects/<project_id>/papers/<paper_id>/notes/
    """
    serializer_class = PaperNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_paper(self):
        paper_id = self.kwargs["paper_id"]
        paper = get_object_or_404(Paper, pk=paper_id)
        if not can_view_project(self.request.user, paper.project):
            raise Http404("Paper not found.")
        return paper

    def get_queryset(self):
        paper = self._get_paper()
        return PaperNote.objects.filter(
            paper=paper,
            user=self.request.user
        ).order_by("-updated_at")

    def perform_create(self, serializer):
        paper = self._get_paper()
        serializer.save(
            paper=paper,
            user=self.request.user
        )


class PaperNoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/paper-notes/<note_id>/
    PATCH  /api/paper-notes/<note_id>/
    PUT    /api/paper-notes/<note_id>/
    DELETE /api/paper-notes/<note_id>/
    """
    serializer_class = PaperNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        note_id = self.kwargs.get("note_id") or self.kwargs.get("pk")
        note = get_object_or_404(
            PaperNote,
            pk=note_id,
            user=self.request.user
        )
        if not can_view_project(self.request.user, note.paper.project):
            raise Http404("Note not found.")
        return note