"""
MCP AI Orchestrator for NForge.

Bridges Gemini and MCP tools:
1. Discovers tools from the MCP server.
2. Passes tools to Gemini via function calling.
3. Validates and executes tool calls exclusively through the MCP client.
4. Manages multi-turn tool calling with iteration limits.
5. In MCP-only mode, never falls back to direct internal Python function execution.
6. Returns standard NForge payload: answer, sources, citation_map, notes_used, notes_used_count.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from google import genai
from google.genai import types

from ai.citations import (
    build_citation_id,
    build_citation_map,
    format_citation_label,
    get_citation_number_for_id,
)
from ai.mcp_client import (
    MCPClient,
    MCPError,
    MCPUnavailableError,
    default_mcp_client,
    is_mcp_enabled,
)
from ai.services import RateLimitError, _is_rate_limit_error

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 5


def get_max_tool_iterations() -> int:
    """Return maximum allowed tool call iterations."""
    try:
        return int(os.environ.get("MCP_MAX_TOOL_ITERATIONS", DEFAULT_MAX_ITERATIONS))
    except (ValueError, TypeError):
        return DEFAULT_MAX_ITERATIONS


def execute_gemini_mcp_turn(
    user: User,
    system_instruction: str,
    user_prompt: str,
    mcp_client: Optional[MCPClient] = None,
    max_iterations: Optional[int] = None,
    feature_name: str = "mcp_ai",
) -> Dict[str, Any]:
    """
    Execute an AI request where tools are accessed exclusively through MCP.

    Args:
        user: The authenticated Django User.
        system_instruction: The system prompt guiding Gemini's persona and rules.
        user_prompt: The user's query or prompt.
        mcp_client: The MCPClient instance (defaults to default_mcp_client).
        max_iterations: Maximum tool call iterations.
        feature_name: Diagnostic feature label.

    Returns:
        Standard NForge AI response dict:
        {
            "answer": str,
            "sources": list[dict],
            "citation_map": dict,
            "notes_used": list[int],
            "notes_used_count": int,
            "tool_calls_executed": list[dict],
        }
    """
    client_instance = mcp_client or default_mcp_client
    max_iter = max_iterations or get_max_tool_iterations()

    # 1. Discover tools via MCP
    gemini_tools = client_instance.get_gemini_tools(user)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    gemini_client = genai.Client(api_key=api_key)

    # 2. Setup Gemini content and config
    config = types.GenerateContentConfig(
        tools=gemini_tools if gemini_tools else None,
        system_instruction=system_instruction,
    )

    contents: List[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
    ]

    all_retrieved_chunks = []
    notes_used_ids = set()
    executed_tool_calls = []

    iteration = 0
    final_answer = ""

    while iteration < max_iter:
        iteration += 1

        # Call Gemini
        start_time = time.time()
        try:
            print(f"[MCP AI] Gemini turn #{iteration} ({feature_name})...")
            response = gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=config,
            )
            duration = time.time() - start_time
            print(f"[DIAGNOSTICS] Feature: {feature_name} | Turn #{iteration} | Duration: {duration:.2f}s")
        except Exception as err:
            if _is_rate_limit_error(err):
                raise RateLimitError("Gemini API rate limit exceeded.") from err
            raise

        # Check if the model requested function calls
        function_calls = getattr(response, "function_calls", None)

        if not function_calls:
            # Model generated a direct response or final synthesis
            final_answer = response.text or ""
            break

        # Append model response containing the tool call requests to history
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            contents.append(types.Content(role="model", parts=response.candidates[0].content.parts))

        # Execute each requested function call through MCP
        for fc in function_calls:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            print(f"[MCP AI] Executing MCP tool '{tool_name}' with args {tool_args}")

            # Route through MCP Client exclusively
            tool_result = client_instance.call_tool(tool_name, tool_args, user=user)
            executed_tool_calls.append({
                "tool": tool_name,
                "args": tool_args,
                "result_status": tool_result.get("status") if isinstance(tool_result, dict) else "unknown",
            })

            # Harvest paper evidence chunks if returned
            if isinstance(tool_result, dict):
                # search_paper_evidence returns "sources"
                if "sources" in tool_result and isinstance(tool_result["sources"], list):
                    all_retrieved_chunks.extend(tool_result["sources"])
                # compare_papers returns "comparisons" with sources
                if "comparisons" in tool_result and isinstance(tool_result["comparisons"], list):
                    for comp in tool_result["comparisons"]:
                        if isinstance(comp, dict) and "sources" in comp:
                            all_retrieved_chunks.extend(comp["sources"])
                # search_my_notes returns "notes"
                if "notes" in tool_result and isinstance(tool_result["notes"], list):
                    for n in tool_result["notes"]:
                        if isinstance(n, dict) and "id" in n:
                            notes_used_ids.add(n["id"])

            # Provide the tool result back to Gemini
            fr_part = types.Part.from_function_response(
                name=tool_name,
                response={"result": tool_result},
            )
            contents.append(types.Content(role="user", parts=[fr_part]))

        # If we reached max iterations, force final synthesis without further tool calls
        if iteration >= max_iter:
            print(f"[MCP AI] Reached max tool iterations ({max_iter}). Requesting final synthesis...")
            synthesis_prompt = "Please synthesize your final answer now using the tool results obtained above."
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=synthesis_prompt)]))
            no_tool_config = types.GenerateContentConfig(system_instruction=system_instruction)
            final_resp = gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=no_tool_config,
            )
            final_answer = final_resp.text or ""
            break

    # 3. Format grounded sources and citations
    sources = []
    seen_chunks = set()

    for idx, c in enumerate(all_retrieved_chunks):
        chunk_id = c.get("chunk_id")
        paper_id = c.get("paper_id")
        if chunk_id and (paper_id, chunk_id) in seen_chunks:
            continue
        if chunk_id:
            seen_chunks.add((paper_id, chunk_id))

        citation_id = build_citation_id(paper_id, chunk_id) if (paper_id and chunk_id) else None

        sources.append({
            "source_number": len(sources) + 1,
            "citation_id": citation_id,
            "paper_id": paper_id,
            "paper_title": c.get("paper_title") or "Unknown Paper",
            "chunk_id": chunk_id,
            "chunk_index": c.get("chunk_index"),
            "page_number": c.get("page_number"),
            "text": c.get("text") or "",
            "similarity": c.get("similarity"),
        })

    citation_map = build_citation_map(sources)
    for src in sources:
        cid = src.get("citation_id")
        num = get_citation_number_for_id(citation_map, cid)
        if num is not None:
            src["citation_number"] = num
            src["citation_label"] = format_citation_label(num)

    notes_used_list = sorted(list(notes_used_ids))

    return {
        "answer": final_answer,
        "sources": sources,
        "citation_map": citation_map,
        "notes_used": notes_used_list,
        "notes_used_count": len(notes_used_list),
        "tool_calls_executed": executed_tool_calls,
    }
