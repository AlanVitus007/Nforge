from django.test import TestCase
from django.contrib.auth.models import User
from projects.models import Project
from papers.models import Paper
from ai.models import PaperChunk
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









