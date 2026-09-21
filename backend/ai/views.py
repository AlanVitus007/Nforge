from django.shortcuts import render
from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from papers.models import Paper
from .models import PaperChunk, ResearchSession, ResearchMessage, ResearchEvidence
from .services import (
    semantic_search,
    generate_ai_answer,
    generate_paper_summary,
    generate_research_gaps,
    retrieve_multi_paper_evidence,
    generate_multi_paper_synthesis,
    RateLimitError,
)




def handle_ai_exception(e):
    """
    Centralized error handling for AI endpoints.
    Returns structured JSON with appropriate HTTP status code.
    """
    err_msg = str(e)
    if isinstance(e, RateLimitError) or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
        return Response({
            "error": "Gemini API rate limit exceeded. Please try again later.",
            "code": "RATE_LIMITED"
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    if "503" in err_msg or "UNAVAILABLE" in err_msg:
        return Response({
            "error": "Gemini is temporarily unavailable. Please try again shortly.",
            "code": "SERVICE_UNAVAILABLE"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if isinstance(e, ValueError):
        return Response({
            "error": err_msg,
            "code": "BAD_REQUEST"
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "error": "Something went wrong while processing the request.",
        "code": "INTERNAL_SERVER_ERROR"
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def health(request):
    return Response({
        "status": "healthy",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask_ai(request):
    try:
        paper_id = request.data.get("paper_id")
        question = request.data.get("question")
        session_id = request.data.get("session_id")

        if not paper_id or not question:
            return Response({
                "error": "paper_id and question are required",
                "code": "BAD_REQUEST"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            paper = Paper.objects.get(id=paper_id)
        except Paper.DoesNotExist:
            return Response({
                "error": "Paper not found",
                "code": "NOT_FOUND"
            }, status=status.HTTP_404_NOT_FOUND)

        session = None
        if session_id is not None:
            try:
                session = ResearchSession.objects.get(id=session_id)
            except ResearchSession.DoesNotExist:
                return Response({
                    "error": "Research session not found.",
                    "code": "NOT_FOUND"
                }, status=status.HTTP_404_NOT_FOUND)

            if session.project.owner != request.user:
                return Response({
                    "error": "Access denied.",
                    "code": "FORBIDDEN"
                }, status=status.HTTP_403_FORBIDDEN)

            if paper.project != session.project:
                return Response({
                    "error": "Paper does not belong to this research session.",
                    "code": "BAD_REQUEST"
                }, status=status.HTTP_400_BAD_REQUEST)

        if session:
            with transaction.atomic():
                user_msg = ResearchMessage.objects.create(
                    session=session,
                    role=ResearchMessage.ROLE_USER,
                    content=question,
                )

                search_results = semantic_search(question, paper, top_k=5)
                ai_response = generate_ai_answer(question, search_results)

                assistant_msg = ResearchMessage.objects.create(
                    session=session,
                    role=ResearchMessage.ROLE_ASSISTANT,
                    content=ai_response["answer"],
                )

                for source in ai_response.get("sources", []):
                    chunk_obj = None
                    cid = source.get("chunk_id")
                    if cid:
                        chunk_obj = PaperChunk.objects.filter(id=cid).first()

                    ResearchEvidence.objects.create(
                        message=assistant_msg,
                        paper=paper,
                        chunk=chunk_obj,
                        page_number=source.get("page_number"),
                        text=source.get("text") or "",
                    )

                session.save()
                ai_response["session_id"] = session.id
                return Response(ai_response, status=status.HTTP_200_OK)
        else:
            search_results = semantic_search(question, paper, top_k=5)
            ai_response = generate_ai_answer(question, search_results)
            return Response(ai_response, status=status.HTTP_200_OK)

    except Exception as e:
        return handle_ai_exception(e)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_summary_view(request):
    try:
        paper_id = request.data.get("paper_id")

        if not paper_id:
            return Response({
                "error": "paper_id is required",
                "code": "BAD_REQUEST"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            paper = Paper.objects.get(id=paper_id, project__owner=request.user)
        except Paper.DoesNotExist:
            return Response({
                "error": "Paper not found or access denied.",
                "code": "NOT_FOUND"
            }, status=status.HTTP_404_NOT_FOUND)

        summary_response = generate_paper_summary(paper)
        return Response(summary_response, status=status.HTTP_200_OK)

    except Exception as e:
        return handle_ai_exception(e)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_research_gaps_view(request):
    try:
        paper_id = request.data.get("paper_id")

        if not paper_id:
            return Response({
                "error": "paper_id is required",
                "code": "BAD_REQUEST"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            paper = Paper.objects.get(id=paper_id, project__owner=request.user)
        except Paper.DoesNotExist:
            return Response({
                "error": "Paper not found or access denied.",
                "code": "NOT_FOUND"
            }, status=status.HTTP_404_NOT_FOUND)

        gaps_response = generate_research_gaps(paper)
        return Response(gaps_response, status=status.HTTP_200_OK)

    except Exception as e:
        return handle_ai_exception(e)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def compare_papers_view(request):
    try:
        paper_ids = request.data.get("paper_ids")
        question = request.data.get("question")

        # 1. Validate paper_ids existence & type
        if paper_ids is None or not isinstance(paper_ids, list):
            return Response({
                "error": "paper_ids must be a list.",
                "code": "BAD_REQUEST"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. Validate paper count (min 2, max 4)
        if len(paper_ids) < 2 or len(paper_ids) > 4:
            return Response({
                "error": "Multi-paper comparison requires between 2 and 4 papers.",
                "code": "BAD_REQUEST"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. Validate paper_ids integers & duplicates
        for pid in paper_ids:
            if not isinstance(pid, int) or isinstance(pid, bool):
                return Response({
                    "error": "All paper_ids must be integers.",
                    "code": "BAD_REQUEST"
                }, status=status.HTTP_400_BAD_REQUEST)

        if len(paper_ids) != len(set(paper_ids)):
            return Response({
                "error": "Duplicate paper IDs are not allowed.",
                "code": "BAD_REQUEST"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 4. Verify paper existence & user access while preserving requested order
        ordered_papers = []
        for pid in paper_ids:
            try:
                paper = Paper.objects.get(id=pid)
            except Paper.DoesNotExist:
                return Response({
                    "error": "One or more requested papers were not found.",
                    "code": "NOT_FOUND"
                }, status=status.HTTP_404_NOT_FOUND)

            if paper.project.owner != request.user:
                return Response({
                    "error": "Access denied for one or more requested papers.",
                    "code": "FORBIDDEN"
                }, status=status.HTTP_403_FORBIDDEN)

            ordered_papers.append(paper)

        # 5. Default query fallback if question is empty/missing (0 Gemini calls!)
        query_text = (
            question.strip()
            if (question and isinstance(question, str) and question.strip())
            else "main findings methodology limitations research gaps"
        )

        # 6. Perform cross-paper synthesis with single Gemini call and DB-validated evidence
        comparison_response = generate_multi_paper_synthesis(
            question=query_text,
            papers=ordered_papers,
        )

        return Response(comparison_response, status=status.HTTP_200_OK)

    except Exception as e:
        return handle_ai_exception(e)



