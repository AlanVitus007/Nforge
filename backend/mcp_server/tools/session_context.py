"""
Tool: get_research_session_context

Retrieves attached papers and conversation context for an authorized ResearchSession.
"""

from typing import Any, Dict
from mcp.server.mcpserver import Context

from ai.models import ResearchSession, ResearchMessage
from projects.permissions import can_view_project
from mcp_server.auth import require_authenticated_user, MCPAuthError


def get_research_session_context_handler(
    session_id: int,
    message_limit: int = 6,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Retrieve permitted papers and conversation context for an accessible ResearchSession.

    Args:
        session_id: The ID of the ResearchSession.
        message_limit: Maximum number of recent messages to return (1 to 20, default 6).
        ctx: MCP Context containing authenticated request headers.
    """
    try:
        user = require_authenticated_user(ctx)
    except MCPAuthError as auth_err:
        return {"status": "error", "error": str(auth_err), "code": "UNAUTHORIZED"}

    if not isinstance(session_id, int) or session_id <= 0:
        return {
            "status": "error",
            "error": "session_id must be a positive integer.",
            "code": "BAD_REQUEST",
        }

    try:
        session = ResearchSession.objects.select_related("project").get(id=session_id)
    except ResearchSession.DoesNotExist:
        return {
            "status": "error",
            "error": f"Research session with id {session_id} not found.",
            "code": "NOT_FOUND",
        }

    if not can_view_project(user, session.project):
        return {
            "status": "error",
            "error": f"Access denied for session id {session_id}.",
            "code": "FORBIDDEN",
        }

    clamped_limit = max(1, min(20, int(message_limit or 6)))
    papers = list(session.papers.all())

    raw_messages = list(session.messages.order_by("-created_at")[:clamped_limit])
    recent_messages = []
    for m in reversed(raw_messages):
        recent_messages.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": str(m.created_at) if hasattr(m, "created_at") else None,
        })

    return {
        "status": "success",
        "session_id": session.id,
        "session_title": session.title,
        "project_id": session.project_id,
        "project_title": session.project.title,
        "papers": [{"id": p.id, "title": p.title} for p in papers],
        "recent_messages": recent_messages,
    }
