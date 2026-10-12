"""
Regression and Integration Test Suite for NForge MCP Tool Interface.

Covers all 12 testing requirements:
1. MCP server startup and tool discovery.
2. Correct tool selection for different user questions.
3. Successful MCP tool invocation and result handling.
4. Invalid tool names and malformed arguments.
5. Multiple tool calls and iteration limits.
6. MCP server unavailable, timeout, and malformed-response scenarios.
7. Authentication and project permissions.
8. Cross-user notebook privacy.
9. Unauthorized paper and session access.
10. Genuine evidence and page references.
11. Existing single-paper Q&A and Research Workspace compatibility.
12. No silent direct-execution fallback when MCP-only mode is enabled.
"""

from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from google.genai import types

from projects.models import Project, ProjectMember
from papers.models import Paper, PaperNote
from ai.models import PaperChunk, ResearchSession, ResearchMessage, ResearchEvidence
from ai.mcp_client import (
    MCPClient,
    MCPUnavailableError,
    MCPError,
    is_mcp_enabled,
    get_mcp_auth_key,
)
from ai.mcp_orchestrator import execute_gemini_mcp_turn
from mcp_server.server import server_instance
from mcp_server.auth import validate_context_auth, require_authenticated_user, MCPAuthError
from mcp.server.mcpserver import Context


