"""
MCP Client for NForge.

Connects Django AI services to the dedicated NForge MCP Server.
Provides:
1. Tool discovery and translation to Gemini function declarations.
2. Secure tool invocation transmitting authenticated user context via headers.
3. Strict MCP-only enforcement (no direct execution bypass when MCP is enabled).
4. Configurable transport: Remote SSE (default) or inprocess (for tests/local embedded).
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from google.genai import types

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP operations."""
    pass


class MCPUnavailableError(MCPError):
    """Raised when the MCP server is unreachable or offline."""
    pass


class MCPToolExecutionError(MCPError):
    """Raised when an MCP tool returns an error or execution fails."""
    pass


def is_mcp_enabled() -> bool:
    """Return whether MCP is enabled as the exclusive LLM tool interface."""
    val = os.environ.get("MCP_ENABLED", "false").lower()
    return val in ("true", "1", "t", "yes", "mcp")


def get_mcp_server_url() -> str:
    """Return the configured MCP server URL."""
    return os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8001/sse")


def get_mcp_auth_key() -> str:
    """Return the configured MCP server authentication key."""
    return os.environ.get("MCP_AUTH_KEY", "nforge-local-dev-mcp-key-change-in-production")


def get_mcp_timeout() -> float:
    """Return the MCP request timeout in seconds."""
    try:
        return float(os.environ.get("MCP_TIMEOUT", "10.0"))
    except (ValueError, TypeError):
        return 10.0


def _build_auth_headers(user: Optional[User]) -> Dict[str, str]:
    """Construct trusted server-side authentication headers for MCP requests."""
    user_id_str = str(user.id) if (user and getattr(user, "is_authenticated", False)) else "0"
    return {
        "X-MCP-Auth-Key": get_mcp_auth_key(),
        "X-MCP-User-Id": user_id_str,
    }


class MCPClient:
    """
    Client for interacting with the NForge MCP server.
    """

    def __init__(self, server_url: Optional[str] = None, timeout: Optional[float] = None):
        self.server_url = server_url or get_mcp_server_url()
        self.timeout = timeout or get_mcp_timeout()

    async def _list_tools_remote(self, user: Optional[User]) -> List[Any]:
        headers = _build_auth_headers(user)
        try:
            async with sse_client(self.server_url, headers=headers, timeout=self.timeout) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.list_tools()
                    return getattr(response, "tools", []) or []
        except Exception as err:
            logger.error(f"[MCPClient] Failed to list tools from {self.server_url}: {err}")
            raise MCPUnavailableError(f"Could not connect to MCP server at {self.server_url}: {err}") from err

    async def _list_tools_inprocess(self) -> List[Any]:
        from mcp_server.server import server_instance
        tools = await server_instance.list_tools()
        return tools

    async def list_tools_async(self, user: Optional[User] = None) -> List[Any]:
        """List all tools exposed by the MCP server."""
        if self.server_url == "inprocess":
            return await self._list_tools_inprocess()
        return await self._list_tools_remote(user)

    def list_tools(self, user: Optional[User] = None) -> List[Any]:
        """Synchronous wrapper for listing tools."""
        return asyncio.run(self.list_tools_async(user))

    def get_gemini_tools(self, user: Optional[User] = None) -> List[types.Tool]:
        """
        Fetch registered MCP tools and convert them into Gemini types.Tool objects.
        """
        tools = self.list_tools(user)
        declarations = []

        for t in tools:
            # t has name, description, input_schema
            schema = getattr(t, "input_schema", None)
            if hasattr(schema, "model_dump"):
                schema_dict = schema.model_dump()
            elif isinstance(schema, dict):
                schema_dict = schema
            else:
                schema_dict = {"type": "object", "properties": {}}

            fd = types.FunctionDeclaration(
                name=t.name,
                description=t.description or f"NForge tool: {t.name}",
                parameters_json_schema=schema_dict,
            )
            declarations.append(fd)

        if not declarations:
            return []

        return [types.Tool(function_declarations=declarations)]

    async def call_tool_async(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool via the MCP protocol.
        """
        if self.server_url == "inprocess":
            return await self._call_tool_inprocess(tool_name, arguments, user)
        return await self._call_tool_remote(tool_name, arguments, user)

    async def _call_tool_remote(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        headers = _build_auth_headers(user)
        try:
            async with sse_client(self.server_url, headers=headers, timeout=self.timeout) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return self._parse_tool_result(result)
        except MCPError:
            raise
        except Exception as err:
            logger.error(f"[MCPClient] Error calling tool '{tool_name}' at {self.server_url}: {err}")
            raise MCPUnavailableError(
                f"MCP server communication failed for tool '{tool_name}': {err}"
            ) from err

    async def _call_tool_inprocess(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        from mcp_server.server import server_instance
        from mcp.server.mcpserver import Context

        # Simulate context headers for in-process calls
        from unittest.mock import MagicMock
        headers = _build_auth_headers(user)
        req_mock = MagicMock(headers=headers, user=user)
        rc_mock = MagicMock(request=req_mock)
        ctx = Context(
            request_context=rc_mock,
            mcp_server=server_instance,
        )

        # Call tool through the MCPServer instance directly
        try:
            result = await server_instance.call_tool(tool_name, arguments, context=ctx)
            return self._parse_tool_result(result)
        except Exception as err:
            logger.error(f"[MCPClient Inprocess] Error calling tool '{tool_name}': {err}")
            raise MCPToolExecutionError(f"In-process tool call failed: {err}") from err

    def _parse_tool_result(self, result: Any) -> Dict[str, Any]:
        """Extract JSON or structured content from an MCP CallToolResult."""
        if getattr(result, "is_error", False):
            error_text = "MCP tool reported an error."
            if hasattr(result, "content") and result.content:
                error_text = getattr(result.content[0], "text", error_text)
            return {"status": "error", "error": error_text, "code": "TOOL_ERROR"}

        # Check structured_content
        if hasattr(result, "structured_content") and result.structured_content is not None:
            sc = result.structured_content
            if isinstance(sc, dict) and "result" in sc:
                res_val = sc["result"]
                if isinstance(res_val, dict):
                    return res_val
                elif isinstance(res_val, str):
                    try:
                        return json.loads(res_val)
                    except Exception:
                        return {"result": res_val}
            return sc

        # Check content text
        if hasattr(result, "content") and result.content:
            for item in result.content:
                text_val = getattr(item, "text", "")
                if text_val:
                    try:
                        return json.loads(text_val)
                    except Exception:
                        return {"result": text_val}

        return {"result": None}

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for tool execution."""
        return asyncio.run(self.call_tool_async(tool_name, arguments, user))


# Default client instance
default_mcp_client = MCPClient()
