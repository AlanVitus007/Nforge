import json
from django.shortcuts import render
from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from projects.models import Project
from papers.models import Paper
from .models import PaperChunk, ResearchSession, ResearchMessage, ResearchEvidence
from .serializers import (
    ResearchSessionListSerializer,
    ResearchSessionDetailSerializer,
)
from .services import (
    semantic_search,
    generate_ai_answer,
    generate_paper_summary,
    generate_research_gaps,
    retrieve_multi_paper_evidence,
    generate_multi_paper_synthesis,
    generate_research_gap_analysis,
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
        session_id = request.data.get("session_id")

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

        # 5. Session validation (optional session_id)
        session = None
        if session_id is not None:
            try:
                session = ResearchSession.objects.get(id=session_id)
            except (ResearchSession.DoesNotExist, ValueError, TypeError):
                return Response({
                    "error": "Research session not found.",
                    "code": "NOT_FOUND"
                }, status=status.HTTP_404_NOT_FOUND)

            if session.project.owner != request.user:
                return Response({
                    "error": "Access denied.",
                    "code": "FORBIDDEN"
                }, status=status.HTTP_403_FORBIDDEN)

            for paper in ordered_papers:
                if paper.project != session.project:
                    return Response({
                        "error": "One or more papers do not belong to this research session.",
                        "code": "BAD_REQUEST"
                    }, status=status.HTTP_400_BAD_REQUEST)

        # 6. Default query fallback if question is empty/missing (0 Gemini calls!)
        query_text = (
            question.strip()
            if (question and isinstance(question, str) and question.strip())
            else "main findings methodology limitations research gaps"
        )

        # 7. Perform cross-paper synthesis and persist to ResearchSession if provided
        if session:
            with transaction.atomic():
                user_msg = ResearchMessage.objects.create(
                    session=session,
                    role=ResearchMessage.ROLE_USER,
                    content=query_text,
                )

                comparison_response = generate_multi_paper_synthesis(
                    question=query_text,
                    papers=ordered_papers,
                )

                assistant_msg = ResearchMessage.objects.create(
                    session=session,
                    role=ResearchMessage.ROLE_ASSISTANT,
                    content=json.dumps(comparison_response.get("comparison", {})),
                )

                # Collect all validated sources without duplication
                comparison_data = comparison_response.get("comparison", {})
                unique_sources = []
                seen_keys = set()
                sections = [
                    comparison_data.get("similarities", []),
                    comparison_data.get("differences", []),
                    comparison_data.get("methodology_comparison", []),
                    comparison_data.get("findings_comparison", []),
                    comparison_data.get("research_gaps", []),
                ]

                for section in sections:
                    if isinstance(section, list):
                        for item in section:
                            if isinstance(item, dict):
                                for src in item.get("sources", []):
                                    if isinstance(src, dict):
                                        cid = src.get("chunk_id")
                                        pid = src.get("paper_id")
                                        dedup_key = (pid, cid) if cid is not None else (pid, src.get("page_number"), src.get("text"))
                                        if dedup_key not in seen_keys:
                                            seen_keys.add(dedup_key)
                                            unique_sources.append(src)

                paper_map = {p.id: p for p in ordered_papers}
                chunk_ids = [s.get("chunk_id") for s in unique_sources if s.get("chunk_id")]
                chunks_by_id = {c.id: c for c in PaperChunk.objects.filter(id__in=chunk_ids)} if chunk_ids else {}

                for src in unique_sources:
                    paper_id = src.get("paper_id")
                    paper_obj = paper_map.get(paper_id)
                    if not paper_obj and paper_id:
                        paper_obj = Paper.objects.filter(id=paper_id).first()
                    if not paper_obj:
                        continue

                    chunk_obj = chunks_by_id.get(src.get("chunk_id"))

                    ResearchEvidence.objects.create(
                        message=assistant_msg,
                        paper=paper_obj,
                        chunk=chunk_obj,
                        page_number=src.get("page_number"),
                        text=src.get("text") or "",
                    )

                session.save()
                comparison_response["session_id"] = session.id
                return Response(comparison_response, status=status.HTTP_200_OK)
        else:
            comparison_response = generate_multi_paper_synthesis(
                question=query_text,
                papers=ordered_papers,
            )
            return Response(comparison_response, status=status.HTTP_200_OK)

    except Exception as e:
        return handle_ai_exception(e)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def research_gap_analysis_view(request):
    """
    POST /api/ai/gap-analysis/
    Performs multi-paper research gap analysis over 2-4 selected papers.
    Validates paper existence, project ownership, optional session project alignment,
    and invokes generate_research_gap_analysis().
    Does not persist messages to ResearchSession in this phase (deferred to Phase 7.1.3).
    """
    try:
        paper_ids = request.data.get("paper_ids")
        question = request.data.get("question")
        session_id = request.data.get("session_id")

        # 1. Validate paper_ids existence & type
        if paper_ids is None or not isinstance(paper_ids, list):
            return Response({
                "error": "paper_ids must be a list.",
                "code": "BAD_REQUEST"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. Validate paper count (min 2, max 4)
        if len(paper_ids) < 2 or len(paper_ids) > 4:
            return Response({
                "error": "Research gap analysis requires between 2 and 4 papers.",
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

        # 5. Session validation (optional session_id)
        session = None
        if session_id is not None:
            try:
                session = ResearchSession.objects.get(id=session_id)
            except (ResearchSession.DoesNotExist, ValueError, TypeError):
                return Response({
                    "error": "Research session not found.",
                    "code": "NOT_FOUND"
                }, status=status.HTTP_404_NOT_FOUND)

            if session.project.owner != request.user:
                return Response({
                    "error": "Access denied.",
                    "code": "FORBIDDEN"
                }, status=status.HTTP_403_FORBIDDEN)

            for paper in ordered_papers:
                if paper.project != session.project:
                    return Response({
                        "error": "One or more papers do not belong to this research session.",
                        "code": "BAD_REQUEST"
                    }, status=status.HTTP_400_BAD_REQUEST)

        # 6. Default question fallback if question is empty/missing
        DEFAULT_GAP_QUESTION = (
            "Identify the major research gaps, limitations, unanswered questions, "
            "and future research directions across these papers."
        )
        effective_question = (
            question.strip()
            if (question and isinstance(question, str) and question.strip())
            else DEFAULT_GAP_QUESTION
        )

        # 7. Execute single-call Research Gap Analysis service and persist if session provided
        if session:
            with transaction.atomic():
                user_msg = ResearchMessage.objects.create(
                    session=session,
                    role=ResearchMessage.ROLE_USER,
                    content=effective_question,
                )

                gap_response = generate_research_gap_analysis(
                    question=effective_question,
                    papers=ordered_papers,
                )

                assistant_msg = ResearchMessage.objects.create(
                    session=session,
                    role=ResearchMessage.ROLE_ASSISTANT,
                    content=json.dumps(gap_response.get("gap_analysis", {})),
                )

                # Collect all validated sources across all 7 categories without duplication
                gap_data = gap_response.get("gap_analysis", {})
                unique_sources = []
                seen_keys = set()
                sections = [
                    gap_data.get("common_limitations", []),
                    gap_data.get("methodological_gaps", []),
                    gap_data.get("dataset_population_gaps", []),
                    gap_data.get("understudied_areas", []),
                    gap_data.get("contradictions_inconsistencies", []),
                    gap_data.get("unanswered_research_questions", []),
                    gap_data.get("future_research_directions", []),
                ]

                for section in sections:
                    if isinstance(section, list):
                        for item in section:
                            if isinstance(item, dict):
                                for src in item.get("sources", []):
                                    if isinstance(src, dict):
                                        cid = src.get("chunk_id")
                                        pid = src.get("paper_id")
                                        dedup_key = (pid, cid) if cid is not None else (pid, src.get("page_number"), src.get("text"))
                                        if dedup_key not in seen_keys:
                                            seen_keys.add(dedup_key)
                                            unique_sources.append(src)

                paper_map = {p.id: p for p in ordered_papers}
                chunk_ids = [s.get("chunk_id") for s in unique_sources if s.get("chunk_id")]
                chunks_by_id = {c.id: c for c in PaperChunk.objects.filter(id__in=chunk_ids)} if chunk_ids else {}

                for src in unique_sources:
                    paper_id = src.get("paper_id")
                    paper_obj = paper_map.get(paper_id)
                    if not paper_obj and paper_id:
                        paper_obj = Paper.objects.filter(id=paper_id).first()
                    if not paper_obj:
                        continue

                    chunk_obj = chunks_by_id.get(src.get("chunk_id"))

                    ResearchEvidence.objects.create(
                        message=assistant_msg,
                        paper=paper_obj,
                        chunk=chunk_obj,
                        page_number=src.get("page_number"),
                        text=src.get("text") or "",
                    )

                session.save()
                gap_response["session_id"] = session.id
                return Response(gap_response, status=status.HTTP_200_OK)
        else:
            gap_response = generate_research_gap_analysis(
                question=effective_question,
                papers=ordered_papers,
            )
            return Response(gap_response, status=status.HTTP_200_OK)

    except Exception as e:
        return handle_ai_exception(e)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def session_list_create_view(request):
    try:
        if request.method == "POST":
            project_id = request.data.get("project_id")
            if project_id is None:
                return Response({
                    "error": "project_id is required.",
                    "code": "BAD_REQUEST"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                project = Project.objects.get(id=project_id)
            except (Project.DoesNotExist, ValueError, TypeError):
                return Response({
                    "error": "Project not found.",
                    "code": "NOT_FOUND"
                }, status=status.HTTP_404_NOT_FOUND)

            if project.owner != request.user:
                return Response({
                    "error": "Access denied.",
                    "code": "FORBIDDEN"
                }, status=status.HTTP_403_FORBIDDEN)

            title = request.data.get("title")
            if title is None or (isinstance(title, str) and not title.strip()):
                title = "Research Session"
            elif isinstance(title, str):
                title = title.strip()

            session = ResearchSession.objects.create(
                project=project,
                title=title,
            )

            serializer = ResearchSessionListSerializer(session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "GET":
            project_id = request.query_params.get("project_id")
            if not project_id:
                return Response({
                    "error": "project_id query parameter is required.",
                    "code": "BAD_REQUEST"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                project = Project.objects.get(id=project_id)
            except (Project.DoesNotExist, ValueError, TypeError):
                return Response({
                    "error": "Project not found.",
                    "code": "NOT_FOUND"
                }, status=status.HTTP_404_NOT_FOUND)

            if project.owner != request.user:
                return Response({
                    "error": "Access denied.",
                    "code": "FORBIDDEN"
                }, status=status.HTTP_403_FORBIDDEN)

            sessions = ResearchSession.objects.filter(project=project).order_by("-updated_at")
            serializer = ResearchSessionListSerializer(sessions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return handle_ai_exception(e)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def session_detail_view(request, session_id):
    try:
        try:
            session = ResearchSession.objects.select_related("project__owner").prefetch_related(
                "papers",
                "messages__evidence__paper",
                "messages__evidence__chunk"
            ).get(id=session_id)
        except (ResearchSession.DoesNotExist, ValueError, TypeError):
            return Response({
                "error": "Research session not found.",
                "code": "NOT_FOUND"
            }, status=status.HTTP_404_NOT_FOUND)

        if session.project.owner != request.user:
            return Response({
                "error": "Access denied.",
                "code": "FORBIDDEN"
            }, status=status.HTTP_403_FORBIDDEN)

        if request.method == "GET":
            serializer = ResearchSessionDetailSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "PATCH":
            title = request.data.get("title")
            if title is not None:
                if not isinstance(title, str) or not title.strip():
                    return Response({
                        "error": "Title cannot be empty.",
                        "code": "BAD_REQUEST"
                    }, status=status.HTTP_400_BAD_REQUEST)
                session.title = title.strip()
                session.save(update_fields=["title", "updated_at"])

            if "papers" in request.data:
                paper_ids = request.data.get("papers")
                if not isinstance(paper_ids, list):
                    return Response({
                        "error": "papers must be a list of paper IDs.",
                        "code": "BAD_REQUEST"
                    }, status=status.HTTP_400_BAD_REQUEST)

                valid_ids = []
                for pid in paper_ids:
                    try:
                        valid_ids.append(int(pid))
                    except (ValueError, TypeError):
                        return Response({
                            "error": "All paper IDs must be integers.",
                            "code": "BAD_REQUEST"
                        }, status=status.HTTP_400_BAD_REQUEST)

                project_papers = list(Paper.objects.filter(id__in=valid_ids, project=session.project))
                if len(project_papers) != len(set(valid_ids)):
                    return Response({
                        "error": "One or more paper IDs are invalid or do not belong to this project.",
                        "code": "BAD_REQUEST"
                    }, status=status.HTTP_400_BAD_REQUEST)

                session.papers.set(project_papers)
                session.save()

            # Refresh session to ensure prefetch caches reflect updated papers
            session = ResearchSession.objects.select_related("project__owner").prefetch_related(
                "papers",
                "messages__evidence__paper",
                "messages__evidence__chunk"
            ).get(id=session.id)

            serializer = ResearchSessionDetailSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "DELETE":
            session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        return handle_ai_exception(e)