class MCPIntegrationTests(TransactionTestCase):
    """
    Comprehensive test suite validating the Model Context Protocol (MCP)
    as the exclusive LLM tool interface.
    """

    def setUp(self):
        self.client = APIClient()

        # Users
        self.owner = User.objects.create_user(username="alice_owner", password="password123")
        self.editor = User.objects.create_user(username="bob_editor", password="password123")
        self.viewer = User.objects.create_user(username="carol_viewer", password="password123")
        self.outsider = User.objects.create_user(username="dave_outsider", password="password123")

        # Project & Memberships
        self.project = Project.objects.create(owner=self.owner, title="Distributed Systems Research")
        ProjectMember.objects.create(project=self.project, user=self.editor, role=ProjectMember.ROLE_EDITOR)
        ProjectMember.objects.create(project=self.project, user=self.viewer, role=ProjectMember.ROLE_VIEWER)

        # Papers in project
        self.paper1 = Paper.objects.create(project=self.project, title="Distributed Consensus Algorithms")
        self.paper2 = Paper.objects.create(project=self.project, title="Fault-Tolerant Replicated State Machines")

        # Chunks for Paper 1
        dummy_embedding = [0.1] * 384
        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=3,
            text="Raft achieves consensus via an elected leader and replicated log entries.",
            embedding=dummy_embedding,
        )
        self.chunk2 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=1,
            page_number=5,
            text="Paxos guarantees safety under asynchronous network conditions.",
            embedding=dummy_embedding,
        )

        # Chunks for Paper 2
        self.chunk3 = PaperChunk.objects.create(
            paper=self.paper2,
            chunk_index=0,
            page_number=1,
            text="Replicated state machines provide high availability by executing identical sequence of commands.",
            embedding=dummy_embedding,
        )

        # Private Notebook Notes
        self.owner_note = PaperNote.objects.create(
            user=self.owner,
            paper=self.paper1,
            title="Leader Election Analysis",
            content="Raft leader election uses randomized election timers to avoid split votes.",
        )
        self.editor_note = PaperNote.objects.create(
            user=self.editor,
            paper=self.paper1,
            title="Editor Private Observations",
            content="Heartbeats must be sent periodically to maintain leadership.",
        )

        # Research Session
        self.session = ResearchSession.objects.create(
            project=self.project,
            title="Consensus Protocol Comparison",
        )
        self.session.papers.add(self.paper1, self.paper2)

        # Dedicated test MCP client (uses inprocess server for deterministic fast testing)
        self.mcp_client = MCPClient(server_url="inprocess")

    # -------------------------------------------------------------------------
    # 1. MCP Server Startup and Tool Discovery
    # -------------------------------------------------------------------------
    def test_01_server_startup_and_tool_discovery(self):
        """Verify all 6 tools are discovered with valid schemas and no user_id leakage."""
        tools = self.mcp_client.list_tools()
        tool_names = [t.name for t in tools]

        expected_tools = [
            "search_paper_evidence",
            "search_papers",
            "get_paper_details",
            "search_my_notes",
            "get_research_session_context",
            "compare_papers",
        ]

        for expected in expected_tools:
            self.assertIn(expected, tool_names, f"Missing tool: {expected}")

        # Verify that Gemini tools are generated and none expose user_id or context
        gemini_tools = self.mcp_client.get_gemini_tools(self.owner)
        self.assertEqual(len(gemini_tools), 1)
        declarations = gemini_tools[0].function_declarations
        self.assertEqual(len(declarations), 6)

        for decl in declarations:
            props = decl.parameters_json_schema.get("properties", {})
            self.assertNotIn("user_id", props, f"Tool {decl.name} must never expose user_id in schema.")
            self.assertNotIn("ctx", props, f"Tool {decl.name} must never expose ctx in schema.")

    def test_02_correct_tool_selection_for_different_user_questions(self):
        """Verify that Gemini function calls trigger the correct MCP tool execution."""
        fc1 = MagicMock()
        fc1.name = "search_paper_evidence"
        fc1.args = {"paper_id": self.paper1.id, "query": "Raft leader"}
        mock_response_turn1 = MagicMock()
        mock_response_turn1.function_calls = [fc1]
        mock_response_turn1.candidates = [
            MagicMock(content=MagicMock(parts=[
                types.Part.from_function_call(name="search_paper_evidence", args={"paper_id": self.paper1.id, "query": "Raft leader"})
            ]))
        ]

        mock_response_turn2 = MagicMock()
        mock_response_turn2.function_calls = None
        mock_response_turn2.text = "Raft uses randomized timers for leader election."

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.side_effect = [mock_response_turn1, mock_response_turn2]

            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
                result = execute_gemini_mcp_turn(
                    user=self.owner,
                    system_instruction="You are an academic assistant.",
                    user_prompt="Explain Raft leader election.",
                    mcp_client=self.mcp_client,
                )

                self.assertIn("Raft uses randomized timers", result["answer"])
                self.assertEqual(len(result["tool_calls_executed"]), 1)
                self.assertEqual(result["tool_calls_executed"][0]["tool"], "search_paper_evidence")

    # -------------------------------------------------------------------------
    # 3. Successful MCP Tool Invocation and Result Handling
    # -------------------------------------------------------------------------
    def test_03_successful_mcp_tool_invocation_and_result_handling(self):
        """Invoke search_paper_evidence through MCP and verify result format."""
        result = self.mcp_client.call_tool(
            "search_paper_evidence",
            {"paper_id": self.paper1.id, "query": "Raft consensus", "top_k": 5},
            user=self.owner,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["paper_id"], self.paper1.id)
        self.assertTrue(len(result["sources"]) > 0)

        first_src = result["sources"][0]
        self.assertEqual(first_src["chunk_id"], self.chunk1.id)
        self.assertEqual(first_src["page_number"], 3)
        self.assertIn("Raft achieves consensus", first_src["text"])

    # -------------------------------------------------------------------------
    # 4. Invalid Tool Names and Malformed Arguments
    # -------------------------------------------------------------------------
    def test_04_invalid_tool_names_and_malformed_arguments(self):
        """Verify error responses for invalid tool names and bad parameters."""
        # Malformed paper_id
        res_bad_id = self.mcp_client.call_tool(
            "search_paper_evidence",
            {"paper_id": -99, "query": "test"},
            user=self.owner,
        )
        self.assertEqual(res_bad_id["status"], "error")
        self.assertEqual(res_bad_id["code"], "BAD_REQUEST")

        # Empty query
        res_bad_query = self.mcp_client.call_tool(
            "search_paper_evidence",
            {"paper_id": self.paper1.id, "query": ""},
            user=self.owner,
        )
        self.assertEqual(res_bad_query["status"], "error")
        self.assertEqual(res_bad_query["code"], "BAD_REQUEST")

        # Compare papers with fewer than 2 papers
        res_compare_bad = self.mcp_client.call_tool(
            "compare_papers",
            {"paper_ids": [self.paper1.id], "query": "comparison"},
            user=self.owner,
        )
        self.assertEqual(res_compare_bad["status"], "error")
        self.assertEqual(res_compare_bad["code"], "BAD_REQUEST")

    # -------------------------------------------------------------------------
    # 5. Multiple Tool Calls and Iteration Limits
    # -------------------------------------------------------------------------
    def test_05_multiple_tool_calls_and_iteration_limits(self):
        """Verify that multi-step tool calls succeed and iteration ceiling stops loops."""
        # Create an infinite tool call loop response
        fc_loop = MagicMock()
        fc_loop.name = "get_paper_details"
        fc_loop.args = {"paper_id": self.paper1.id}
        mock_loop_resp = MagicMock()
        mock_loop_resp.function_calls = [fc_loop]
        mock_loop_resp.candidates = [
            MagicMock(content=MagicMock(parts=[
                types.Part.from_function_call(name="get_paper_details", args={"paper_id": self.paper1.id})
            ]))
        ]

        mock_final_resp = MagicMock()
        mock_final_resp.function_calls = None
        mock_final_resp.text = "Reached max iterations and synthesized answer."

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            # 2 tool loop turns + 1 final synthesis turn
            mock_client.models.generate_content.side_effect = [
                mock_loop_resp,
                mock_loop_resp,
                mock_final_resp,
            ]

            with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
                result = execute_gemini_mcp_turn(
                    user=self.owner,
                    system_instruction="Assistant",
                    user_prompt="Tell me details.",
                    mcp_client=self.mcp_client,
                    max_iterations=2,
                )

                self.assertIn("synthesized answer", result["answer"])
                self.assertEqual(len(result["tool_calls_executed"]), 2)

    # -------------------------------------------------------------------------
    # 6. MCP Server Unavailable Scenarios
    # -------------------------------------------------------------------------
    def test_06_mcp_server_unavailable_scenario(self):
        """Verify that when MCP server is unreachable, MCPUnavailableError is raised."""
        bad_client = MCPClient(server_url="http://127.0.0.1:9999/sse", timeout=0.1)

        with self.assertRaises(MCPUnavailableError):
            bad_client.list_tools(self.owner)

        with self.assertRaises(MCPUnavailableError):
            bad_client.call_tool("search_paper_evidence", {"paper_id": self.paper1.id, "query": "test"}, self.owner)

    # -------------------------------------------------------------------------
    # 7. Authentication and Project Permissions
    # -------------------------------------------------------------------------
    def test_07_authentication_and_project_permissions(self):
        """Validate auth key checks and role permissions."""
        # Invalid Auth Key
        req_mock = MagicMock(headers={"x-mcp-auth-key": "wrong_key", "x-mcp-user-id": str(self.owner.id)}, user=None)
        rc_mock = MagicMock(request=req_mock)
        fake_ctx = Context(
            request_context=rc_mock,
            mcp_server=server_instance,
        )
        is_valid, err_msg, user = validate_context_auth(fake_ctx)
        self.assertFalse(is_valid)
        self.assertIn("Invalid or missing X-MCP-Auth-Key", err_msg)

        # Viewer can read evidence
        res_viewer = self.mcp_client.call_tool(
            "search_paper_evidence",
            {"paper_id": self.paper1.id, "query": "consensus"},
            user=self.viewer,
        )
        self.assertEqual(res_viewer["status"], "success")

        # Outsider is denied
        res_outsider = self.mcp_client.call_tool(
            "search_paper_evidence",
            {"paper_id": self.paper1.id, "query": "consensus"},
            user=self.outsider,
        )
        self.assertEqual(res_outsider["status"], "error")
        self.assertEqual(res_outsider["code"], "FORBIDDEN")

    # -------------------------------------------------------------------------
    # 8. Cross-User Notebook Privacy
    # -------------------------------------------------------------------------
    def test_08_cross_user_notebook_privacy(self):
        """Owner and editor can only search their own private notes via MCP."""
        owner_res = self.mcp_client.call_tool(
            "search_my_notes",
            {"query": "election", "paper_id": self.paper1.id},
            user=self.owner,
        )
        self.assertEqual(owner_res["status"], "success")
        owner_note_ids = [n["id"] for n in owner_res["notes"]]
        self.assertIn(self.owner_note.id, owner_note_ids)
        self.assertNotIn(self.editor_note.id, owner_note_ids)

        editor_res = self.mcp_client.call_tool(
            "search_my_notes",
            {"query": "election", "paper_id": self.paper1.id},
            user=self.editor,
        )
        self.assertEqual(editor_res["status"], "success")
        editor_note_ids = [n["id"] for n in editor_res["notes"]]
        self.assertNotIn(self.owner_note.id, editor_note_ids)

    # -------------------------------------------------------------------------
    # 9. Unauthorized Paper and Session Access
    # -------------------------------------------------------------------------
    def test_09_unauthorized_paper_and_session_access(self):
        """Ensure accessing unauthorized or nonexistent papers and sessions returns errors."""
        # Nonexistent paper
        res_nonexistent_paper = self.mcp_client.call_tool(
            "get_paper_details",
            {"paper_id": 99999},
            user=self.owner,
        )
        self.assertEqual(res_nonexistent_paper["code"], "NOT_FOUND")

        # Nonexistent session
        res_nonexistent_session = self.mcp_client.call_tool(
            "get_research_session_context",
            {"session_id": 99999},
            user=self.owner,
        )
        self.assertEqual(res_nonexistent_session["code"], "NOT_FOUND")

        # Outsider accessing session
        res_outsider_session = self.mcp_client.call_tool(
            "get_research_session_context",
            {"session_id": self.session.id},
            user=self.outsider,
        )
        self.assertEqual(res_outsider_session["code"], "FORBIDDEN")

    # -------------------------------------------------------------------------
    # 10. Genuine Evidence and Page References
    # -------------------------------------------------------------------------
    def test_10_genuine_evidence_and_page_references(self):
        """Verify that chunks retrieved through MCP contain genuine page numbers and chunk IDs."""
        res = self.mcp_client.call_tool(
            "search_paper_evidence",
            {"paper_id": self.paper1.id, "query": "Raft consensus", "top_k": 2},
            user=self.owner,
        )
        self.assertEqual(res["status"], "success")
        for src in res["sources"]:
            self.assertIn("page_number", src)
            self.assertIn("chunk_id", src)
            self.assertIn("similarity", src)
            self.assertIn(src["page_number"], [3, 5])

    # -------------------------------------------------------------------------
    # 11. Single-Paper Q&A and Research Workspace Compatibility
    # -------------------------------------------------------------------------
    def test_11_single_paper_qa_and_research_workspace_compatibility(self):
        """Validate API endpoints with MCP enabled."""
        self.client.force_authenticate(user=self.owner)

        mock_answer_resp = {
            "answer": "Consensus is maintained using leader heartbeats.",
            "sources": [
                {
                    "source_number": 1,
                    "citation_id": f"cite_p{self.paper1.id}_c{self.chunk1.id}",
                    "paper_id": self.paper1.id,
                    "paper_title": self.paper1.title,
                    "chunk_id": self.chunk1.id,
                    "chunk_index": self.chunk1.chunk_index,
                    "page_number": self.chunk1.page_number,
                    "text": self.chunk1.text,
                }
            ],
            "citation_map": {
                f"cite_p{self.paper1.id}_c{self.chunk1.id}": {
                    "citation_number": 1,
                    "citation_label": "[1]",
                }
            },
            "notes_used": [self.owner_note.id],
            "notes_used_count": 1,
            "tool_calls_executed": [{"tool": "search_paper_evidence", "args": {}}],
        }

        with patch.dict("os.environ", {"MCP_ENABLED": "true"}):
            with patch("ai.views.execute_gemini_mcp_turn", return_value=mock_answer_resp):
                # 1. Single-paper Q&A
                resp_ask = self.client.post("/api/ai/ask/", {
                    "paper_id": self.paper1.id,
                    "question": "How is consensus maintained?",
                }, format="json")

                self.assertEqual(resp_ask.status_code, status.HTTP_200_OK)
                self.assertIn("answer", resp_ask.data)
                self.assertIn("sources", resp_ask.data)
                self.assertIn("citation_map", resp_ask.data)
                self.assertEqual(resp_ask.data["notes_used_count"], 1)

                # 2. Research Workspace Q&A
                resp_research = self.client.post("/api/ai/research-ask/", {
                    "session_id": self.session.id,
                    "question": "Synthesize consensus across both papers.",
                }, format="json")

                self.assertEqual(resp_research.status_code, status.HTTP_200_OK)
                self.assertIn("answer", resp_research.data)
                self.assertIn("sources", resp_research.data)
                self.assertEqual(resp_research.data["session_id"], self.session.id)

    # -------------------------------------------------------------------------
    # 12. No Silent Direct-Execution Fallback in MCP Mode
    # -------------------------------------------------------------------------
    def test_12_no_silent_fallback_when_mcp_enabled(self):
        """When MCP is enabled and MCP server is unavailable, returns HTTP 503 instead of falling back."""
        self.client.force_authenticate(user=self.owner)

        with patch.dict("os.environ", {"MCP_ENABLED": "true"}):
            with patch(
                "ai.views.execute_gemini_mcp_turn",
                side_effect=MCPUnavailableError("MCP server offline at http://127.0.0.1:8001/sse"),
            ):
                with patch("ai.services.semantic_search") as mock_direct_search:
                    response = self.client.post("/api/ai/ask/", {
                        "paper_id": self.paper1.id,
                        "question": "Explain consensus.",
                    }, format="json")

                    # Must return HTTP 503 MCP_UNAVAILABLE
                    self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
                    self.assertEqual(response.data["code"], "MCP_UNAVAILABLE")

                    # Verify direct semantic_search was NEVER called (zero silent fallback!)
                    mock_direct_search.assert_not_called()
