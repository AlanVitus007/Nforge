"""
NForge Dedicated MCP Server.

Exposes application functionality exclusively via the Model Context Protocol.
Runs as a separate process using Starlette/Uvicorn SSE transport.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

# Ensure Django environment is configured
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from mcp.server.mcpserver import MCPServer, Context
from mcp_server.tools.paper_evidence import search_paper_evidence_handler
from mcp_server.tools.paper_metadata import (
    search_papers_handler,
    get_paper_details_handler,
)
from mcp_server.tools.user_notes import search_my_notes_handler
from mcp_server.tools.session_context import get_research_session_context_handler
from mcp_server.tools.paper_comparison import compare_papers_handler


def create_mcp_server() -> MCPServer:
    """Create and configure the MCPServer instance with all registered tools."""
    server = MCPServer("nforge-mcp-server")

    @server.tool(
        name="search_paper_evidence",
        description="Search for relevant textual excerpts and evidence from an authorized research paper using semantic embeddings. Returns grounded chunk texts, page numbers, chunk IDs, and similarity scores.",
    )
    def search_paper_evidence(
        paper_id: int,
        query: str,
        top_k: int = 5,
        ctx: Context = None,
    ) -> dict:
        return search_paper_evidence_handler(paper_id=paper_id, query=query, top_k=top_k, ctx=ctx)

    @server.tool(
        name="search_papers",
        description="Search and list research papers accessible to the authenticated user. Optionally filter by project ID or search by title keyword.",
    )
    def search_papers(
        query: str = "",
        project_id: Optional[int] = None,
        limit: int = 10,
        ctx: Context = None,
    ) -> dict:
        return search_papers_handler(query=query, project_id=project_id, limit=limit, ctx=ctx)

    @server.tool(
        name="get_paper_details",
        description="Retrieve metadata, title, project information, and chunk count for a specific paper authorized for the authenticated user.",
    )
    def get_paper_details(
        paper_id: int,
        ctx: Context = None,
    ) -> dict:
        return get_paper_details_handler(paper_id=paper_id, ctx=ctx)

    @server.tool(
        name="search_my_notes",
        description="Search only the authenticated user's private notebook notes. Never searches or reveals notes belonging to other users. Optionally filters to a specific paper.",
    )
    def search_my_notes(
        query: str,
        paper_id: Optional[int] = None,
        limit: int = 5,
        ctx: Context = None,
    ) -> dict:
        return search_my_notes_handler(query=query, paper_id=paper_id, limit=limit, ctx=ctx)

    @server.tool(
        name="get_research_session_context",
        description="Retrieve the attached papers and recent conversation history for a permitted ResearchSession in the Research Workspace.",
    )
    def get_research_session_context(
        session_id: int,
        message_limit: int = 6,
        ctx: Context = None,
    ) -> dict:
        return get_research_session_context_handler(session_id=session_id, message_limit=message_limit, ctx=ctx)

    @server.tool(
        name="compare_papers",
        description="Retrieve and organize relevant comparative evidence from 2 to 4 authorized research papers against a specific question or topic.",
    )
    def compare_papers(
        paper_ids: List[int],
        query: str,
        top_k_per_paper: int = 3,
        ctx: Context = None,
    ) -> dict:
        return compare_papers_handler(paper_ids=paper_ids, query=query, top_k_per_paper=top_k_per_paper, ctx=ctx)

    return server


# Global server and ASGI app instance
server_instance = create_mcp_server()
app = server_instance.sse_app()


def main():
    """Entry point for running the standalone MCP server process."""
    import uvicorn

    host = os.environ.get("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_SERVER_PORT", "8001"))
    log_level = os.environ.get("MCP_LOG_LEVEL", "info")

    print(f"[NForge MCP Server] Starting standalone server on http://{host}:{port}/sse ...")
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()
