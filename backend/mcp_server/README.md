# NForge MCP Server

Dedicated Model Context Protocol (MCP) server for NForge.
Exposes application functionality exclusively via MCP tools to the LLM orchestration layer.

## Architecture

The MCP server runs as a separate process from the Django backend.
- **Transport**: Server-Sent Events (SSE) over HTTP (`http://127.0.0.1:8001/sse`).
- **Security & Auth**: Server-to-server shared secret (`X-MCP-Auth-Key`) and trusted caller context (`X-MCP-User-Id`).
- **Tools Registered**:
  1. `search_paper_evidence`: Semantic evidence retrieval from an authorized paper with page references.
  2. `search_papers`: List papers accessible to the authenticated user.
  3. `get_paper_details`: Metadata and chunk stats for an authorized paper.
  4. `search_my_notes`: Search strictly the authenticated user's private notebook notes.
  5. `get_research_session_context`: Retrieve papers and recent message history for an authorized session.
  6. `compare_papers`: Multi-paper evidence retrieval for comparative analysis.

## Requirements

Install dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Running the Server

Start the standalone MCP server:
```bash
# From backend/
python -m mcp_server.server
```

Or using uvicorn directly:
```bash
uvicorn mcp_server.server:app --host 127.0.0.1 --port 8001
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MCP_ENABLED` | Set `true` to enable exclusive MCP tool interface | `false` |
| `MCP_SERVER_HOST` | Host interface for MCP server | `127.0.0.1` |
| `MCP_SERVER_PORT` | Port for MCP server | `8001` |
| `MCP_SERVER_URL` | Full URL for Django client to connect to | `http://127.0.0.1:8001/sse` |
| `MCP_AUTH_KEY` | Shared secret key for MCP authentication | `nforge-local-dev-mcp-key-change-in-production` |
| `MCP_MAX_TOOL_ITERATIONS` | Max tool calls before synthesizing final response | `5` |
| `MCP_TIMEOUT` | Client timeout in seconds | `10.0` |

## Rollback / Disabling MCP

To disable MCP and restore direct Python service execution:
1. In `backend/.env`, set `MCP_ENABLED=false` (or remove the variable).
2. Restart the Django backend server.
