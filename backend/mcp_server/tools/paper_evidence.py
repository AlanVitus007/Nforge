"""
Tool: search_paper_evidence

Retrieves relevant textual excerpts and evidence from an authorized research paper
using semantic embeddings. Returns grounded chunk texts, page numbers, chunk IDs,
and similarity scores.
"""

from typing import Any, Dict
from mcp.server.mcpserver import Context

from papers.models import Paper
from projects.permissions import can_view_project
from ai.services import semantic_search
from mcp_server.auth import require_authenticated_user, MCPAuthError


def search_paper_evidence_handler(
    paper_id: int,
    query: str,
    top_k: int = 5,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Search for relevant evidence chunks from an authorized research paper.

    Args:
        paper_id: The ID of the research paper to search.
        query: The semantic search query or question text.
        top_k: Maximum number of relevant chunks to retrieve (1 to 10, default 5).
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

    query_str = str(query or "").strip()
    if not query_str:
        return {
            "status": "error",
            "error": "query must be a non-empty string.",
            "code": "BAD_REQUEST",
        }

    clamped_top_k = max(1, min(10, int(top_k or 5)))

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

    try:
        raw_results = semantic_search(query_str, paper, top_k=clamped_top_k)
    except Exception as err:
        return {
            "status": "error",
            "error": f"Semantic search failed: {err}",
            "code": "SEARCH_FAILED",
        }

    sources = []
    for r in raw_results:
        chunk = r.get("chunk")
        if not chunk:
            continue
        sources.append({
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "text": chunk.text,
            "similarity": round(float(r.get("similarity", 0.0)), 4),
            "paper_id": paper.id,
            "paper_title": paper.title,
        })

    return {
        "status": "success",
        "paper_id": paper.id,
        "paper_title": paper.title,
        "total_found": len(sources),
        "sources": sources,
    }
