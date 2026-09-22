from django.test import TestCase
from django.contrib.auth.models import User
from projects.models import Project
from papers.models import Paper
from ai.models import PaperChunk, ResearchSession, ResearchMessage, ResearchEvidence
from ai.services import (
    split_into_sentences,
    split_text_structure_aware,
    create_paper_chunks,
    split_word_boundary,
)


class StructureAwareChunkingTests(TestCase):

    def test_sentence_splitting_abbreviations_and_decimals(self):
        text = (
            "Dr. J. K. Smith et al. published Fig. 3.14 in Vol. 12, No. 4. "
            "The operating system is a control program. "
            "Is resource allocation fair? Yes, according to Ref. [1]."
        )
        sents = split_into_sentences(text)
        self.assertEqual(len(sents), 4)
        self.assertEqual(
            sents[0],
            "Dr. J. K. Smith et al. published Fig. 3.14 in Vol. 12, No. 4.",
        )
        self.assertEqual(
            sents[1],
            "The operating system is a control program.",
        )
        self.assertEqual(
            sents[2],
            "Is resource allocation fair?",
        )
        self.assertEqual(
            sents[3],
            "Yes, according to Ref. [1].",
        )

    def test_structure_aware_chunking_preserves_sentences_and_pages(self):
        page1_paras = [
            "1. Introduction",
            "An operating system acts as an intermediary between the user of a computer and computer hardware. Its goal is to provide an environment in which a user can execute programs cleanly.",
            "Operating systems manage hardware resources effectively and fairly.",
        ]
        page2_paras = [
            "2. System Calls",
            "System calls provide an interface to the services provided by the operating system. They are generally available as assembly language instructions.",
        ]
        page_structures = [(1, page1_paras), (2, page2_paras)]

        chunks = split_text_structure_aware(
            page_structures,
            target_chunk_size=200,
            max_chunk_size=300,
            min_chunk_size=50,
        )

        self.assertTrue(len(chunks) >= 2)
        # Check that page 1 chunks have page_number 1 and page 2 chunks have page_number 2
        for chunk_text, page_num in chunks:
            self.assertIn(page_num, [1, 2])
            # Check that no word is cut off (no trailing hyphens or half words)
            self.assertFalse(chunk_text.endswith("-"))

        # Verify page 1 heading attached
        p1_chunks = [c for c, p in chunks if p == 1]
        self.assertTrue(any("1. Introduction" in c for c in p1_chunks))

        # Verify page 2 heading attached
        p2_chunks = [c for c, p in chunks if p == 2]
        self.assertTrue(any("2. System Calls" in c for c in p2_chunks))

    def test_never_splits_words(self):
        text = "Supercalifragilisticexpialidocious " * 50
        chunks = split_word_boundary(text, target_size=100)
        for chunk in chunks:
            words = chunk.split()
            for w in words:
                self.assertEqual(w, "Supercalifragilisticexpialidocious")

    def test_create_paper_chunks_structure_aware(self):
        user = User.objects.create_user(username="testuser", password="password")
        project = Project.objects.create(owner=user, title="Test Project")
        paper = Paper.objects.create(project=project, title="Test Paper")

        page_structures = [
            (1, ["Abstract. Operating systems coordinate hardware resources."]),
            (2, ["Section 1. Detailed architecture analysis and design principles."]),
        ]

        chunks = create_paper_chunks(paper, page_texts=page_structures)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].page_number, 1)
        self.assertEqual(chunks[1].page_number, 2)
        self.assertIn("Operating systems", chunks[0].text)
        self.assertIn("Detailed architecture", chunks[1].text)

    def test_parse_summary_json(self):
        from ai.services import parse_summary_json
        raw = '```json\n{"overview": "An operating system manages hardware.", "key_points": ["Point 1", "Point 2"]}\n```'
        parsed = parse_summary_json(raw)
        self.assertEqual(parsed["overview"], "An operating system manages hardware.")
        self.assertEqual(len(parsed["key_points"]), 2)
        self.assertEqual(parsed["methodology"], "Not clearly stated in the paper.")

    def test_parse_research_gaps_json(self):
        from ai.services import parse_research_gaps_json
        raw = '''```json
{
    "summary_statement": "The paper lacks evaluation on non-English corpora.",
    "gaps": [
        {
            "category": "Dataset / Sample Limitation",
            "title": "Monolingual Dataset",
            "description": "The dataset is limited to English text.",
            "page_number": 4
        }
    ]
}
```'''
        parsed = parse_research_gaps_json(raw)
        self.assertEqual(parsed["summary_statement"], "The paper lacks evaluation on non-English corpora.")
        self.assertEqual(len(parsed["gaps"]), 1)
        self.assertEqual(parsed["gaps"][0]["category"], "Dataset / Sample Limitation")
        self.assertEqual(parsed["gaps"][0]["title"], "Monolingual Dataset")
    def test_handle_ai_exception(self):
        from ai.views import handle_ai_exception
        from ai.services import RateLimitError

        # Test RateLimitError -> 429
        resp_429 = handle_ai_exception(RateLimitError("Limit hit"))
        self.assertEqual(resp_429.status_code, 429)
        self.assertEqual(resp_429.data["code"], "RATE_LIMITED")
        self.assertIn("rate limit exceeded", resp_429.data["error"])

        # Test 503 Unavailable -> 503
        resp_503 = handle_ai_exception(Exception("503 UNAVAILABLE"))
        self.assertEqual(resp_503.status_code, 503)
        self.assertEqual(resp_503.data["code"], "SERVICE_UNAVAILABLE")

        # Test ValueError -> 400
        resp_400 = handle_ai_exception(ValueError("Invalid paper ID"))
        self.assertEqual(resp_400.status_code, 400)
        self.assertEqual(resp_400.data["code"], "BAD_REQUEST")


class MultiPaperRetrievalTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="retrievaluser", password="password")
        self.project = Project.objects.create(owner=self.user, title="Retrieval Project")
        self.paper1 = Paper.objects.create(project=self.project, title="Paper Alpha")
        self.paper2 = Paper.objects.create(project=self.project, title="Paper Beta")
        self.paper3 = Paper.objects.create(project=self.project, title="Paper Gamma")
        self.paper4 = Paper.objects.create(project=self.project, title="Paper Delta")
        self.paper5 = Paper.objects.create(project=self.project, title="Paper Epsilon")

        # Create chunks with mock normalized embeddings for Paper Alpha
        for i in range(10):
            PaperChunk.objects.create(
                paper=self.paper1,
                chunk_index=i,
                page_number=i + 1,
                text=f"Paper Alpha content chunk {i}",
                embedding=[0.1 * (i + 1)] + [0.0] * 383,
            )

        # Create chunks for Paper Beta
        for i in range(10):
            PaperChunk.objects.create(
                paper=self.paper2,
                chunk_index=i,
                page_number=i + 5,
                text=f"Paper Beta content chunk {i}",
                embedding=[0.05 * (i + 1)] + [0.0] * 383,
            )

    def test_retrieve_multi_paper_evidence_separate_groups_and_sorting(self):
        from unittest.mock import patch
        from ai.services import retrieve_multi_paper_evidence

        dummy_query_emb = [1.0] + [0.0] * 383
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb) as mock_emb:
            results = retrieve_multi_paper_evidence("operating system scheduling", [self.paper1, self.paper2])

            # 1. Query embedding generated ONCE
            self.assertEqual(mock_emb.call_count, 1)

            # 2. Two separate groups returned
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["paper_id"], self.paper1.id)
            self.assertEqual(results[0]["paper_title"], "Paper Alpha")
            self.assertEqual(results[1]["paper_id"], self.paper2.id)
            self.assertEqual(results[1]["paper_title"], "Paper Beta")

            # 3. Default top_k_per_paper = 5
            self.assertEqual(len(results[0]["sources"]), 5)
            self.assertEqual(len(results[1]["sources"]), 5)

            # 4. Results sorted by similarity descending
            sims_alpha = [s["similarity"] for s in results[0]["sources"]]
            self.assertEqual(sims_alpha, sorted(sims_alpha, reverse=True))

            # 5. Page numbers come from PaperChunk.page_number
            self.assertEqual(results[0]["sources"][0]["page_number"], 10)

    def test_max_chunks_limit_enforced(self):
        from unittest.mock import patch
        from ai.services import retrieve_multi_paper_evidence

        dummy_query_emb = [1.0] + [0.0] * 383
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb):
            # Test custom top_k_per_paper = 8
            results = retrieve_multi_paper_evidence("test query", [self.paper1], top_k_per_paper=8)
            self.assertEqual(len(results[0]["sources"]), 8)

            # top_k_per_paper > 8 raises ValueError
            with self.assertRaises(ValueError):
                retrieve_multi_paper_evidence("test query", [self.paper1], top_k_per_paper=9)

    def test_paper_with_no_chunks_returns_empty_sources(self):
        from unittest.mock import patch
        from ai.services import retrieve_multi_paper_evidence

        dummy_query_emb = [1.0] + [0.0] * 383
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb):
            results = retrieve_multi_paper_evidence("test query", [self.paper1, self.paper3])
            self.assertEqual(len(results), 2)
            self.assertEqual(results[1]["paper_id"], self.paper3.id)
            self.assertEqual(results[1]["sources"], [])

    def test_validation_errors(self):
        from ai.services import retrieve_multi_paper_evidence

        # Invalid empty question
        with self.assertRaises(ValueError):
            retrieve_multi_paper_evidence("", [self.paper1])

        # Invalid papers empty
        with self.assertRaises(ValueError):
            retrieve_multi_paper_evidence("valid question", [])

        # More than 4 papers
        with self.assertRaises(ValueError):
            retrieve_multi_paper_evidence("valid question", [self.paper1, self.paper2, self.paper3, self.paper4, self.paper5])

        # Invalid paper item
        with self.assertRaises(ValueError):
            retrieve_multi_paper_evidence("valid question", [self.paper1, "not a paper"])

    def test_unrelated_paper_chunks_never_returned(self):
        from unittest.mock import patch
        from ai.services import retrieve_multi_paper_evidence

        dummy_query_emb = [1.0] + [0.0] * 383
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb):
            results = retrieve_multi_paper_evidence("test query", [self.paper1])
            retrieved_chunk_ids = [s["chunk_id"] for s in results[0]["sources"]]
            p2_chunk_ids = list(PaperChunk.objects.filter(paper=self.paper2).values_list("id", flat=True))

            for cid in retrieved_chunk_ids:
                self.assertNotIn(cid, p2_chunk_ids)


