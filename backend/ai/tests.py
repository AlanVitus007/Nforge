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


