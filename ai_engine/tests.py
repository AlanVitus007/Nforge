import io
import os
import tempfile

from django.test import TestCase

from .services import answer_question, detect_research_gaps, extract_keywords, extract_pdf_text, summarize_text


class AIToolsTests(TestCase):
    def test_pdf_analysis_pipeline(self):
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Transformers improve language understanding and climate modeling research.")
        buffer = io.BytesIO()
        doc.save(buffer)
        doc.close()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as handle:
            handle.write(buffer.getvalue())
            temp_path = handle.name

        try:
            extracted_text = extract_pdf_text(temp_path)
            self.assertIn('Transformers', extracted_text)

            summary = summarize_text(extracted_text)
            self.assertTrue(summary)

            keywords = extract_keywords(extracted_text)
            self.assertIn('transformers', keywords)

            gaps = detect_research_gaps(extracted_text, [
                'Climate models often rely on statistical methods and large datasets.',
                'Language understanding can be improved with transformer architectures.'
            ])
            self.assertTrue(gaps)

            answer = answer_question('What improves language understanding?', extracted_text)
            self.assertTrue(answer)
        finally:
            os.remove(temp_path)
