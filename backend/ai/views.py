from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from papers.models import Paper
from .services import (
    semantic_search,
    generate_ai_answer,
    generate_paper_summary,
    generate_research_gaps,
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