class ComparePapersAPITests(TestCase):

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()

        self.user1 = User.objects.create_user(username="apiuser1", password="password")
        self.user2 = User.objects.create_user(username="apiuser2", password="password")

        self.proj1 = Project.objects.create(owner=self.user1, title="User1 Project")
        self.proj2 = Project.objects.create(owner=self.user2, title="User2 Project")

        self.paper1 = Paper.objects.create(project=self.proj1, title="Paper 1")
        self.paper2 = Paper.objects.create(project=self.proj1, title="Paper 2")
        self.paper3 = Paper.objects.create(project=self.proj1, title="Paper 3")
        self.paper4 = Paper.objects.create(project=self.proj1, title="Paper 4")
        self.paper5 = Paper.objects.create(project=self.proj1, title="Paper 5")

        self.other_paper = Paper.objects.create(project=self.proj2, title="Other User Paper")

        PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=3,
            text="Chunk text for paper 1",
            embedding=[0.1] * 384
        )

        PaperChunk.objects.create(
            paper=self.paper2,
            chunk_index=0,
            page_number=7,
            text="Chunk text for paper 2",
            embedding=[0.2] * 384
        )

    def test_unauthenticated_request_returns_401(self):
        resp = self.client.post("/api/ai/compare/", {"paper_ids": [self.paper1.id, self.paper2.id]}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_user_can_compare_accessible_papers(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch, MagicMock

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = '{"overall_synthesis": "Synthesis", "similarities": [], "differences": [], "methodology_comparison": [], "findings_comparison": [], "research_gaps": []}'

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):
            resp = self.client.post("/api/ai/compare/", {
                "paper_ids": [self.paper2.id, self.paper1.id],
                "question": "What is the key comparison?"
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # Check order preservation (requested paper2 then paper1)
            self.assertEqual(len(data["papers"]), 2)
            self.assertEqual(data["papers"][0]["paper_id"], self.paper2.id)
            self.assertEqual(data["papers"][1]["paper_id"], self.paper1.id)

            # Check question and comparison structure
            self.assertEqual(data["question"], "What is the key comparison?")
            self.assertIn("comparison", data)
            self.assertIn("overall_synthesis", data["comparison"])
            self.assertIn("similarities", data["comparison"])
            self.assertIn("differences", data["comparison"])

    def test_empty_paper_ids_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {"paper_ids": []}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_one_paper_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {"paper_ids": [self.paper1.id]}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_more_than_four_papers_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {
            "paper_ids": [self.paper1.id, self.paper2.id, self.paper3.id, self.paper4.id, self.paper5.id]
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_paper_ids_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {"paper_ids": [self.paper1.id, self.paper1.id]}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_paper_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {"paper_ids": [self.paper1.id, 999999]}, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["error"])

    def test_unauthorized_paper_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {"paper_ids": [self.paper1.id, self.other_paper.id]}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["error"])

    def test_empty_paper_chunks_represented_safely(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch, MagicMock

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = '{"overall_synthesis": "Synthesis", "similarities": [], "differences": [], "methodology_comparison": [], "findings_comparison": [], "research_gaps": []}'

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):
            resp = self.client.post("/api/ai/compare/", {
                "paper_ids": [self.paper1.id, self.paper3.id]
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["papers"][1]["paper_id"], self.paper3.id)
            self.assertIn("comparison", data)


class MultiPaperSynthesisTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="synthuser", password="password")
        self.project = Project.objects.create(owner=self.user, title="Synth Project")
        self.paper1 = Paper.objects.create(project=self.project, title="Paper Alpha")
        self.paper2 = Paper.objects.create(project=self.project, title="Paper Beta")

        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=5,
            text="Paper Alpha details memory management.",
            embedding=[0.1] * 384,
        )
        self.chunk2 = PaperChunk.objects.create(
            paper=self.paper2,
            chunk_index=0,
            page_number=12,
            text="Paper Beta details virtual memory swapping.",
            embedding=[0.2] * 384,
        )

    def test_parse_multi_paper_synthesis_json(self):
        from ai.services import parse_multi_paper_synthesis_json
        raw_text = f"""```json
{{
    "overall_synthesis": "Both papers discuss memory operating system design.",
    "similarities": [
        {{
            "statement": "Both explore virtual memory.",
            "source_refs": [{{"paper_id": {self.paper1.id}, "chunk_id": {self.chunk1.id}}}]
        }}
    ],
    "differences": [],
    "methodology_comparison": [],
    "findings_comparison": [],
    "research_gaps": []
}}
```"""
        parsed = parse_multi_paper_synthesis_json(raw_text)
        self.assertEqual(parsed["overall_synthesis"], "Both papers discuss memory operating system design.")
        self.assertEqual(len(parsed["similarities"]), 1)
        self.assertEqual(parsed["similarities"][0]["statement"], "Both explore virtual memory.")

    def test_validate_and_resolve_source_refs(self):
        from ai.services import validate_and_resolve_source_refs
        valid_map = {self.chunk1.id: self.chunk1}

        refs = [
            {"paper_id": self.paper1.id, "chunk_id": self.chunk1.id},
            {"paper_id": 9999, "chunk_id": 8888}  # invalid chunk
        ]

        resolved = validate_and_resolve_source_refs(refs, valid_map)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["paper_id"], self.paper1.id)
        self.assertEqual(resolved[0]["paper_title"], "Paper Alpha")
        self.assertEqual(resolved[0]["chunk_id"], self.chunk1.id)
        self.assertEqual(resolved[0]["page_number"], 5)
        self.assertEqual(resolved[0]["text"], "Paper Alpha details memory management.")

    def test_generate_multi_paper_synthesis_single_gemini_call(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_multi_paper_synthesis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = f"""{{
    "overall_synthesis": "Synthesis statement.",
    "similarities": [
        {{
            "statement": "Memory focus.",
            "source_refs": [
                {{"paper_id": {self.paper1.id}, "chunk_id": {self.chunk1.id}}},
                {{"paper_id": {self.paper2.id}, "chunk_id": {self.chunk2.id}}}
            ]
        }}
    ],
    "differences": [],
    "methodology_comparison": [],
    "findings_comparison": [],
    "research_gaps": []
}}"""

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response) as mock_gemini:

            result = generate_multi_paper_synthesis(
                question="Compare memory management",
                papers=[self.paper1, self.paper2],
            )

            # Assert EXACTLY 1 Gemini call was made
            self.assertEqual(mock_gemini.call_count, 1)

            # Assert returned structure
            self.assertEqual(result["question"], "Compare memory management")
            self.assertEqual(len(result["papers"]), 2)
            self.assertEqual(result["comparison"]["overall_synthesis"], "Synthesis statement.")
            
            # Assert DB resolved evidence references
            sim_sources = result["comparison"]["similarities"][0]["sources"]
            self.assertEqual(len(sim_sources), 2)
            self.assertEqual(sim_sources[0]["paper_title"], "Paper Alpha")
            self.assertEqual(sim_sources[0]["page_number"], 5)
            self.assertEqual(sim_sources[1]["paper_title"], "Paper Beta")
            self.assertEqual(sim_sources[1]["page_number"], 12)


class ResearchSessionModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="sessionuser", password="password")
        self.project = Project.objects.create(owner=self.user, title="Persistence Project")
        self.paper1 = Paper.objects.create(project=self.project, title="Paper One")
        self.paper2 = Paper.objects.create(project=self.project, title="Paper Two")
        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=3,
            text="Chunk 1 text",
            embedding=[0.1] * 384,
        )

    def test_research_session_creation_and_papers(self):
        from ai.models import ResearchSession
        session = ResearchSession.objects.create(
            project=self.project,
            title="Analysis of Memory Architectures",
        )
        session.papers.add(self.paper1, self.paper2)

        self.assertEqual(session.project, self.project)
        self.assertEqual(session.title, "Analysis of Memory Architectures")
        self.assertEqual(session.papers.count(), 2)
        self.assertIn(self.paper1, session.papers.all())
        self.assertIn(self.paper2, session.papers.all())

    def test_research_message_roles_and_chronological_ordering(self):
        from ai.models import ResearchSession, ResearchMessage
        session = ResearchSession.objects.create(project=self.project)

        msg1 = ResearchMessage.objects.create(
            session=session,
            role=ResearchMessage.ROLE_USER,
            content="What are the key findings?",
        )
        msg2 = ResearchMessage.objects.create(
            session=session,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="The key findings are memory safety and efficiency.",
        )

        messages = list(session.messages.all())
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)
        self.assertEqual(messages[0].role, "USER")
        self.assertEqual(messages[1].role, "ASSISTANT")

    def test_research_evidence_references(self):
        from ai.models import ResearchSession, ResearchMessage, ResearchEvidence
        session = ResearchSession.objects.create(project=self.project)
        msg = ResearchMessage.objects.create(
            session=session,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="Answer text",
        )

        evidence = ResearchEvidence.objects.create(
            message=msg,
            paper=self.paper1,
            chunk=self.chunk1,
            page_number=3,
            text="Evidence snippet from paper one",
        )

        self.assertEqual(evidence.message, msg)
        self.assertEqual(evidence.paper, self.paper1)
        self.assertEqual(evidence.chunk, self.chunk1)
        self.assertEqual(evidence.page_number, 3)
        self.assertEqual(evidence.text, "Evidence snippet from paper one")

    def test_cascade_deletion_removes_messages_and_evidence(self):
        from ai.models import ResearchSession, ResearchMessage, ResearchEvidence
        session = ResearchSession.objects.create(project=self.project)
        msg = ResearchMessage.objects.create(
            session=session,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="Answer text",
        )
        ResearchEvidence.objects.create(
            message=msg,
            paper=self.paper1,
            chunk=self.chunk1,
            page_number=3,
            text="Snippet",
        )

        self.assertEqual(ResearchSession.objects.count(), 1)
        self.assertEqual(ResearchMessage.objects.count(), 1)
        self.assertEqual(ResearchEvidence.objects.count(), 1)

        # Delete session
        session.delete()

        self.assertEqual(ResearchSession.objects.count(), 0)
        self.assertEqual(ResearchMessage.objects.count(), 0)
        self.assertEqual(ResearchEvidence.objects.count(), 0)


class AskAIPersistenceAPITests(TestCase):

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()

        self.user1 = User.objects.create_user(username="askuser1", password="password")
        self.user2 = User.objects.create_user(username="askuser2", password="password")

        self.proj1 = Project.objects.create(owner=self.user1, title="User1 Project")
        self.proj2 = Project.objects.create(owner=self.user2, title="User2 Project")

        self.paper1 = Paper.objects.create(project=self.proj1, title="Paper 1")
        self.paper_other = Paper.objects.create(project=self.proj2, title="Paper Other")

        from ai.models import PaperChunk, ResearchSession
        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=4,
            text="Operating systems manage hardware resources efficiently.",
            embedding=[0.1] * 384,
        )

        self.session1 = ResearchSession.objects.create(project=self.proj1, title="Session 1")
        self.session_other = ResearchSession.objects.create(project=self.proj2, title="Session Other")

    def test_ask_ai_without_session_id_backward_compatibility(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch, MagicMock
        from ai.models import ResearchMessage, ResearchEvidence

        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = "An operating system manages system resources."
        dummy_query_emb = [0.1] * 384

        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_resp):

            resp = self.client.post("/api/ai/ask/", {
                "paper_id": self.paper1.id,
                "question": "What is an operating system?"
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("answer", data)
            self.assertIn("sources", data)
            self.assertNotIn("session_id", data)

            # Ensure 0 DB session/message records created
            self.assertEqual(ResearchMessage.objects.count(), 0)
            self.assertEqual(ResearchEvidence.objects.count(), 0)

    def test_ask_ai_with_valid_session_id_persists_messages_and_evidence(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch, MagicMock
        from ai.models import ResearchMessage, ResearchEvidence

        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = "Operating systems manage hardware."
        dummy_query_emb = [0.1] * 384

        initial_updated_at = self.session1.updated_at

        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_resp):

            resp = self.client.post("/api/ai/ask/", {
                "paper_id": self.paper1.id,
                "question": "What do operating systems do?",
                "session_id": self.session1.id,
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["session_id"], self.session1.id)

            # Verify USER message
            user_msg = ResearchMessage.objects.get(session=self.session1, role="USER")
            self.assertEqual(user_msg.content, "What do operating systems do?")

            # Verify ASSISTANT message
            assistant_msg = ResearchMessage.objects.get(session=self.session1, role="ASSISTANT")
            self.assertEqual(assistant_msg.content, "Operating systems manage hardware.")

            # Verify evidence record
            evidence_records = list(ResearchEvidence.objects.filter(message=assistant_msg))
            self.assertTrue(len(evidence_records) > 0)
            self.assertEqual(evidence_records[0].paper, self.paper1)
            self.assertEqual(evidence_records[0].chunk, self.chunk1)
            self.assertEqual(evidence_records[0].page_number, 4)
            self.assertIn("Operating systems manage hardware", evidence_records[0].text)

            # Verify updated_at refreshed
            self.session1.refresh_from_db()
            self.assertGreaterEqual(self.session1.updated_at, initial_updated_at)

    def test_ask_ai_invalid_session_id_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/ask/", {
            "paper_id": self.paper1.id,
            "question": "Test question?",
            "session_id": 999999,
        }, format="json")

        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["error"])

    def test_ask_ai_unauthorized_session_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/ask/", {
            "paper_id": self.paper1.id,
            "question": "Test question?",
            "session_id": self.session_other.id,
        }, format="json")

        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["error"])

    def test_ask_ai_paper_from_another_project_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/ask/", {
            "paper_id": self.paper_other.id,
            "question": "Test question?",
            "session_id": self.session1.id,
        }, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("does not belong to this research session", resp.json()["error"])

    def test_ask_ai_gemini_failure_rolls_back_user_message(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        from ai.services import RateLimitError
        from ai.models import ResearchMessage

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("ai.views.generate_ai_answer", side_effect=RateLimitError("Rate limit hit")):

            resp = self.client.post("/api/ai/ask/", {
                "paper_id": self.paper1.id,
                "question": "Failing question?",
                "session_id": self.session1.id,
            }, format="json")

            self.assertEqual(resp.status_code, 429)

            # Atomic transaction rollback check: 0 messages saved for session1
            self.assertEqual(ResearchMessage.objects.filter(session=self.session1).count(), 0)


class ComparePapersPersistenceAPITests(TestCase):

    def setUp(self):
        from rest_framework.test import APIClient
        from ai.models import PaperChunk, ResearchSession

        self.client = APIClient()
        self.user1 = User.objects.create_user(username="compare_user1", password="password")
        self.user2 = User.objects.create_user(username="compare_user2", password="password")

        self.proj1 = Project.objects.create(owner=self.user1, title="Project 1")
        self.proj1_other = Project.objects.create(owner=self.user1, title="Project 1 Other")
        self.proj2 = Project.objects.create(owner=self.user2, title="Project 2")

        self.paper1 = Paper.objects.create(project=self.proj1, title="Paper 1")
        self.paper2 = Paper.objects.create(project=self.proj1, title="Paper 2")
        self.paper_other_proj = Paper.objects.create(project=self.proj1_other, title="Paper in Proj 1 Other")
        self.paper_user2 = Paper.objects.create(project=self.proj2, title="Paper User 2")

        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=3,
            text="Memory management architecture in paper 1.",
            embedding=[0.1] * 384,
        )
        self.chunk2 = PaperChunk.objects.create(
            paper=self.paper2,
            chunk_index=0,
            page_number=7,
            text="Distributed consensus protocols in paper 2.",
            embedding=[0.2] * 384,
        )

        self.session1 = ResearchSession.objects.create(project=self.proj1, title="Session 1")
        self.session_user2 = ResearchSession.objects.create(project=self.proj2, title="Session User 2")

    def test_compare_without_session_id_backward_compatibility(self):
        self.client.force_authenticate(user=self.user1)
        import json
        from unittest.mock import patch, MagicMock
        from ai.models import ResearchMessage, ResearchEvidence

        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = json.dumps({
            "overall_synthesis": "Both papers discuss system architecture.",
            "similarities": [],
            "differences": [],
            "methodology_comparison": [],
            "findings_comparison": [],
            "research_gaps": [],
        })
        dummy_query_emb = [0.1] * 384

        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_resp):

            resp = self.client.post("/api/ai/compare/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "Compare system architectures",
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("comparison", data)
            self.assertIn("overall_synthesis", data["comparison"])
            self.assertNotIn("session_id", data)

            # Ensure no session message or evidence records created
            self.assertEqual(ResearchMessage.objects.count(), 0)
            self.assertEqual(ResearchEvidence.objects.count(), 0)

    def test_compare_with_valid_session_id_persists_messages_and_evidence(self):
        self.client.force_authenticate(user=self.user1)
        import json
        from unittest.mock import patch, MagicMock
        from ai.models import ResearchMessage, ResearchEvidence

        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = json.dumps({
            "overall_synthesis": "Both papers examine scalable systems.",
            "similarities": [
                {
                    "statement": "Both use distributed structures.",
                    "source_refs": [
                        {"paper_id": self.paper1.id, "chunk_id": self.chunk1.id},
                    ]
                }
            ],
            "differences": [
                {
                    "statement": "Paper 2 focuses on consensus.",
                    "source_refs": [
                        {"paper_id": self.paper2.id, "chunk_id": self.chunk2.id},
                    ]
                }
            ],
            "methodology_comparison": [
                {
                    "paper_id": self.paper1.id,
                    "summary": "Paper 1 uses memory benchmarks.",
                    "source_refs": [
                        {"paper_id": self.paper1.id, "chunk_id": self.chunk1.id},
                    ]
                }
            ],
            "findings_comparison": [],
            "research_gaps": [],
        })
        dummy_query_emb = [0.1] * 384
        initial_updated_at = self.session1.updated_at

        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_resp):

            resp = self.client.post("/api/ai/compare/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "Compare the core architectures",
                "session_id": self.session1.id,
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["session_id"], self.session1.id)
            self.assertIn("comparison", data)
            self.assertEqual(data["question"], "Compare the core architectures")

            # 3. USER ResearchMessage is created
            user_msg = ResearchMessage.objects.get(session=self.session1, role="USER")
            # 5. Effective question stored
            self.assertEqual(user_msg.content, "Compare the core architectures")

            # 4. ASSISTANT ResearchMessage is created
            assistant_msg = ResearchMessage.objects.get(session=self.session1, role="ASSISTANT")

            # 6. Structured comparison JSON is stored
            stored_comp = json.loads(assistant_msg.content)
            self.assertEqual(stored_comp["overall_synthesis"], "Both papers examine scalable systems.")
            self.assertEqual(len(stored_comp["similarities"]), 1)
            self.assertEqual(len(stored_comp["differences"]), 1)
            self.assertEqual(len(stored_comp["methodology_comparison"]), 1)

            # 7. Evidence records are created
            evidence_records = list(ResearchEvidence.objects.filter(message=assistant_msg).order_by("id"))
            # chunk1 appeared in similarities and methodology_comparison, chunk2 appeared in differences.
            # 12. Duplicate evidence sources are stored only once: exactly 2 evidence records!
            self.assertEqual(len(evidence_records), 2)

            # 8, 9, 10, 11: Correct paper, chunk, page_number, text
            ev1 = evidence_records[0]
            self.assertEqual(ev1.paper, self.paper1)
            self.assertEqual(ev1.chunk, self.chunk1)
            self.assertEqual(ev1.page_number, 3)
            self.assertEqual(ev1.text, "Memory management architecture in paper 1.")

            ev2 = evidence_records[1]
            self.assertEqual(ev2.paper, self.paper2)
            self.assertEqual(ev2.chunk, self.chunk2)
            self.assertEqual(ev2.page_number, 7)
            self.assertEqual(ev2.text, "Distributed consensus protocols in paper 2.")

            # 10. Session updated_at refreshed
            self.session1.refresh_from_db()
            self.assertGreaterEqual(self.session1.updated_at, initial_updated_at)

    def test_compare_with_empty_question_stores_effective_question(self):
        self.client.force_authenticate(user=self.user1)
        import json
        from unittest.mock import patch, MagicMock
        from ai.models import ResearchMessage

        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = json.dumps({
            "overall_synthesis": "Default comparison summary.",
            "similarities": [],
            "differences": [],
            "methodology_comparison": [],
            "findings_comparison": [],
            "research_gaps": [],
        })
        dummy_query_emb = [0.1] * 384

        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_resp):

            resp = self.client.post("/api/ai/compare/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "",
                "session_id": self.session1.id,
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            user_msg = ResearchMessage.objects.get(session=self.session1, role="USER")
            self.assertEqual(user_msg.content, "main findings methodology limitations research gaps")

    def test_compare_duplicate_evidence_stored_only_once(self):
        self.client.force_authenticate(user=self.user1)
        import json
        from unittest.mock import patch, MagicMock
        from ai.models import ResearchMessage, ResearchEvidence

        # Same chunk1 referenced across multiple sections
        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = json.dumps({
            "overall_synthesis": "Synthesis",
            "similarities": [
                {"statement": "Sim 1", "source_refs": [{"paper_id": self.paper1.id, "chunk_id": self.chunk1.id}]},
                {"statement": "Sim 2", "source_refs": [{"paper_id": self.paper1.id, "chunk_id": self.chunk1.id}]},
            ],
            "differences": [
                {"statement": "Diff 1", "source_refs": [{"paper_id": self.paper1.id, "chunk_id": self.chunk1.id}]},
            ],
            "methodology_comparison": [
                {"paper_id": self.paper1.id, "summary": "Meth 1", "source_refs": [{"paper_id": self.paper1.id, "chunk_id": self.chunk1.id}]},
            ],
            "findings_comparison": [
                {"paper_id": self.paper1.id, "summary": "Find 1", "source_refs": [{"paper_id": self.paper1.id, "chunk_id": self.chunk1.id}]},
            ],
            "research_gaps": [
                {"statement": "Gap 1", "type": "explicit", "source_refs": [{"paper_id": self.paper1.id, "chunk_id": self.chunk1.id}]},
            ],
        })
        dummy_query_emb = [0.1] * 384

        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_resp):

            resp = self.client.post("/api/ai/compare/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "Check deduplication",
                "session_id": self.session1.id,
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            assistant_msg = ResearchMessage.objects.get(session=self.session1, role="ASSISTANT")
            evidence_count = ResearchEvidence.objects.filter(message=assistant_msg).count()
            self.assertEqual(evidence_count, 1)

    def test_compare_invalid_session_id_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {
            "paper_ids": [self.paper1.id, self.paper2.id],
            "question": "Question?",
            "session_id": 999999,
        }, format="json")

        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["error"])

    def test_compare_unauthorized_session_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {
            "paper_ids": [self.paper1.id, self.paper2.id],
            "question": "Question?",
            "session_id": self.session_user2.id,
        }, format="json")

        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["error"])

    def test_compare_paper_outside_session_project_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/compare/", {
            "paper_ids": [self.paper1.id, self.paper_other_proj.id],
            "question": "Question?",
            "session_id": self.session1.id,
        }, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("do not belong to this research session", resp.json()["error"])

    def test_compare_gemini_failure_rolls_back_user_message_and_evidence(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        from ai.services import RateLimitError
        from ai.models import ResearchMessage, ResearchEvidence

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("ai.views.generate_multi_paper_synthesis", side_effect=RateLimitError("Rate limit hit")):

            resp = self.client.post("/api/ai/compare/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "Will it fail?",
                "session_id": self.session1.id,
            }, format="json")

            self.assertEqual(resp.status_code, 429)

            # Atomic transaction rollback check: 0 messages, 0 evidence saved
            self.assertEqual(ResearchMessage.objects.filter(session=self.session1).count(), 0)
            self.assertEqual(ResearchEvidence.objects.count(), 0)


