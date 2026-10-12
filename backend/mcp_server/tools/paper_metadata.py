"""
Tools: search_papers and get_paper_details.

Provides authorized metadata inspection and paper listing for the authenticated user.
"""

from typing import Any, Dict, Optional
from django.db.models import Q
from mcp.server.mcpserver import Context

from papers.models import Paper
from ai.models import PaperChunk
from projects.permissions import can_view_project, get_projects_for_user
from mcp_server.auth import require_authenticated_user, MCPAuthError


def search_papers_handler(
    query: str = "",
    project_id: Optional[int] = None,
    limit: int = 10,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Search and list papers accessible to the authenticated user.

    Args:
        query: Optional title search filter.
        project_id: Optional project ID filter.
        limit: Maximum papers to return (1 to 25, default 10).
        ctx: MCP Context containing authenticated request headers.
    """
    try:
        user = require_authenticated_user(ctx)
    except MCPAuthError as auth_err:
        return {"status": "error", "error": str(auth_err), "code": "UNAUTHORIZED"}

    user_projects = get_projects_for_user(user)

    if project_id is not None:
        try:
            pid = int(project_id)
            if pid <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return {
                "status": "error",
                "error": "project_id must be a positive integer.",
                "code": "BAD_REQUEST",
            }

        target_project = user_projects.filter(id=pid).first()
        if not target_project:
            return {
                "status": "error",
                "error": f"Project id {project_id} not found or access denied.",
                "code": "FORBIDDEN",
            }
        qs = Paper.objects.filter(project=target_project)
    else:
        qs = Paper.objects.filter(project__in=user_projects)

    clean_query = str(query or "").strip()
    if clean_query:
        qs = qs.filter(title__icontains=clean_query)

    clamped_limit = max(1, min(25, int(limit or 10)))
    papers = list(qs.select_related("project").order_by("-uploaded_at")[:clamped_limit])

    results = []
    for p in papers:
        results.append({
            "id": p.id,
            "title": p.title,
            "project_id": p.project_id,
            "project_title": p.project.title,
            "uploaded_at": str(p.uploaded_at) if hasattr(p, "uploaded_at") else None,
        })

    return {
        "status": "success",
        "total_found": len(results),
        "papers": results,
    }


def get_paper_details_handler(
    paper_id: int,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Retrieve permitted metadata and chunk count for a specific paper.

    Args:
        paper_id: The ID of the research paper.
        ctx: MCP Context containing authenticated request headers.
    """
    try:
        user = require_authenticated_user(ctx)
    except MCPAuthError as auth_err:
        return {"status": "error", "error": str(auth_err), "code": "UNAUTHORIZED"}

    if not isinstance(paper_id, int) or paper_id <= 0:
        return {
            "status": "error",
            "error": "paper_id must be a positive integer.",
            "code": "BAD_REQUEST",
        }

    try:
        paper = Paper.objects.select_related("project").get(id=paper_id)
    except Paper.DoesNotExist:
        return {
            "status": "error",
            "error": f"Paper with id {paper_id} not found.",
            "code": "NOT_FOUND",
        }

    if not can_view_project(user, paper.project):
        return {
            "status": "error",
            "error": f"Access denied for paper id {paper_id}.",
            "code": "FORBIDDEN",
        }

    chunk_count = PaperChunk.objects.filter(paper=paper).count()

    return {
        "status": "success",
        "id": paper.id,
        "title": paper.title,
        "project_id": paper.project_id,
        "project_title": paper.project.title,
        "total_chunks": chunk_count,
        "uploaded_at": str(paper.uploaded_at) if hasattr(paper, "uploaded_at") else None,
    }
