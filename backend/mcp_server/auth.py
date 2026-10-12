"""
Authentication and Authorization helpers for NForge MCP Server.

Validates that:
1. The caller provides the trusted server auth key matching MCP_AUTH_KEY.
2. The caller provides a valid authenticated user ID via X-MCP-User-Id.
3. The user exists, is active, and is resolved securely through Django's User model.
"""

import hmac
import os
from typing import Optional, Tuple
from django.contrib.auth.models import User
from mcp.server.mcpserver import Context


class MCPAuthError(Exception):
    """Raised when MCP server authentication or user identification fails."""
    pass


def get_expected_auth_key() -> str:
    """Return the configured MCP auth key from environment, with a secure default."""
    return os.environ.get("MCP_AUTH_KEY", "nforge-local-dev-mcp-key-change-in-production")


def validate_context_auth(ctx: Context) -> Tuple[bool, Optional[str], Optional[User]]:
    """
    Extract and validate server credentials and authenticated user from MCP Context.
    
    Returns:
        (is_valid: bool, error_message: Optional[str], user: Optional[User])
    """
    if not ctx:
        return False, "Missing request headers context in MCP invocation.", None

    headers = None
    try:
        headers = ctx.headers
    except (ValueError, AttributeError):
        pass

    if not headers and hasattr(ctx, "_request_context") and ctx._request_context is not None:
        req = getattr(ctx._request_context, "request", None)
        if req and hasattr(req, "headers"):
            headers = req.headers

    if not headers:
        return False, "Missing request headers context in MCP invocation.", None

    provided_key = headers.get("x-mcp-auth-key") or headers.get("X-MCP-Auth-Key")
    expected_key = get_expected_auth_key()

    if not provided_key or not hmac.compare_digest(str(provided_key), expected_key):
        return False, "Invalid or missing X-MCP-Auth-Key.", None

    # Check if a User instance is already attached directly (in-process client mode)
    if hasattr(ctx, "_request_context") and ctx._request_context is not None:
        req = getattr(ctx._request_context, "request", None)
        if req and hasattr(req, "user") and req.user is not None:
            return True, None, req.user

    raw_user_id = headers.get("x-mcp-user-id") or headers.get("X-MCP-User-Id")
    if not raw_user_id:
        return False, "Missing X-MCP-User-Id in MCP request.", None

    try:
        user_id = int(raw_user_id)
        if user_id <= 0:
            return False, "Invalid X-MCP-User-Id (must be positive integer).", None
    except (ValueError, TypeError):
        return False, f"Malformed X-MCP-User-Id: {raw_user_id}", None

    try:
        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return False, f"User with id {user_id} not found or inactive.", None
    except Exception as err:
        return False, f"Database error resolving user: {err}", None

    return True, None, user


def require_authenticated_user(ctx: Context) -> User:
    """
    Strictly require and return the authenticated User from the MCP Context.
    Raises MCPAuthError if authentication fails.
    """
    is_valid, error_msg, user = validate_context_auth(ctx)
    if not is_valid or not user:
        raise MCPAuthError(error_msg or "Authentication failed.")
    return user
