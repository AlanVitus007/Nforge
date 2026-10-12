"""
Tool: compare_papers

Retrieves and organizes relevant evidence across 2 to 4 authorized papers for comparison.
"""

from typing import Any, Dict, List
from mcp.server.mcpserver import Context

from papers.models import Paper
from projects.permissions import can_view_project
from ai.services import retrieve_multi_paper_evidence
from mcp_server.auth import require_authenticated_user, MCPAuthError


def compare_papers_handler(
    paper_ids: List[int],
    query: str,
    top_k_per_paper: int = 3,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Retrieve and organize evidence chunks across 2 to 4 authorized papers for comparison.

    Args:
        paper_ids: List of 2 to 4 distinct paper IDs to compare.
        query: The comparison topic or question.
        top_k_per_paper: Chunks per paper (1 to 5, default 3).
        ctx: MCP Context containing authenticated request headers.
    """
    try:
        user = require_authenticated_user(ctx)
    except MCPAuthError as auth_err:
        return {"status": "error", "error": str(auth_err), "code": "UNAUTHORIZED"}

    if not isinstance(paper_ids, list):
        return {
            "status": "error",
            "error": "paper_ids must be a list of integers.",
            "code": "BAD_REQUEST",
        }

    if len(paper_ids) < 2 or len(paper_ids) > 4:
        return {
            "status": "error",
            "error": "Multi-paper comparison requires between 2 and 4 papers.",
            "code": "BAD_REQUEST",
        }

    # Validate integers and duplicates
    seen_ids = set()
    cleaned_ids = []
    for pid in paper_ids:
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            return {
                "status": "error",
                "error": "All paper_ids must be positive integers.",
                "code": "BAD_REQUEST",
            }
        if pid in seen_ids:
            return {
                "status": "error",
                "error": "Duplicate paper IDs are not allowed.",
                "code": "BAD_REQUEST",
            }
        seen_ids.add(pid)
        cleaned_ids.append(pid)

    query_str = str(query or "").strip()
    if not query_str:
        return {
            "status": "error",
            "error": "query must be a non-empty string.",
            "code": "BAD_REQUEST",
        }

    clamped_top_k = max(1, min(5, int(top_k_per_paper or 3)))

    # Fetch and verify permissions for each paper in order
    ordered_papers = []
    for pid in cleaned_ids:
        try:
            p = Paper.objects.select_related("project").get(id=pid)
        except Paper.DoesNotExist:
            return {
                "status": "error",
                "error": f"Paper id {pid} not found.",
                "code": "NOT_FOUND",
            }

        if not can_view_project(user, p.project):
            return {
                "status": "error",
                "error": f"Access denied for paper id {pid}.",
                "code": "FORBIDDEN",
            }
        ordered_papers.append(p)

    try:
        grouped_results = retrieve_multi_paper_evidence(
            question=query_str,
            papers=ordered_papers,
            top_k_per_paper=clamped_top_k,
        )
    except Exception as err:
        return {
            "status": "error",
            "error": f"Evidence retrieval failed: {err}",
            "code": "RETRIEVAL_FAILED",
        }

    return {
        "status": "success",
        "query": query_str,
        "total_papers": len(ordered_papers),
        "comparisons": grouped_results,
    }