class ResearchSessionRESTAPITests(TestCase):

    def setUp(self):
        from rest_framework.test import APIClient
        from ai.models import ResearchSession, PaperChunk

        self.client = APIClient()
        self.user1 = User.objects.create_user(username="session_user1", password="password")
        self.user2 = User.objects.create_user(username="session_user2", password="password")

        self.proj1 = Project.objects.create(owner=self.user1, title="User1 Project")
        self.proj2 = Project.objects.create(owner=self.user2, title="User2 Project")

        self.paper1 = Paper.objects.create(project=self.proj1, title="Paper A")
        self.paper2 = Paper.objects.create(project=self.proj1, title="Paper B")

        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=5,
            text="Evidence excerpt text from Paper A.",
            embedding=[0.1] * 384,
        )

    def test_create_session_with_default_title(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        resp = self.client.post("/api/ai/sessions/", {
            "project_id": self.proj1.id,
        }, format="json")

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["project_id"], self.proj1.id)
        self.assertEqual(data["title"], "Research Session")
        self.assertEqual(data["papers"], [])
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)
        self.assertTrue(ResearchSession.objects.filter(id=data["id"]).exists())

    def test_create_session_with_custom_title(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/sessions/", {
            "project_id": self.proj1.id,
            "title": "Literature Review"
        }, format="json")

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["title"], "Literature Review")

    def test_create_session_unauthorized_project_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/sessions/", {
            "project_id": self.proj2.id,
            "title": "Unauthorized Session"
        }, format="json")

        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["error"])

    def test_create_session_missing_project_id_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/sessions/", {
            "title": "No Project ID"
        }, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("project_id", resp.json()["error"])

    def test_create_session_nonexistent_project_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/sessions/", {
            "project_id": 999999,
            "title": "Nonexistent Project"
        }, format="json")

        self.assertEqual(resp.status_code, 404)
        self.assertIn("Project not found", resp.json()["error"])

    def test_list_sessions_missing_project_id_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.get("/api/ai/sessions/")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("project_id", resp.json()["error"])

    def test_list_sessions_nonexistent_project_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.get("/api/ai/sessions/?project_id=999999")
        self.assertEqual(resp.status_code, 404)

    def test_list_sessions_unauthorized_project_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.get(f"/api/ai/sessions/?project_id={self.proj2.id}")
        self.assertEqual(resp.status_code, 403)

    def test_list_sessions_success_ordered_by_updated_at_descending(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession
        from django.utils import timezone
        import datetime

        s1 = ResearchSession.objects.create(project=self.proj1, title="Session 1")
        s2 = ResearchSession.objects.create(project=self.proj1, title="Session 2")
        # Touch s1 so updated_at is later
        ResearchSession.objects.filter(id=s1.id).update(updated_at=timezone.now() + datetime.timedelta(seconds=10))

        resp = self.client.get(f"/api/ai/sessions/?project_id={self.proj1.id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        # s1 should be first because of later updated_at
        self.assertEqual(data[0]["id"], s1.id)
        self.assertEqual(data[1]["id"], s2.id)

    def test_retrieve_session_chronological_messages_and_evidence(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession, ResearchMessage, ResearchEvidence

        session = ResearchSession.objects.create(project=self.proj1, title="Literature Review")
        session.papers.add(self.paper1)

        msg1 = ResearchMessage.objects.create(
            session=session,
            role="USER",
            content="What methodology does this paper use?",
        )
        msg2 = ResearchMessage.objects.create(
            session=session,
            role="ASSISTANT",
            content="The paper uses a transformer architecture.",
        )
        ev1 = ResearchEvidence.objects.create(
            message=msg2,
            paper=self.paper1,
            chunk=self.chunk1,
            page_number=5,
            text="Evidence excerpt text from Paper A.",
        )

        resp = self.client.get(f"/api/ai/sessions/{session.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], session.id)
        self.assertEqual(data["title"], "Literature Review")
        self.assertEqual(len(data["papers"]), 1)
        self.assertEqual(data["papers"][0]["id"], self.paper1.id)
        self.assertEqual(data["papers"][0]["title"], self.paper1.title)

        # Messages: chronological order
        self.assertEqual(len(data["messages"]), 2)
        self.assertEqual(data["messages"][0]["id"], msg1.id)
        self.assertEqual(data["messages"][0]["role"], "USER")
        self.assertEqual(data["messages"][0]["content"], "What methodology does this paper use?")

        self.assertEqual(data["messages"][1]["id"], msg2.id)
        self.assertEqual(data["messages"][1]["role"], "ASSISTANT")
        self.assertEqual(len(data["messages"][1]["evidence"]), 1)

        evidence_data = data["messages"][1]["evidence"][0]
        self.assertEqual(evidence_data["id"], ev1.id)
        self.assertEqual(evidence_data["paper_id"], self.paper1.id)
        self.assertEqual(evidence_data["paper_title"], self.paper1.title)
        self.assertEqual(evidence_data["chunk_id"], self.chunk1.id)
        self.assertEqual(evidence_data["page_number"], 5)
        self.assertEqual(evidence_data["text"], "Evidence excerpt text from Paper A.")

    def test_retrieve_session_preserves_structured_comparison_json(self):
        self.client.force_authenticate(user=self.user1)
        import json
        from ai.models import ResearchSession, ResearchMessage

        comparison_payload = {
            "overall_synthesis": "Synthesis statement.",
            "similarities": [{"statement": "Sim 1", "sources": []}],
            "differences": [{"statement": "Diff 1", "sources": []}],
            "methodology_comparison": [],
            "findings_comparison": [],
            "research_gaps": [],
        }
        json_content = json.dumps(comparison_payload)

        session = ResearchSession.objects.create(project=self.proj1, title="Compare Session")
        ResearchMessage.objects.create(session=session, role="USER", content="Compare papers")
        ResearchMessage.objects.create(session=session, role="ASSISTANT", content=json_content)

        resp = self.client.get(f"/api/ai/sessions/{session.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        assistant_content = data["messages"][1]["content"]
        self.assertEqual(assistant_content, json_content)
        parsed = json.loads(assistant_content)
        self.assertEqual(parsed["overall_synthesis"], "Synthesis statement.")

    def test_retrieve_session_unauthorized_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session_other = ResearchSession.objects.create(project=self.proj2, title="Other Session")
        resp = self.client.get(f"/api/ai/sessions/{session_other.id}/")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["error"])

    def test_retrieve_session_not_found_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.get("/api/ai/sessions/999999/")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["error"])

    def test_update_session_title(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session = ResearchSession.objects.create(project=self.proj1, title="Original Title")
        resp = self.client.patch(f"/api/ai/sessions/{session.id}/", {
            "title": "Final Literature Review",
            "project_id": self.proj2.id,
        }, format="json")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["title"], "Final Literature Review")
        session.refresh_from_db()
        self.assertEqual(session.title, "Final Literature Review")
        self.assertEqual(session.project, self.proj1)

    def test_update_session_unauthorized_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session_other = ResearchSession.objects.create(project=self.proj2, title="Other Title")
        resp = self.client.patch(f"/api/ai/sessions/{session_other.id}/", {
            "title": "Hacked Title"
        }, format="json")

        self.assertEqual(resp.status_code, 403)
        session_other.refresh_from_db()
        self.assertEqual(session_other.title, "Other Title")

    def test_delete_session_cascades_messages_and_evidence(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession, ResearchMessage, ResearchEvidence

        session = ResearchSession.objects.create(project=self.proj1, title="To Delete")
        msg = ResearchMessage.objects.create(session=session, role="ASSISTANT", content="Answer")
        ev = ResearchEvidence.objects.create(
            message=msg,
            paper=self.paper1,
            chunk=self.chunk1,
            page_number=5,
            text="Evidence",
        )

        resp = self.client.delete(f"/api/ai/sessions/{session.id}/")
        self.assertEqual(resp.status_code, 204)

        # Verify session deleted
        self.assertFalse(ResearchSession.objects.filter(id=session.id).exists())
        # Verify cascaded deletion of messages and evidence
        self.assertFalse(ResearchMessage.objects.filter(id=msg.id).exists())
        self.assertFalse(ResearchEvidence.objects.filter(id=ev.id).exists())

        # Verify parent models (Project, Paper, PaperChunk) are NOT deleted
        self.assertTrue(Project.objects.filter(id=self.proj1.id).exists())
        self.assertTrue(Paper.objects.filter(id=self.paper1.id).exists())
        self.assertTrue(self.chunk1.__class__.objects.filter(id=self.chunk1.id).exists())

    def test_delete_session_unauthorized_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session_other = ResearchSession.objects.create(project=self.proj2, title="Other Delete")
        resp = self.client.delete(f"/api/ai/sessions/{session_other.id}/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ResearchSession.objects.filter(id=session_other.id).exists())

    def test_update_session_papers_success(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session = ResearchSession.objects.create(project=self.proj1, title="Session Papers Test")
        self.assertEqual(session.papers.count(), 0)

        resp = self.client.patch(f"/api/ai/sessions/{session.id}/", {
            "papers": [self.paper1.id, self.paper2.id]
        }, format="json")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["papers"]), 2)
        returned_ids = [p["id"] for p in data["papers"]]
        self.assertIn(self.paper1.id, returned_ids)
        self.assertIn(self.paper2.id, returned_ids)

        session.refresh_from_db()
        self.assertEqual(session.papers.count(), 2)

    def test_update_session_papers_empty_list(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session = ResearchSession.objects.create(project=self.proj1, title="Session Clear Papers")
        session.papers.add(self.paper1)
        self.assertEqual(session.papers.count(), 1)

        resp = self.client.patch(f"/api/ai/sessions/{session.id}/", {
            "papers": []
        }, format="json")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["papers"]), 0)

        session.refresh_from_db()
        self.assertEqual(session.papers.count(), 0)

    def test_update_session_papers_invalid_id(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session = ResearchSession.objects.create(project=self.proj1, title="Session Invalid Paper")
        resp = self.client.patch(f"/api/ai/sessions/{session.id}/", {
            "papers": [self.paper1.id, 999999]
        }, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("invalid or do not belong to this project", resp.json()["error"])

    def test_update_session_papers_different_project(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        other_proj_paper = Paper.objects.create(project=self.proj2, title="Other Project Paper")
        session = ResearchSession.objects.create(project=self.proj1, title="Session Foreign Paper")
        resp = self.client.patch(f"/api/ai/sessions/{session.id}/", {
            "papers": [other_proj_paper.id]
        }, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("invalid or do not belong to this project", resp.json()["error"])

    def test_update_session_papers_invalid_type(self):
        self.client.force_authenticate(user=self.user1)
        from ai.models import ResearchSession

        session = ResearchSession.objects.create(project=self.proj1, title="Session Bad Type")
        resp = self.client.patch(f"/api/ai/sessions/{session.id}/", {
            "papers": "not-a-list"
        }, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("must be a list", resp.json()["error"])


class ResearchGapAnalysisServiceTests(TestCase):
    """
    Focused tests for Phase 7.1.1: Research Gap Analysis backend service.
    Verifies structured schema, multi-paper retrieval reuse, single Gemini call,
    parsing robustness, source reference resolution, page number preservation,
    and boundary handling.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="gap_user", password="password")
        self.project = Project.objects.create(owner=self.user, title="Gap Analysis Project")

        self.paper1 = Paper.objects.create(project=self.project, title="Paper Alpha")
        self.paper2 = Paper.objects.create(project=self.project, title="Paper Beta")
        self.paper3 = Paper.objects.create(project=self.project, title="Paper Gamma")
        self.paper4 = Paper.objects.create(project=self.project, title="Paper Delta")

        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=5,
            text="Paper Alpha has sample size limitations and small cohort.",
            embedding=[0.1] * 384,
        )
        self.chunk2 = PaperChunk.objects.create(
            paper=self.paper2,
            chunk_index=0,
            page_number=12,
            text="Paper Beta lacks longitudinal evaluation and tracking.",
            embedding=[0.1] * 384,
        )
        self.chunk3 = PaperChunk.objects.create(
            paper=self.paper3,
            chunk_index=0,
            page_number=20,
            text="Paper Gamma dataset only covers US cohort demographics.",
            embedding=[0.1] * 384,
        )
        self.chunk4 = PaperChunk.objects.create(
            paper=self.paper4,
            chunk_index=0,
            page_number=8,
            text="Paper Delta contradicts Alpha regarding algorithm convergence speed.",
            embedding=[0.1] * 384,
        )

    def test_valid_structured_gap_analysis_response(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = f"""{{
            "overall_assessment": "Comprehensive gap assessment across 3 papers.",
            "common_limitations": [
                {{
                    "statement": "Sample size is small.",
                    "source_refs": [{{"paper_id": {self.paper1.id}, "chunk_id": {self.chunk1.id}}}]
                }}
            ],
            "methodological_gaps": [
                {{
                    "statement": "No longitudinal tracking.",
                    "source_refs": [{{"paper_id": {self.paper2.id}, "chunk_id": {self.chunk2.id}}}]
                }}
            ],
            "dataset_population_gaps": [
                {{
                    "statement": "Demographics limited to US cohort.",
                    "source_refs": [{{"paper_id": {self.paper3.id}, "chunk_id": {self.chunk3.id}}}]
                }}
            ],
            "understudied_areas": [
                {{
                    "statement": "Low resource environments understudied.",
                    "source_refs": [{{"paper_id": {self.paper1.id}, "chunk_id": {self.chunk1.id}}}]
                }}
            ],
            "contradictions_inconsistencies": [
                {{
                    "statement": "Discrepancy in convergence findings.",
                    "source_refs": [
                        {{"paper_id": {self.paper1.id}, "chunk_id": {self.chunk1.id}}},
                        {{"paper_id": {self.paper2.id}, "chunk_id": {self.chunk2.id}}}
                    ]
                }}
            ],
            "unanswered_research_questions": [
                {{
                    "question": "How does this method scale to 10M parameters?",
                    "source_refs": [{{"paper_id": {self.paper2.id}, "chunk_id": {self.chunk2.id}}}]
                }}
            ],
            "future_research_directions": [
                {{
                    "direction": "Test against cross-continental datasets.",
                    "source_refs": [{{"paper_id": {self.paper3.id}, "chunk_id": {self.chunk3.id}}}]
                }}
            ]
        }}"""

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response) as mock_gemini:

            result = generate_research_gap_analysis(
                question="Identify research gaps and limitations",
                papers=[self.paper1, self.paper2, self.paper3],
            )

            self.assertEqual(mock_gemini.call_count, 1)
            self.assertIn("gap_analysis", result)
            gap = result["gap_analysis"]

            self.assertEqual(gap["overall_assessment"], "Comprehensive gap assessment across 3 papers.")
            self.assertEqual(len(gap["common_limitations"]), 1)
            self.assertEqual(gap["common_limitations"][0]["statement"], "Sample size is small.")
            self.assertEqual(len(gap["common_limitations"][0]["sources"]), 1)
            self.assertEqual(gap["common_limitations"][0]["sources"][0]["chunk_id"], self.chunk1.id)
            self.assertEqual(gap["common_limitations"][0]["sources"][0]["page_number"], 5)

            self.assertEqual(len(gap["methodological_gaps"]), 1)
            self.assertEqual(len(gap["dataset_population_gaps"]), 1)
            self.assertEqual(len(gap["understudied_areas"]), 1)
            self.assertEqual(len(gap["contradictions_inconsistencies"]), 1)
            self.assertEqual(len(gap["unanswered_research_questions"]), 1)
            self.assertEqual(gap["unanswered_research_questions"][0]["question"], "How does this method scale to 10M parameters?")
            self.assertEqual(len(gap["future_research_directions"]), 1)
            self.assertEqual(gap["future_research_directions"][0]["direction"], "Test against cross-continental datasets.")

    def test_malformed_gemini_json_graceful_fallback(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = "This is not valid json! {broken"

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):

            result = generate_research_gap_analysis(
                question="Analyze gaps",
                papers=[self.paper1, self.paper2],
            )

            gap = result["gap_analysis"]
            self.assertEqual(gap["overall_assessment"], "Assessment unavailable based on the provided evidence.")
            self.assertEqual(gap["common_limitations"], [])
            self.assertEqual(gap["methodological_gaps"], [])
            self.assertEqual(gap["dataset_population_gaps"], [])
            self.assertEqual(gap["understudied_areas"], [])
            self.assertEqual(gap["contradictions_inconsistencies"], [])
            self.assertEqual(gap["unanswered_research_questions"], [])
            self.assertEqual(gap["future_research_directions"], [])

    def test_missing_optional_sections_normalized(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = """{
            "overall_assessment": "Partial assessment.",
            "common_limitations": [
                {
                    "statement": "Hardware constraints.",
                    "source_refs": []
                }
            ]
        }"""

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):

            result = generate_research_gap_analysis(
                question="Gaps",
                papers=[self.paper1, self.paper2],
            )

            gap = result["gap_analysis"]
            self.assertEqual(gap["overall_assessment"], "Partial assessment.")
            self.assertEqual(len(gap["common_limitations"]), 1)
            self.assertEqual(gap["methodological_gaps"], [])
            self.assertEqual(gap["dataset_population_gaps"], [])
            self.assertEqual(gap["understudied_areas"], [])
            self.assertEqual(gap["contradictions_inconsistencies"], [])
            self.assertEqual(gap["unanswered_research_questions"], [])
            self.assertEqual(gap["future_research_directions"], [])

    def test_invalid_source_references_filtered_out(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = f"""{{
            "overall_assessment": "Gaps with fabricated chunk ids.",
            "common_limitations": [
                {{
                    "statement": "Fabricated chunk test.",
                    "source_refs": [
                        {{"paper_id": {self.paper1.id}, "chunk_id": 999999}},
                        {{"paper_id": {self.paper1.id}, "chunk_id": {self.chunk1.id}}}
                    ]
                }}
            ],
            "methodological_gaps": [],
            "dataset_population_gaps": [],
            "understudied_areas": [],
            "contradictions_inconsistencies": [],
            "unanswered_research_questions": [],
            "future_research_directions": []
        }}"""

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):

            result = generate_research_gap_analysis(
                question="Gaps",
                papers=[self.paper1, self.paper2],
            )

            sources = result["gap_analysis"]["common_limitations"][0]["sources"]
            # 999999 should be filtered out, only chunk1 should remain
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0]["chunk_id"], self.chunk1.id)

    def test_cross_paper_unretrieved_source_references(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        # Paper 4 has chunk 4, but we only analyze paper 1 and paper 2
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = f"""{{
            "overall_assessment": "Cross paper invalid ref test.",
            "common_limitations": [
                {{
                    "statement": "Mismatched paper and unretrieved chunk.",
                    "source_refs": [
                        {{"paper_id": {self.paper2.id}, "chunk_id": {self.chunk1.id}}},
                        {{"paper_id": {self.paper4.id}, "chunk_id": {self.chunk4.id}}}
                    ]
                }}
            ],
            "methodological_gaps": [],
            "dataset_population_gaps": [],
            "understudied_areas": [],
            "contradictions_inconsistencies": [],
            "unanswered_research_questions": [],
            "future_research_directions": []
        }}"""

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):

            result = generate_research_gap_analysis(
                question="Gaps",
                papers=[self.paper1, self.paper2],
            )

            sources = result["gap_analysis"]["common_limitations"][0]["sources"]
            # chunk1 belongs to paper1, but ref specified paper2 -> filtered out
            # chunk4 belongs to paper4, which was not retrieved -> filtered out
            self.assertEqual(len(sources), 0)

    def test_page_number_preservation(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = f"""{{
            "overall_assessment": "Page check.",
            "common_limitations": [
                {{
                    "statement": "Page verification.",
                    "source_refs": [
                        {{"paper_id": {self.paper1.id}, "chunk_id": {self.chunk1.id}}},
                        {{"paper_id": {self.paper2.id}, "chunk_id": {self.chunk2.id}}}
                    ]
                }}
            ],
            "methodological_gaps": [],
            "dataset_population_gaps": [],
            "understudied_areas": [],
            "contradictions_inconsistencies": [],
            "unanswered_research_questions": [],
            "future_research_directions": []
        }}"""

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):

            result = generate_research_gap_analysis(
                question="Gaps",
                papers=[self.paper1, self.paper2],
            )

            sources = result["gap_analysis"]["common_limitations"][0]["sources"]
            self.assertEqual(len(sources), 2)
            self.assertEqual(sources[0]["page_number"], 5)
            self.assertEqual(sources[1]["page_number"], 12)

    def test_one_gemini_synthesis_call_only(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = '{"overall_assessment": "One call."}'

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response) as mock_gemini:

            generate_research_gap_analysis(
                question="Analyze gaps",
                papers=[self.paper1, self.paper2],
            )

            self.assertEqual(mock_gemini.call_count, 1)

    def test_two_paper_analysis_boundary(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = '{"overall_assessment": "Two papers evaluated."}'

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):

            result = generate_research_gap_analysis(
                question="Analyze gaps",
                papers=[self.paper1, self.paper2],
            )

            self.assertEqual(len(result["papers"]), 2)
            self.assertEqual(result["gap_analysis"]["overall_assessment"], "Two papers evaluated.")

    def test_four_paper_analysis_boundary(self):
        from unittest.mock import patch, MagicMock
        from ai.services import generate_research_gap_analysis

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = '{"overall_assessment": "Four papers evaluated."}'

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini", return_value=mock_gemini_response):

            result = generate_research_gap_analysis(
                question="Analyze gaps",
                papers=[self.paper1, self.paper2, self.paper3, self.paper4],
            )

            self.assertEqual(len(result["papers"]), 4)
            self.assertEqual(result["gap_analysis"]["overall_assessment"], "Four papers evaluated.")

    def test_empty_retrieval_evidence_behavior(self):
        from unittest.mock import patch
        from ai.services import generate_research_gap_analysis

        empty_paper_a = Paper.objects.create(project=self.project, title="Empty Paper A")
        empty_paper_b = Paper.objects.create(project=self.project, title="Empty Paper B")

        dummy_query_emb = [0.1] * 384
        with patch("ai.services.generate_embedding", return_value=dummy_query_emb), \
             patch("os.getenv", return_value="fake-api-key"), \
             patch("ai.services._call_gemini") as mock_gemini:

            result = generate_research_gap_analysis(
                question="Analyze gaps",
                papers=[empty_paper_a, empty_paper_b],
            )

            # Gemini must NOT be called when chunks are empty
            self.assertEqual(mock_gemini.call_count, 0)
            self.assertIn("Insufficient text content", result["gap_analysis"]["overall_assessment"])
            self.assertEqual(result["gap_analysis"]["common_limitations"], [])
            self.assertEqual(result["gap_analysis"]["methodological_gaps"], [])

    def test_paper_count_validation(self):
        from ai.services import generate_research_gap_analysis

        # 1 paper: invalid
        with self.assertRaises(ValueError) as ctx:
            generate_research_gap_analysis("Gaps", [self.paper1])
        self.assertIn("requires between 2 and 4 papers", str(ctx.exception))

        # 5 papers: invalid
        paper5 = Paper.objects.create(project=self.project, title="Paper Epsilon")
        with self.assertRaises(ValueError) as ctx:
            generate_research_gap_analysis("Gaps", [self.paper1, self.paper2, self.paper3, self.paper4, paper5])
        self.assertIn("requires between 2 and 4 papers", str(ctx.exception))

        # Non-paper item: invalid
        with self.assertRaises(ValueError) as ctx:
            generate_research_gap_analysis("Gaps", [self.paper1, "invalid_paper"])
        self.assertIn("must be a valid Paper instance", str(ctx.exception))

    def test_parse_research_gap_analysis_json_code_fences(self):
        from ai.services import parse_research_gap_analysis_json

        fenced_input = """```json
        {
            "overall_assessment": "Fenced analysis.",
            "common_limitations": [{"statement": "Fenced limitation"}]
        }
        ```"""
        parsed = parse_research_gap_analysis_json(fenced_input)
        self.assertEqual(parsed["overall_assessment"], "Fenced analysis.")
        self.assertEqual(len(parsed["common_limitations"]), 1)


class ResearchGapAnalysisAPITests(TestCase):
    """
    Focused API tests for Phase 7.1.2: Research Gap Analysis REST API endpoint
    POST /api/ai/gap-analysis/
    Verifies authentication, paper bounds, duplicates, ownership, cross-project checks,
    optional session validation, non-persistence, default questions, and error handling.
    """

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()

        self.user1 = User.objects.create_user(username="gap_api_user1", password="password")
        self.user2 = User.objects.create_user(username="gap_api_user2", password="password")

        self.proj1 = Project.objects.create(owner=self.user1, title="User1 Project")
        self.proj2 = Project.objects.create(owner=self.user2, title="User2 Project")

        self.paper1 = Paper.objects.create(project=self.proj1, title="Paper Alpha")
        self.paper2 = Paper.objects.create(project=self.proj1, title="Paper Beta")
        self.paper3 = Paper.objects.create(project=self.proj1, title="Paper Gamma")
        self.paper4 = Paper.objects.create(project=self.proj1, title="Paper Delta")
        self.paper5 = Paper.objects.create(project=self.proj1, title="Paper Epsilon")

        self.other_paper = Paper.objects.create(project=self.proj2, title="Other User Paper")

        self.session1 = ResearchSession.objects.create(project=self.proj1, title="Session 1")
        self.session2 = ResearchSession.objects.create(project=self.proj2, title="Session 2")

        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=3,
            text="Paper Alpha chunk text",
            embedding=[0.1] * 384
        )
        self.chunk2 = PaperChunk.objects.create(
            paper=self.paper2,
            chunk_index=0,
            page_number=7,
            text="Paper Beta chunk text",
            embedding=[0.2] * 384
        )

        self.mock_gap_response = {
            "question": "What research gaps exist across these papers?",
            "papers": [
                {"paper_id": self.paper1.id, "title": self.paper1.title},
                {"paper_id": self.paper2.id, "title": self.paper2.title}
            ],
            "gap_analysis": {
                "overall_assessment": "Grounded research gaps across papers.",
                "common_limitations": [
                    {"statement": "Limited sample size.", "sources": []}
                ],
                "methodological_gaps": [],
                "dataset_population_gaps": [],
                "understudied_areas": [],
                "contradictions_inconsistencies": [],
                "unanswered_research_questions": [],
                "future_research_directions": []
            }
        }

    def test_successful_2_paper_analysis(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch

        with patch("ai.views.generate_research_gap_analysis", return_value=self.mock_gap_response):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "What research gaps exist across these papers?"
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(len(data["papers"]), 2)
            self.assertEqual(data["gap_analysis"]["overall_assessment"], "Grounded research gaps across papers.")
            self.assertEqual(data["question"], "What research gaps exist across these papers?")

    def test_successful_4_paper_analysis(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch

        four_paper_resp = {
            "question": "Analyze gaps",
            "papers": [
                {"paper_id": self.paper1.id, "title": self.paper1.title},
                {"paper_id": self.paper2.id, "title": self.paper2.title},
                {"paper_id": self.paper3.id, "title": self.paper3.title},
                {"paper_id": self.paper4.id, "title": self.paper4.title},
            ],
            "gap_analysis": {"overall_assessment": "Four papers evaluated."}
        }

        with patch("ai.views.generate_research_gap_analysis", return_value=four_paper_resp):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id, self.paper3.id, self.paper4.id]
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.json()["papers"]), 4)

    def test_missing_paper_ids_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/gap-analysis/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BAD_REQUEST")

    def test_paper_ids_not_a_list_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/gap-analysis/", {"paper_ids": "not-a-list"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BAD_REQUEST")

    def test_fewer_than_2_papers_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp_empty = self.client.post("/api/ai/gap-analysis/", {"paper_ids": []}, format="json")
        self.assertEqual(resp_empty.status_code, 400)

        resp_single = self.client.post("/api/ai/gap-analysis/", {"paper_ids": [self.paper1.id]}, format="json")
        self.assertEqual(resp_single.status_code, 400)
        self.assertIn("requires between 2 and 4 papers", resp_single.json()["error"])

    def test_more_than_4_papers_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, self.paper2.id, self.paper3.id, self.paper4.id, self.paper5.id]
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("requires between 2 and 4 papers", resp.json()["error"])

    def test_duplicate_paper_ids_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, self.paper1.id]
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Duplicate paper IDs", resp.json()["error"])

    def test_paper_ids_non_integer_elements_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        resp_str = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, "string_id"]
        }, format="json")
        self.assertEqual(resp_str.status_code, 400)

        resp_bool = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, True]
        }, format="json")
        self.assertEqual(resp_bool.status_code, 400)

    def test_nonexistent_paper_id_returns_404(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, 999999]
        }, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "NOT_FOUND")

    def test_unauthenticated_request_returns_401(self):
        resp = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, self.paper2.id]
        }, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_unauthorized_cross_project_paper_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, self.other_paper.id]
        }, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], "FORBIDDEN")

    def test_unauthorized_session_returns_403(self):
        self.client.force_authenticate(user=self.user1)
        resp = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, self.paper2.id],
            "session_id": self.session2.id
        }, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], "FORBIDDEN")

    def test_cross_project_paper_with_valid_session_returns_400(self):
        self.client.force_authenticate(user=self.user1)
        # Create second project for user1
        proj1_b = Project.objects.create(owner=self.user1, title="User1 Project B")
        paper_1b = Paper.objects.create(project=proj1_b, title="Project B Paper")

        resp = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, paper_1b.id],
            "session_id": self.session1.id
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("do not belong to this research session", resp.json()["error"])

    def test_blank_question_uses_default_question(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch

        expected_default = (
            "Identify the major research gaps, limitations, unanswered questions, "
            "and future research directions across these papers."
        )

        with patch("ai.views.generate_research_gap_analysis", return_value=self.mock_gap_response) as mock_service:
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "   "
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            mock_service.assert_called_once()
            called_question = mock_service.call_args.kwargs["question"]
            self.assertEqual(called_question, expected_default)

    def test_custom_question_passed_to_service(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch

        custom_q = "What are the specific dataset biases between these papers?"

        with patch("ai.views.generate_research_gap_analysis", return_value=self.mock_gap_response) as mock_service:
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": custom_q
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            mock_service.assert_called_once()
            called_question = mock_service.call_args.kwargs["question"]
            self.assertEqual(called_question, custom_q)

    def test_service_called_with_exact_validated_papers(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch

        with patch("ai.views.generate_research_gap_analysis", return_value=self.mock_gap_response) as mock_service:
            # Send in reverse order [paper2, paper1]
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper2.id, self.paper1.id]
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            mock_service.assert_called_once()
            called_papers = mock_service.call_args.kwargs["papers"]
            self.assertEqual(called_papers, [self.paper2, self.paper1])

    def test_service_failure_maps_to_appropriate_api_errors(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        from ai.services import RateLimitError

        # 429 RateLimitError
        with patch("ai.views.generate_research_gap_analysis", side_effect=RateLimitError("Rate limit")):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id]
            }, format="json")
            self.assertEqual(resp.status_code, 429)
            self.assertEqual(resp.json()["code"], "RATE_LIMITED")

        # 503 Unavailable
        with patch("ai.views.generate_research_gap_analysis", side_effect=Exception("503 UNAVAILABLE")):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id]
            }, format="json")
            self.assertEqual(resp.status_code, 503)
            self.assertEqual(resp.json()["code"], "SERVICE_UNAVAILABLE")

        # 400 ValueError
        with patch("ai.views.generate_research_gap_analysis", side_effect=ValueError("Invalid paper parameters")):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id]
            }, format="json")
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json()["code"], "BAD_REQUEST")

    def test_endpoint_creates_research_message_records_when_session_id_provided(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        from ai.models import ResearchMessage
        import json

        initial_msg_count = ResearchMessage.objects.filter(session=self.session1).count()

        with patch("ai.views.generate_research_gap_analysis", return_value=self.mock_gap_response):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "What research gaps exist across these papers?",
                "session_id": self.session1.id
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(ResearchMessage.objects.filter(session=self.session1).count(), initial_msg_count + 2)

            user_msg = ResearchMessage.objects.filter(session=self.session1, role=ResearchMessage.ROLE_USER).last()
            self.assertEqual(user_msg.content, "What research gaps exist across these papers?")

            asst_msg = ResearchMessage.objects.filter(session=self.session1, role=ResearchMessage.ROLE_ASSISTANT).last()
            parsed_content = json.loads(asst_msg.content)
            self.assertEqual(parsed_content["overall_assessment"], "Grounded research gaps across papers.")

    def test_endpoint_creates_research_evidence_records_with_deduplication(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        from ai.models import ResearchEvidence, ResearchMessage

        # Mock gap response with sources across multiple sections, including a duplicate source
        source_p1 = {
            "chunk_id": self.chunk1.id,
            "paper_id": self.paper1.id,
            "page_number": 3,
            "text": "Paper Alpha chunk text",
        }
        source_p2 = {
            "chunk_id": self.chunk2.id,
            "paper_id": self.paper2.id,
            "page_number": 7,
            "text": "Paper Beta chunk text",
        }

        mock_gap = {
            "question": "Gap analysis question",
            "papers": [
                {"paper_id": self.paper1.id, "title": self.paper1.title},
                {"paper_id": self.paper2.id, "title": self.paper2.title}
            ],
            "gap_analysis": {
                "overall_assessment": "Grounded gaps.",
                "common_limitations": [
                    {"statement": "Small sample size.", "sources": [source_p1]}
                ],
                "methodological_gaps": [
                    # Include source_p1 again (duplicate) and source_p2
                    {"statement": "No cross-validation.", "sources": [source_p1, source_p2]}
                ],
                "dataset_population_gaps": [],
                "understudied_areas": [],
                "contradictions_inconsistencies": [],
                "unanswered_research_questions": [],
                "future_research_directions": []
            }
        }

        with patch("ai.views.generate_research_gap_analysis", return_value=mock_gap):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "session_id": self.session1.id
            }, format="json")

            self.assertEqual(resp.status_code, 200)

            asst_msg = ResearchMessage.objects.filter(session=self.session1, role=ResearchMessage.ROLE_ASSISTANT).last()
            evidence_records = ResearchEvidence.objects.filter(message=asst_msg)

            # Exactly 2 unique evidence records should be created (source_p1 deduplicated)
            self.assertEqual(evidence_records.count(), 2)

            evidence_chunk_ids = set(evidence_records.values_list("chunk_id", flat=True))
            self.assertIn(self.chunk1.id, evidence_chunk_ids)
            self.assertIn(self.chunk2.id, evidence_chunk_ids)

            ev_p1 = evidence_records.get(chunk=self.chunk1)
            self.assertEqual(ev_p1.paper, self.paper1)
            self.assertEqual(ev_p1.page_number, 3)
            self.assertEqual(ev_p1.text, "Paper Alpha chunk text")

    def test_endpoint_does_not_create_records_when_no_session_id(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        from ai.models import ResearchMessage, ResearchEvidence

        initial_msg_count = ResearchMessage.objects.count()
        initial_ev_count = ResearchEvidence.objects.count()

        with patch("ai.views.generate_research_gap_analysis", return_value=self.mock_gap_response):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(ResearchMessage.objects.count(), initial_msg_count)
            self.assertEqual(ResearchEvidence.objects.count(), initial_ev_count)

    def test_session_persistence_atomic_rollback_on_service_exception(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        from ai.models import ResearchMessage, ResearchEvidence

        initial_msg_count = ResearchMessage.objects.filter(session=self.session1).count()
        initial_ev_count = ResearchEvidence.objects.count()

        with patch("ai.views.generate_research_gap_analysis", side_effect=Exception("Service exploded")):
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "session_id": self.session1.id
            }, format="json")

            self.assertEqual(resp.status_code, 500)
            # Transaction must have rolled back - 0 new messages or evidence
            self.assertEqual(ResearchMessage.objects.filter(session=self.session1).count(), initial_msg_count)
            self.assertEqual(ResearchEvidence.objects.count(), initial_ev_count)

    def test_reconstructed_from_session_detail_endpoint(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch
        import json

        source_p1 = {
            "chunk_id": self.chunk1.id,
            "paper_id": self.paper1.id,
            "page_number": 3,
            "text": "Paper Alpha chunk text",
        }
        mock_gap = {
            "question": "Assess research gaps across papers",
            "papers": [
                {"paper_id": self.paper1.id, "title": self.paper1.title},
                {"paper_id": self.paper2.id, "title": self.paper2.title}
            ],
            "gap_analysis": {
                "overall_assessment": "Assessment of research gaps.",
                "common_limitations": [
                    {"statement": "Limited sample size.", "sources": [source_p1]}
                ],
                "methodological_gaps": [],
                "dataset_population_gaps": [],
                "understudied_areas": [],
                "contradictions_inconsistencies": [],
                "unanswered_research_questions": [],
                "future_research_directions": []
            }
        }

        with patch("ai.views.generate_research_gap_analysis", return_value=mock_gap):
            post_resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "question": "Assess research gaps across papers",
                "session_id": self.session1.id
            }, format="json")
            self.assertEqual(post_resp.status_code, 200)

        # Now fetch session via GET /api/ai/sessions/<id>/
        get_resp = self.client.get(f"/api/ai/sessions/{self.session1.id}/")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()

        messages = data.get("messages", [])
        self.assertGreaterEqual(len(messages), 2)
        user_msg = messages[-2]
        asst_msg = messages[-1]

        self.assertEqual(user_msg["role"], "USER")
        self.assertEqual(user_msg["content"], "Assess research gaps across papers")

        self.assertEqual(asst_msg["role"], "ASSISTANT")
        parsed = json.loads(asst_msg["content"])
        self.assertEqual(parsed["overall_assessment"], "Assessment of research gaps.")
        self.assertEqual(parsed["common_limitations"][0]["statement"], "Limited sample size.")

        # Check evidence attached to assistant message
        evidence = asst_msg.get("evidence", [])
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["paper_id"], self.paper1.id)
        self.assertEqual(evidence[0]["chunk_id"], self.chunk1.id)
        self.assertEqual(evidence[0]["page_number"], 3)
        self.assertEqual(evidence[0]["text"], "Paper Alpha chunk text")

    def test_session_id_is_optional(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch

        # Without session_id
        with patch("ai.views.generate_research_gap_analysis", return_value=dict(self.mock_gap_response)):
            resp_without = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id]
            }, format="json")
            self.assertEqual(resp_without.status_code, 200)
            self.assertNotIn("session_id", resp_without.json())

        # With session_id
        with patch("ai.views.generate_research_gap_analysis", return_value=dict(self.mock_gap_response)):
            resp_with = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id],
                "session_id": self.session1.id
            }, format="json")
            self.assertEqual(resp_with.status_code, 200)
            self.assertEqual(resp_with.json().get("session_id"), self.session1.id)

    def test_exactly_one_service_invocation_per_successful_request(self):
        self.client.force_authenticate(user=self.user1)
        from unittest.mock import patch

        with patch("ai.views.generate_research_gap_analysis", return_value=self.mock_gap_response) as mock_service:
            resp = self.client.post("/api/ai/gap-analysis/", {
                "paper_ids": [self.paper1.id, self.paper2.id]
            }, format="json")

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(mock_service.call_count, 1)

    def test_nonexistent_or_invalid_session_id_returns_404(self):
        self.client.force_authenticate(user=self.user1)

        resp_nonexistent = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, self.paper2.id],
            "session_id": 999999
        }, format="json")
        self.assertEqual(resp_nonexistent.status_code, 404)
        self.assertEqual(resp_nonexistent.json()["code"], "NOT_FOUND")

        resp_invalid_str = self.client.post("/api/ai/gap-analysis/", {
            "paper_ids": [self.paper1.id, self.paper2.id],
            "session_id": "not-an-id"
        }, format="json")
        self.assertEqual(resp_invalid_str.status_code, 404)











