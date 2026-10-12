"""
Tool: search_my_notes

Searches strictly the authenticated user's personal notebook notes.
Guarantees cross-user privacy isolation: never reveals notes belonging to other users.
"""

from typing import Any, Dict, Optional
from mcp.server.mcpserver import Context

from papers.models import Paper, PaperNote
from projects.permissions import can_view_project, get_projects_for_user
from ai.services import retrieve_relevant_user_notes
from mcp_server.auth import require_authenticated_user, MCPAuthError


def search_my_notes_handler(
    query: str,
    paper_id: Optional[int] = None,
    limit: int = 5,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Search personal notebook notes belonging exclusively to the authenticated user.

    Args:
        query: Search keywords or question text to match in notes.
        paper_id: Optional paper ID filter.
        limit: Maximum number of notes to retrieve (1 to 10, default 5).
        ctx: MCP Context containing authenticated request headers.
    """
    try:
        user = require_authenticated_user(ctx)
    except MCPAuthError as auth_err:
        return {"status": "error", "error": str(auth_err), "code": "UNAUTHORIZED"}

    query_str = str(query or "").strip()
    if not query_str:
        return {
            "status": "error",
            "error": "query must be a non-empty string.",
            "code": "BAD_REQUEST",
        }

    clamped_limit = max(1, min(10, int(limit or 5)))

    if paper_id is not None:
        try:
            pid = int(paper_id)
            if pid <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return {
                "status": "error",
                "error": "paper_id must be a positive integer.",
                "code": "BAD_REQUEST",
            }

        try:
            paper = Paper.objects.select_related("project").get(id=pid)
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

        target_papers = [paper]
    else:
        user_projects = get_projects_for_user(user)
        target_papers = list(Paper.objects.filter(project__in=user_projects))

    if not target_papers:
        return {
            "status": "success",
            "total_found": 0,
            "notes": [],
        }

    # Call existing privacy-hardened retrieval logic
    notes = retrieve_relevant_user_notes(
        user=user,
        papers=target_papers,
        question=query_str,
        max_notes=clamped_limit,
    )

    return {
        "status": "success",
        "total_found": len(notes),
        "notes": notes,
    }
