from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from papers.models import Paper
from .services import (
    semantic_search,
    generate_ai_answer,
)


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
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            paper = Paper.objects.get(id=paper_id)
        except Paper.DoesNotExist:
            return Response({
                "error": "Paper not found",
            }, status=status.HTTP_404_NOT_FOUND)

        search_results = semantic_search(question, paper, top_k=5)

        ai_response = generate_ai_answer(question, search_results)

        return Response(ai_response)

    except Exception as e:
        return Response({
            "error": str(e),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
