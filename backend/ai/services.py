import json
import numpy as np
import os
import re
import time

from google import genai
from google.genai import types
from .models import PaperChunk



ABBREVIATIONS = {
    'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr', 'rev', 'st',
    'eg', 'ie', 'vs', 'cf', 'etc', 'viz', 'al', 'etal',
    'fig', 'figs', 'vol', 'no', 'nos', 'ref', 'refs', 'eq', 'eqs',
    'sec', 'secs', 'app', 'ch', 'approx', 'dept', 'univ', 'corp',
    'inc', 'ltd', 'co', 'pp', 'p', 'jan', 'feb', 'mar', 'apr',
    'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec'
}


def split_into_sentences(text):
    """
    Split text into clean, complete sentences using regex boundary matching
    that respects abbreviations, initials, decimals, and citations.
    """
    if not text or not text.strip():
        return []

    text = re.sub(r'\s+', ' ', text.strip())
    pattern = re.compile(r'([.!?]+)(\s+)(?=[A-Z0-9"\'\(\[\{]|$)')

    sentences = []
    start = 0

    for match in pattern.finditer(text):
        punct = match.group(1)
        candidate = text[start:match.start() + len(punct)]

        last_word_match = re.search(r'([A-Za-z0-9.]+)\s*$', candidate)
        is_abbrev = False

        if punct == '.' and last_word_match:
            last_word = last_word_match.group(1).rstrip('.')
            if len(last_word) == 1 and last_word.isalpha():
                is_abbrev = True
            elif last_word.lower() in ABBREVIATIONS:
                is_abbrev = True
            elif last_word.lower().replace('.', '') in ABBREVIATIONS:
                is_abbrev = True

        if not is_abbrev:
            sentence_str = candidate.strip()
            if sentence_str:
                sentences.append(sentence_str)
            start = match.end()

    remainder = text[start:].strip()
    if remainder:
        sentences.append(remainder)

    return sentences


def is_probable_heading(text):
    """
    Detect if text represents a heading (e.g., '1. Introduction', '3.2 Methods').
    """
    text_clean = text.strip()
    if not text_clean:
        return False
    if re.match(r'^\d+(\.\d+)*\s+[A-Z]', text_clean) and len(text_clean) < 120:
        return True
    if len(text_clean) < 80 and not text_clean.endswith(('.', ':', ';', '!', '?')):
        return True
    return False


def split_word_boundary(text, target_size=1000):
    """
    Fallback splitter that splits text at word boundaries only.
    NEVER splits words in the middle.
    """
    words = text.split(' ')
    chunks = []
    cur_words = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 > target_size and cur_words:
            chunks.append(' '.join(cur_words))
            cur_words = [w]
            cur_len = len(w)
        else:
            cur_words.append(w)
            cur_len += len(w) + 1
    if cur_words:
        chunks.append(' '.join(cur_words))
    return chunks


def split_text_structure_aware(
    page_structures,
    target_chunk_size=1000,
    max_chunk_size=1400,
    min_chunk_size=300,
    max_overlap_sentences=2,
    max_overlap_chars=250,
):
    """
    Structure-aware chunking pipeline following the hierarchy:
    PDF Page -> Paragraph -> Sentence -> Semantic Chunk.

    Preserves sentence and paragraph boundaries, attaches headings to content,
    applies sentence-level overlap, and ensures zero word chopping.
    """
    chunks = []

    for page_number, paragraphs in page_structures:
        if not paragraphs:
            continue

        if isinstance(paragraphs, str):
            paragraphs = [p for p in re.split(r'\n\s*\n', paragraphs) if p.strip()]

        items = []
        pending_heading = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if is_probable_heading(para):
                if pending_heading:
                    pending_heading += "\n" + para
                else:
                    pending_heading = para
                continue

            sents = split_into_sentences(para)
            if not sents:
                continue

            if pending_heading:
                sents[0] = f"{pending_heading}\n{sents[0]}"
                pending_heading = ""

            items.extend(sents)

        if pending_heading and items:
            items[-1] = f"{items[-1]}\n{pending_heading}"
            pending_heading = ""
        elif pending_heading:
            items.append(pending_heading)
            pending_heading = ""

        if not items:
            continue

        current_sents = []
        current_len = 0
        page_chunks = []

        for item in items:
            item_len = len(item)

            if item_len > max_chunk_size:
                if current_sents:
                    chunk_text = " ".join(current_sents).strip()
                    if chunk_text:
                        page_chunks.append(chunk_text)
                    current_sents = []
                    current_len = 0
                sub_chunks = split_word_boundary(item, target_size=target_chunk_size)
                for sc in sub_chunks[:-1]:
                    page_chunks.append(sc)
                if sub_chunks:
                    current_sents = [sub_chunks[-1]]
                    current_len = len(sub_chunks[-1])
                continue

            if current_len + item_len + 1 > target_chunk_size:
                if current_len >= min_chunk_size or current_len + item_len + 1 > max_chunk_size:
                    chunk_text = " ".join(current_sents).strip()
                    if chunk_text:
                        page_chunks.append(chunk_text)

                    overlap_sents = []
                    overlap_len = 0
                    for s in reversed(current_sents):
                        if len(overlap_sents) >= max_overlap_sentences:
                            break
                        if overlap_len + len(s) + 1 > max_overlap_chars:
                            break
                        overlap_sents.insert(0, s)
                        overlap_len += len(s) + 1

                    current_sents = overlap_sents + [item]
                    current_len = sum(len(s) for s in current_sents) + max(0, len(current_sents) - 1)
                else:
                    current_sents.append(item)
                    current_len += item_len + 1
            else:
                current_sents.append(item)
                current_len += item_len + 1

        if current_sents:
            chunk_text = " ".join(current_sents).strip()
            if chunk_text:
                if page_chunks and len(chunk_text) < min_chunk_size and (len(page_chunks[-1]) + len(chunk_text) + 1 <= max_chunk_size):
                    page_chunks[-1] = f"{page_chunks[-1]} {chunk_text}"
                else:
                    page_chunks.append(chunk_text)

        for pc in page_chunks:
            chunks.append((pc, page_number))

    return chunks


def split_text(text, chunk_size=1000, overlap=200):
    """
    Structure-aware chunking for raw text strings.
    """
    if not text or not text.strip():
        return []
    structures = [(1, [text])]
    results = split_text_structure_aware(structures, target_chunk_size=chunk_size)
    return [c[0] for c in results]


def split_text_with_pages(page_texts, chunk_size=1000, overlap=200):
    """
    Structure-aware chunking preserving page numbers.
    Accepts list of (page_number, text_or_paragraphs) tuples.
    """
    if not page_texts:
        return []
    return split_text_structure_aware(page_texts, target_chunk_size=chunk_size)


_model = None


def get_embedding_model():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model


def generate_embedding(text):
    model = get_embedding_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()


def create_paper_chunks(paper, page_texts=None):
    """
    Split a paper's text into structure-aware chunks and save them with embeddings.

    Parameters
    ----------
    paper : Paper
        The paper whose chunks should be (re)created.
    page_texts : list of (int, str|list) | None
        A list of (page_number, page_text_or_paragraphs) tuples produced by the PDF extractor.
    """
    # Remove existing chunks so this function can safely be called again.
    paper.chunks.all().delete()

    if page_texts is None and paper.file:
        try:
            from papers.views import extract_page_texts
            page_texts, full_text = extract_page_texts(paper.file.path)
            if full_text and not paper.extracted_text:
                paper.extracted_text = full_text
                paper.save(update_fields=["extracted_text"])
        except Exception as err:
            print(f"Failed to extract page_texts from PDF file: {err}")
            page_texts = None

    if page_texts is not None:
        # Structure and page-aware path
        chunk_tuples = split_text_with_pages(page_texts)
    else:
        # Fallback: use stored extracted_text without page info
        if not paper.extracted_text:
            return []
        raw_chunks = split_text(paper.extracted_text)
        chunk_tuples = [(chunk, None) for chunk in raw_chunks]

    if not chunk_tuples:
        return []

    paper_chunks = []

    for index, (chunk_text, page_number) in enumerate(chunk_tuples):
        embedding = generate_embedding(chunk_text)

        paper_chunk = PaperChunk.objects.create(
            paper=paper,
            chunk_index=index,
            page_number=page_number,
            text=chunk_text,
            embedding=embedding,
        )

        paper_chunks.append(paper_chunk)

    return paper_chunks


def semantic_search(query, paper=None, top_k=5):
    """
    Find the most relevant paper chunks for a user query.
    Returns a list of dicts with 'chunk' and 'similarity' keys.
    The chunk objects now carry page_number.
    """
    query_embedding = np.array(generate_embedding(query))

    chunks = PaperChunk.objects.all()

    if paper is not None:
        chunks = chunks.filter(paper=paper)

    results = []

    for chunk in chunks:
        if not chunk.embedding:
            continue

        chunk_embedding = np.array(chunk.embedding)

        similarity = np.dot(query_embedding, chunk_embedding)

        results.append({
            "chunk": chunk,
            "similarity": float(similarity),
        })

    results.sort(
        key=lambda result: result["similarity"],
        reverse=True,
    )

    return results[:top_k]


def retrieve_multi_paper_evidence(question, papers, top_k_per_paper=5):
    """
    Retrieve relevant evidence chunks grouped by paper across multiple papers.
    Uses local SentenceTransformer embeddings and cosine similarity (0 Gemini calls).

    Parameters
    ----------
    question : str
        The query/question string. Must be non-empty.
    papers : list | QuerySet
        A list of Paper model instances (1 to 4 papers).
    top_k_per_paper : int, optional
        Maximum number of top evidence chunks to return per paper (default 5, max 8).

    Returns
    -------
    list of dict
        Grouped evidence structures per paper containing paper metadata and sorted source chunks.
    """
    from papers.models import Paper

    if not question or not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string.")

    if not papers:
        raise ValueError("papers must be a non-empty list of Paper instances.")

    papers_list = list(papers)

    if len(papers_list) > 4:
        raise ValueError("Maximum 4 papers supported for multi-paper evidence retrieval.")

    for p in papers_list:
        if not isinstance(p, Paper):
            raise ValueError("Each item in papers must be a valid Paper instance.")

    if not isinstance(top_k_per_paper, int) or top_k_per_paper < 1 or top_k_per_paper > 8:
        raise ValueError("top_k_per_paper must be an integer between 1 and 8.")

    # Generate query embedding ONCE for performance
    query_embedding = np.array(generate_embedding(question.strip()))

    grouped_results = []

    # Scoped query: fetch chunks only for the requested papers
    all_chunks = PaperChunk.objects.filter(paper__in=papers_list)

    # Group chunks by paper ID in memory to minimize DB hits
    chunks_by_paper = {}
    for chunk in all_chunks:
        chunks_by_paper.setdefault(chunk.paper_id, []).append(chunk)

    for paper in papers_list:
        paper_chunks = chunks_by_paper.get(paper.id, [])
        scored_sources = []

        for chunk in paper_chunks:
            if not chunk.embedding:
                continue

            chunk_embedding = np.array(chunk.embedding)
            similarity = float(np.dot(query_embedding, chunk_embedding))

            scored_sources.append({
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "similarity": similarity,
            })

        # Sort sources within each paper by similarity descending
        scored_sources.sort(key=lambda s: s["similarity"], reverse=True)

        grouped_results.append({
            "paper_id": paper.id,
            "paper_title": paper.title,
            "sources": scored_sources[:top_k_per_paper],
        })

    return grouped_results


def generate_ai_answer(question, search_results):
    """
    Generate an AI answer using only the retrieved paper chunks.
    Also returns source chunks including page_number for traceability.
    """

    if not search_results:
        return {
            "answer": "I could not find relevant information in this paper.",
            "sources": [],
        }

    context_parts = []

    for index, result in enumerate(search_results):
        chunk = result["chunk"]
        page_str = f"Page {chunk.page_number}" if chunk.page_number else "Page 1"
        context_parts.append(f"SOURCE {index + 1} ({page_str}):\n{chunk.text}")

    context = "\n\n".join(context_parts)

    prompt = f"""
You are an academic research assistant.

Answer the user's question using ONLY the information contained
in the provided paper sources.

Rules:
- Do not invent information.
- Do not use outside knowledge.
- If the paper does not contain enough information, clearly say so.
- Give a clear and concise answer.
- Do not mention similarity scores.
- Do not refer to the sources as "chunks".
- Do not create or invent citations.
- Base every factual statement on the provided sources.

User question:
{question}

Paper sources:
{context}
"""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    print("[Ask AI] Making Gemini call #1 for user question")
    response = _call_gemini(client, prompt, feature_name="ask_ai")

    sources = []

    for index, result in enumerate(search_results):
        chunk = result["chunk"]

        sources.append({
            "source_number": index + 1,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "text": chunk.text,
        })


    return {
        "answer": response.text,
        "sources": sources,
    }


def parse_summary_json(text):
    """
    Parse JSON from Gemini response text, handling markdown code blocks or formatting.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)

    data = json.loads(cleaned)

    return {
        "overview": data.get("overview") or "Not clearly stated in the paper.",
        "key_points": data.get("key_points") if isinstance(data.get("key_points"), list) else ([data.get("key_points")] if data.get("key_points") else ["Not clearly stated in the paper."]),
        "methodology": data.get("methodology") or "Not clearly stated in the paper.",
        "findings": data.get("findings") or "Not clearly stated in the paper.",
        "limitations": data.get("limitations") or "Not clearly stated in the paper.",
    }



class RateLimitError(Exception):
    """Raised when Gemini returns a 429 rate-limit error."""
    pass


def _is_rate_limit_error(err):
    """Check if an exception is a 429 rate-limit error."""
    err_msg = str(err)
    return "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg


def _call_gemini(client, prompt, *, json_mode=False, feature_name="ai"):
    """
    Make a single Gemini API call with smart error handling and diagnostics.

    - 429 / RESOURCE_EXHAUSTED  →  raise RateLimitError immediately (no retry).
    - 503 / UNAVAILABLE         →  retry up to 3 times with exponential backoff (2s, 4s).
    - Other errors              →  raise immediately.
    """
    config = None
    if json_mode:
        config = types.GenerateContentConfig(response_mime_type="application/json")

    last_err = None
    max_attempts = 3  # 1 original + 2 retries for transient 503 errors

    for attempt in range(max_attempts):
        start_time = time.time()
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=config,
            )
            duration = time.time() - start_time
            print(f"[DIAGNOSTICS] Feature: {feature_name} | Request #{attempt + 1} | Status: SUCCESS (200) | Duration: {duration:.2f}s")
            return response
        except Exception as err:
            duration = time.time() - start_time
            last_err = err

            # 429 rate-limit → never retry, surface immediately
            if _is_rate_limit_error(err):
                print(f"[DIAGNOSTICS] Feature: {feature_name} | Request #{attempt + 1} | Status: RATE_LIMITED (429) | Duration: {duration:.2f}s")
                raise RateLimitError(
                    "Gemini API rate limit exceeded. Please try again later."
                ) from err

            # 503 transient → retry with exponential backoff (2s, 4s)
            err_msg = str(err)
            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                print(f"[DIAGNOSTICS] Feature: {feature_name} | Request #{attempt + 1} | Status: SERVICE_UNAVAILABLE (503) | Duration: {duration:.2f}s")
                if attempt < max_attempts - 1:
                    backoff = 2 ** (attempt + 1)
                    print(f"[Gemini] 503 transient error for '{feature_name}', retrying in {backoff}s (attempt {attempt + 1}/{max_attempts})...")
                    time.sleep(backoff)
                    continue

            print(f"[DIAGNOSTICS] Feature: {feature_name} | Request #{attempt + 1} | Status: ERROR ({type(err).__name__}) | Duration: {duration:.2f}s")
            raise

    if last_err:
        raise last_err




def generate_paper_summary(paper):
    """
    Generate a structured academic summary from the paper's stored PaperChunks.

    API call strategy:
    - Normal papers (≤500k chars): ONE Gemini call with all chunk text.
    - Huge papers (>500k chars): Batched into large windows → 1 call per batch + 1 final call.

    Returns a dict with 'summary' object and 'sources' array containing actual page_numbers.
    """
    gemini_call_count = 0

    chunks = list(paper.chunks.all().order_by("chunk_index"))

    if not chunks:
        if paper.extracted_text:
            chunks = create_paper_chunks(paper)
        if not chunks:
            raise ValueError("This paper has no extracted text or chunks available.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    total_chars = sum(len(c.text) for c in chunks)
    print(f"[Summary] Paper '{paper.title}': {len(chunks)} chunks, {total_chars} total chars")

    # Gemini Flash supports ~1M token context. 500k chars ≈ 125k tokens — safe for single call.
    HIERARCHICAL_THRESHOLD = 500000

    prompt_instructions = """
You are an academic research assistant.
Summarize the provided paper using ONLY the information contained in the text.

Rules:
- Do not use outside knowledge.
- Do not invent findings, methodology, overview, or limitations.
- If a category is not clearly stated in the text, set its value to "Not clearly stated in the paper."
- Keep the summary clear, academic, concise, and structured.
- Do not mention chunk IDs or invent page numbers.

Output MUST be a JSON object with these exact keys:
{
    "overview": "High-level summary of what the paper is about",
    "key_points": ["Key takeaway 1", "Key takeaway 2", ...],
    "methodology": "The approach, architecture, dataset, or methods used",
    "findings": "Key findings, experimental results, or conclusions",
    "limitations": "Stated limitations, threats to validity, or future work"
}
"""

    if total_chars <= HIERARCHICAL_THRESHOLD:
        # --- SINGLE CALL: one Gemini request for the entire paper ---
        formatted_chunks = []
        for c in chunks:
            formatted_chunks.append(f"[Page {c.page_number or 1}] {c.text}")
        paper_text = "\n\n".join(formatted_chunks)

        full_prompt = f"{prompt_instructions}\n\nPaper Content:\n{paper_text}"

        gemini_call_count += 1
        print(f"[Summary] Making Gemini call #{gemini_call_count} (single-stage, {len(full_prompt)} chars prompt)")
        response = _call_gemini(client, full_prompt, json_mode=True, feature_name="summary")

        summary_json = parse_summary_json(response.text)

    else:
        # --- BATCHED: large windows to minimize calls ---
        # Use very large batches (100 chunks ≈ 100k chars per batch) to keep call count low
        batch_size = 100
        section_summaries = []

        for idx_batch, i in enumerate(range(0, len(chunks), batch_size)):
            group = chunks[i:i + batch_size]
            group_text = "\n\n".join([f"[Page {c.page_number or 1}] {c.text}" for c in group])
            stage1_prompt = f"Summarize the key information in this section of a research paper concisely:\n\n{group_text}"

            gemini_call_count += 1
            print(f"[Summary] Making Gemini call #{gemini_call_count} (batch {idx_batch + 1}, {len(group)} chunks)")
            res = _call_gemini(client, stage1_prompt, feature_name="summary")

            section_summaries.append(res.text)

        # Final synthesis call
        combined_summaries = "\n\n".join(section_summaries)
        full_prompt = f"{prompt_instructions}\n\nSection Summaries of the Paper:\n{combined_summaries}"

        gemini_call_count += 1
        print(f"[Summary] Making Gemini call #{gemini_call_count} (final synthesis)")
        response = _call_gemini(client, full_prompt, json_mode=True, feature_name="summary")


        summary_json = parse_summary_json(response.text)

    print(f"[Summary] Complete — total Gemini API calls: {gemini_call_count}")

    # Select representative chunks across the paper for page evidence
    selected_chunks = []
    num_chunks = len(chunks)

    if num_chunks <= 4:
        selected_chunks = chunks
    else:
        indices = [0, num_chunks // 3, (2 * num_chunks) // 3, num_chunks - 1]
        for idx in indices:
            selected_chunks.append(chunks[idx])

    sources = []
    for index, c in enumerate(selected_chunks):
        sources.append({
            "source_number": index + 1,
            "chunk_id": c.id,
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "text": c.text,
        })

    return {
        "summary": summary_json,
        "sources": sources,
    }


def parse_research_gaps_json(text):
    """
    Parse JSON from Gemini response text for research gaps,
    handling markdown code blocks or formatting.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)

    data = json.loads(cleaned)
    gaps = data.get("gaps") or []
    if not isinstance(gaps, list):
        gaps = []

    formatted_gaps = []
    for item in gaps:
        if not isinstance(item, dict):
            continue
        formatted_gaps.append({
            "category": item.get("category") or "General Research Gap",
            "title": item.get("title") or "Identified Gap",
            "description": item.get("description") or "No detailed description provided.",
            "page_number": item.get("page_number"),
        })

    return {
        "summary_statement": data.get("summary_statement") or "No overarching research gap statement provided.",
        "gaps": formatted_gaps,
    }


def generate_research_gaps(paper):
    """
    Analyze the selected research paper to detect research gaps, limitations,
    unanswered questions, dataset/methodology constraints, and future work.

    Returns a dict with 'gaps_data' (parsed gaps + summary_statement) and 'sources' array.
    """
    gemini_call_count = 0

    chunks = list(paper.chunks.all().order_by("chunk_index"))

    if not chunks:
        if paper.extracted_text:
            chunks = create_paper_chunks(paper)
        if not chunks:
            raise ValueError("This paper has no extracted text or chunks available.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    total_chars = sum(len(c.text) for c in chunks)
    print(f"[Research Gaps] Paper '{paper.title}': {len(chunks)} chunks, {total_chars} total chars")

    HIERARCHICAL_THRESHOLD = 500000

    prompt_instructions = """
You are an expert academic research gap analyst.
Analyze the provided research paper to identify research gaps, limitations, and areas for future work that are explicitly supported by the text of the paper.

Look specifically for:
1. Limitations explicitly mentioned by the authors (methodology, dataset, sample size, hardware, performance).
2. Unanswered questions or unresolved problems discussed by the authors.
3. Explicitly stated areas for future work or recommended next steps.
4. Missing experiments or evaluation scenarios discussed in the paper.

Rules:
- Base all findings STRICTLY on the text provided. Do NOT invent external knowledge.
- If no explicit research gaps are mentioned in the paper, return a clear summary_statement stating that no explicit research gaps were discussed, with an empty gaps list.
- For each gap item, select an appropriate category:
  - "Methodology Limitation"
  - "Dataset / Sample Limitation"
  - "Unresolved Question"
  - "Future Work"
  - "Missing Evaluation"

Output MUST be a valid JSON object with this exact structure:
{
    "summary_statement": "Brief 1-2 sentence overall synthesis of the primary research gaps identified in this paper.",
    "gaps": [
        {
            "category": "Methodology Limitation",
            "title": "Short descriptive title of the gap",
            "description": "Detailed explanation of the gap as described by the authors.",
            "page_number": 5
        }
    ]
}
"""

    if total_chars <= HIERARCHICAL_THRESHOLD:
        formatted_chunks = []
        for c in chunks:
            formatted_chunks.append(f"[Page {c.page_number or 1}] {c.text}")
        paper_text = "\n\n".join(formatted_chunks)

        full_prompt = f"{prompt_instructions}\n\nPaper Content:\n{paper_text}"

        gemini_call_count += 1
        print(f"[Research Gaps] Making Gemini call #{gemini_call_count} (single-stage)")
        response = _call_gemini(client, full_prompt, json_mode=True, feature_name="research_gaps")

        gaps_json = parse_research_gaps_json(response.text)

    else:
        batch_size = 100
        section_summaries = []

        for idx_batch, i in enumerate(range(0, len(chunks), batch_size)):
            group = chunks[i:i + batch_size]
            group_text = "\n\n".join([f"[Page {c.page_number or 1}] {c.text}" for c in group])
            stage1_prompt = f"Analyze this section of a research paper and list any stated limitations, unresolved questions, or future work:\n\n{group_text}"

            gemini_call_count += 1
            print(f"[Research Gaps] Making Gemini call #{gemini_call_count} (batch {idx_batch + 1})")
            res = _call_gemini(client, stage1_prompt, feature_name="research_gaps")

            section_summaries.append(res.text)

        combined_summaries = "\n\n".join(section_summaries)
        full_prompt = f"{prompt_instructions}\n\nSection Summaries of the Paper:\n{combined_summaries}"

        gemini_call_count += 1
        print(f"[Research Gaps] Making Gemini call #{gemini_call_count} (final synthesis)")
        response = _call_gemini(client, full_prompt, json_mode=True, feature_name="research_gaps")


        gaps_json = parse_research_gaps_json(response.text)

    print(f"[Research Gaps] Complete — total Gemini API calls: {gemini_call_count}")

    # Build sources referencing chunks across the paper
    selected_chunks = []
    num_chunks = len(chunks)

    if num_chunks <= 4:
        selected_chunks = chunks
    else:
        indices = [0, num_chunks // 3, (2 * num_chunks) // 3, num_chunks - 1]
        for idx in indices:
            selected_chunks.append(chunks[idx])

    sources = []
    for index, c in enumerate(selected_chunks):
        sources.append({
            "source_number": index + 1,
            "chunk_id": c.id,
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "text": c.text,
        })

    return {
        "gaps_data": gaps_json,
        "sources": sources,
    }


def parse_multi_paper_synthesis_json(text):
    """
    Parse JSON from Gemini multi-paper synthesis response text.
    Handles Markdown code fences (```json) safely.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        data = json.loads(cleaned)
    except Exception as err:
        print(f"Failed to parse multi-paper synthesis JSON: {err}")
        data = {}

    return {
        "overall_synthesis": data.get("overall_synthesis") or "Synthesis statement unavailable based on the provided evidence.",
        "similarities": data.get("similarities") if isinstance(data.get("similarities"), list) else [],
        "differences": data.get("differences") if isinstance(data.get("differences"), list) else [],
        "methodology_comparison": data.get("methodology_comparison") if isinstance(data.get("methodology_comparison"), list) else [],
        "findings_comparison": data.get("findings_comparison") if isinstance(data.get("findings_comparison"), list) else [],
        "research_gaps": data.get("research_gaps") if isinstance(data.get("research_gaps"), list) else [],
    }


def validate_and_resolve_source_refs(source_refs, valid_chunk_map):
    """
    Validate Gemini returned source_refs against DB PaperChunk map.
    Returns verified sources containing DB page_number, text, and paper_title.
    """
    resolved_sources = []
    if not isinstance(source_refs, list):
        return resolved_sources

    for ref in source_refs:
        if not isinstance(ref, dict):
            continue
        cid = ref.get("chunk_id")
        pid = ref.get("paper_id")

        if cid in valid_chunk_map:
            chunk = valid_chunk_map[cid]
            # Verify paper_id matches chunk.paper.id
            if pid is None or chunk.paper.id == pid:
                resolved_sources.append({
                    "paper_id": chunk.paper.id,
                    "paper_title": chunk.paper.title,
                    "chunk_id": chunk.id,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                })
    return resolved_sources


def generate_multi_paper_synthesis(question, papers):
    """
    Perform single-call Gemini multi-paper cross-paper synthesis.

    1. Calls local retrieve_multi_paper_evidence() to retrieve top evidence chunks.
    2. Builds a bounded context (max 20 chunks total across 4 papers).
    3. Makes EXACTLY ONE Gemini API call.
    4. Validates returned source_refs against actual DB PaperChunk instances.
    """
    # 1. Retrieve local evidence chunks (0 Gemini calls)
    query_text = (
        question.strip()
        if (question and isinstance(question, str) and question.strip())
        else "main findings methodology limitations research gaps"
    )

    retrieved_groups = retrieve_multi_paper_evidence(
        question=query_text,
        papers=papers,
        top_k_per_paper=5,
    )

    # Check for empty evidence
    total_chunks = sum(len(group["sources"]) for group in retrieved_groups)
    if total_chunks == 0:
        return {
            "question": query_text,
            "papers": [{"paper_id": p.id, "title": p.title} for p in papers],
            "comparison": {
                "overall_synthesis": "Insufficient text content found across the selected papers to generate a comparison.",
                "similarities": [],
                "differences": [],
                "methodology_comparison": [],
                "findings_comparison": [],
                "research_gaps": [],
            },
        }

    # Fetch PaperChunk objects for valid_chunk_map to resolve & verify source_refs against DB
    chunk_ids = [
        source["chunk_id"]
        for group in retrieved_groups
        for source in group["sources"]
    ]
    db_chunks = PaperChunk.objects.filter(id__in=chunk_ids).select_related("paper")
    valid_chunk_map = {chunk.id: chunk for chunk in db_chunks}

    # Build prompt context format matching section 5 of requirements
    context_blocks = []
    for group in retrieved_groups:
        paper_block = [f"PAPER ID: {group['paper_id']}\nTitle: {group['paper_title']}"]
        for s in group["sources"]:
            page_str = f"Page: {s['page_number']}" if s.get("page_number") else "Page: 1"
            paper_block.append(f"SOURCE (Chunk ID: {s['chunk_id']}, {page_str}):\n{s['text']}")
        context_blocks.append("\n\n".join(paper_block))

    combined_context = "\n\n---\n\n".join(context_blocks)
    paper_titles_str = ", ".join([f"'{p.title}' (ID: {p.id})" for p in papers])

    prompt = f"""You are an expert academic research synthesis assistant.

Analyze and compare the following research papers: {paper_titles_str}

Use ONLY the provided paper source excerpts to synthesize similarities, differences, methodology, findings, and research gaps.

Rules:
- Base every statement ONLY on the supplied evidence excerpts.
- Do NOT use outside knowledge or invent findings, methodology, limitations, or research gaps.
- Do NOT invent paper titles, paper IDs, chunk IDs, or page numbers.
- Ground claims in evidence. Do not claim agreement or disagreement unless supported by evidence.
- Include "source_refs" referencing exact "paper_id" and "chunk_id" from the excerpts for every claim.

Return your response STRICTLY as a JSON object matching this schema:
{{
    "overall_synthesis": "high-level synthesis statement",
    "similarities": [
        {{
            "statement": "similarity statement",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "differences": [
        {{
            "statement": "difference statement",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}},
                {{"paper_id": 2, "chunk_id": 201}}
            ]
        }}
    ],
    "methodology_comparison": [
        {{
            "paper_id": 1,
            "summary": "methodology summary for this paper",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "findings_comparison": [
        {{
            "paper_id": 1,
            "summary": "findings summary for this paper",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "research_gaps": [
        {{
            "statement": "gap or limitation statement",
            "type": "explicit|potential",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ]
}}

Source Excerpts:
{combined_context}
"""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    # Single Gemini call limit (EXACTLY 1 request)
    gemini_call_count = 1
    print(f"[Multi-Paper Synthesis] Making Gemini call #{gemini_call_count} (EXACTLY 1 request)")
    response = _call_gemini(client, prompt, json_mode=True, feature_name="multi_paper_synthesis")

    raw_parsed = parse_multi_paper_synthesis_json(response.text)

    # Validate and resolve source_refs against DB for each section
    similarities = []
    for item in raw_parsed["similarities"]:
        if isinstance(item, dict) and item.get("statement"):
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            similarities.append({
                "statement": item["statement"],
                "sources": sources,
            })

    differences = []
    for item in raw_parsed["differences"]:
        if isinstance(item, dict) and item.get("statement"):
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            differences.append({
                "statement": item["statement"],
                "sources": sources,
            })

    methodology_comp = []
    for item in raw_parsed["methodology_comparison"]:
        if isinstance(item, dict) and (item.get("summary") or item.get("statement")):
            summary_text = item.get("summary") or item.get("statement")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            methodology_comp.append({
                "paper_id": item.get("paper_id"),
                "summary": summary_text,
                "sources": sources,
            })

    findings_comp = []
    for item in raw_parsed["findings_comparison"]:
        if isinstance(item, dict) and (item.get("summary") or item.get("statement")):
            summary_text = item.get("summary") or item.get("statement")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            findings_comp.append({
                "paper_id": item.get("paper_id"),
                "summary": summary_text,
                "sources": sources,
            })

    research_gaps = []
    for item in raw_parsed["research_gaps"]:
        if isinstance(item, dict) and item.get("statement"):
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            gap_type = item.get("type") if item.get("type") in ["explicit", "potential"] else "explicit"
            research_gaps.append({
                "statement": item["statement"],
                "type": gap_type,
                "sources": sources,
            })

    print(f"[DIAGNOSTICS] Feature: multi_paper_synthesis | Gemini Calls: {gemini_call_count}")

    return {
        "question": query_text,
        "papers": [{"paper_id": p.id, "title": p.title} for p in papers],
        "comparison": {
            "overall_synthesis": raw_parsed["overall_synthesis"],
            "similarities": similarities,
            "differences": differences,
            "methodology_comparison": methodology_comp,
            "findings_comparison": findings_comp,
            "research_gaps": research_gaps,
        },
    }


def parse_research_gap_analysis_json(text):
    """
    Parse JSON from Gemini research gap analysis response text.
    Handles Markdown code fences (```json) safely and normalizes
    missing or malformed categories into safe defaults and lists.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        data = json.loads(cleaned)
    except Exception as err:
        print(f"Failed to parse research gap analysis JSON: {err}")
        data = {}

    if not isinstance(data, dict):
        data = {}

    return {
        "overall_assessment": data.get("overall_assessment") or "Assessment unavailable based on the provided evidence.",
        "common_limitations": data.get("common_limitations") if isinstance(data.get("common_limitations"), list) else [],
        "methodological_gaps": data.get("methodological_gaps") if isinstance(data.get("methodological_gaps"), list) else [],
        "dataset_population_gaps": data.get("dataset_population_gaps") if isinstance(data.get("dataset_population_gaps"), list) else [],
        "understudied_areas": data.get("understudied_areas") if isinstance(data.get("understudied_areas"), list) else [],
        "contradictions_inconsistencies": data.get("contradictions_inconsistencies") if isinstance(data.get("contradictions_inconsistencies"), list) else [],
        "unanswered_research_questions": data.get("unanswered_research_questions") if isinstance(data.get("unanswered_research_questions"), list) else [],
        "future_research_directions": data.get("future_research_directions") if isinstance(data.get("future_research_directions"), list) else [],
    }


def generate_research_gap_analysis(question, papers):
    """
    Perform single-call Gemini multi-paper Research Gap Analysis.

    1. Validates paper count (2 to 4 papers required).
    2. Calls local retrieve_multi_paper_evidence() to retrieve top evidence chunks.
    3. Builds a bounded prompt context with strict grounding rules.
    4. Makes EXACTLY ONE Gemini API call.
    5. Validates and resolves returned source_refs against actual DB PaperChunk instances.
    6. Returns structured gap analysis JSON conforming to Phase 7.1 schema.
    """
    from papers.models import Paper

    if not papers:
        raise ValueError("papers must be a non-empty list of Paper instances.")

    papers_list = list(papers)

    if len(papers_list) < 2 or len(papers_list) > 4:
        raise ValueError("Research gap analysis requires between 2 and 4 papers.")

    for p in papers_list:
        if not isinstance(p, Paper):
            raise ValueError("Each item in papers must be a valid Paper instance.")

    # Formulate query text (0 Gemini calls)
    query_text = (
        question.strip()
        if (question and isinstance(question, str) and question.strip())
        else "research gaps limitations methodological weaknesses dataset constraints unanswered questions future directions"
    )

    # 1. Retrieve local evidence chunks across 2-4 papers (0 Gemini calls)
    retrieved_groups = retrieve_multi_paper_evidence(
        question=query_text,
        papers=papers_list,
        top_k_per_paper=5,
    )

    # Check for empty evidence across all papers
    total_chunks = sum(len(group["sources"]) for group in retrieved_groups)
    if total_chunks == 0:
        empty_gap_data = {
            "overall_assessment": "Insufficient text content found across the selected papers to identify research gaps.",
            "common_limitations": [],
            "methodological_gaps": [],
            "dataset_population_gaps": [],
            "understudied_areas": [],
            "contradictions_inconsistencies": [],
            "unanswered_research_questions": [],
            "future_research_directions": [],
        }
        return {
            "question": query_text,
            "papers": [{"paper_id": p.id, "title": p.title} for p in papers_list],
            "gap_analysis": empty_gap_data,
            **empty_gap_data,
        }

    # Fetch DB PaperChunk objects to resolve and verify source_refs against real DB records
    chunk_ids = [
        source["chunk_id"]
        for group in retrieved_groups
        for source in group["sources"]
    ]
    db_chunks = PaperChunk.objects.filter(id__in=chunk_ids).select_related("paper")
    valid_chunk_map = {chunk.id: chunk for chunk in db_chunks}

    # Build prompt context with exact paper and chunk references
    context_blocks = []
    for group in retrieved_groups:
        paper_block = [f"PAPER ID: {group['paper_id']}\nTitle: {group['paper_title']}"]
        for s in group["sources"]:
            page_str = f"Page: {s['page_number']}" if s.get("page_number") else "Page: 1"
            paper_block.append(f"SOURCE (Chunk ID: {s['chunk_id']}, {page_str}):\n{s['text']}")
        context_blocks.append("\n\n".join(paper_block))

    combined_context = "\n\n---\n\n".join(context_blocks)
    paper_titles_str = ", ".join([f"'{p.title}' (ID: {p.id})" for p in papers_list])

    prompt = f"""You are an expert academic research gap analyst specializing in identifying limitations, literature gaps, and future research directions across scientific literature.

Analyze the following research papers: {paper_titles_str}

Research Gap Query / Focus: {query_text}

Use ONLY the provided paper source excerpts to evaluate research gaps, limitations, and future directions.

Distinctions to strictly observe:
- "common_limitations": Limitations explicitly identified and acknowledged in the papers (e.g. sample size, methodological constraints, hardware, threats to validity).
- "methodological_gaps": Methodological weaknesses, missing controls, lack of longitudinal evaluation, or unvalidated assumptions supported by the excerpts.
- "dataset_population_gaps": Missing datasets, underrepresented populations, geographic/demographic limits, or sample constraints supported by the evidence.
- "understudied_areas": Specific problem facets, edge cases, or sub-domains insufficiently explored across the selected literature.
- "contradictions_inconsistencies": Conflicting findings, divergent conclusions, differing assumptions, or contradictory empirical results supported by evidence.
- "unanswered_research_questions": Specific academic questions that remain open or unresolved based on the selected papers.
- "future_research_directions": Concrete, promising future research avenues directly grounded in the identified gaps and limitations.

Rules:
- Base every single statement strictly on the supplied evidence excerpts.
- Do NOT use outside knowledge, speculate without evidence, or invent unsupported claims.
- Do NOT invent paper titles, paper IDs, chunk IDs, or page numbers.
- For every substantive item, include "source_refs" referencing exact "paper_id" and "chunk_id" from the excerpts.
- If a category has no evidence in the provided excerpts, return an empty array [] for that category.

Return your response STRICTLY as a JSON object matching this schema:
{{
    "overall_assessment": "Comprehensive high-level synthesis of research gaps and limitations across the analyzed papers",
    "common_limitations": [
        {{
            "statement": "Explicit limitation statement",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "methodological_gaps": [
        {{
            "statement": "Methodological gap statement",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "dataset_population_gaps": [
        {{
            "statement": "Dataset or population gap statement",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "understudied_areas": [
        {{
            "statement": "Understudied area statement",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "contradictions_inconsistencies": [
        {{
            "statement": "Contradiction or inconsistency statement",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}},
                {{"paper_id": 2, "chunk_id": 201}}
            ]
        }}
    ],
    "unanswered_research_questions": [
        {{
            "question": "Unanswered research question",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ],
    "future_research_directions": [
        {{
            "direction": "Future research direction grounded in identified gaps",
            "source_refs": [
                {{"paper_id": 1, "chunk_id": 101}}
            ]
        }}
    ]
}}

Source Excerpts:
{combined_context}
"""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    # Single Gemini call limit (EXACTLY 1 request)
    gemini_call_count = 1
    print(f"[Research Gap Analysis] Making Gemini call #{gemini_call_count} (EXACTLY 1 request)")
    response = _call_gemini(client, prompt, json_mode=True, feature_name="research_gap_analysis")

    raw_parsed = parse_research_gap_analysis_json(response.text)

    # Validate and resolve source_refs against DB PaperChunk map for each section
    common_limitations = []
    for item in raw_parsed["common_limitations"]:
        if isinstance(item, dict) and (item.get("statement") or item.get("summary")):
            stmt = item.get("statement") or item.get("summary")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            common_limitations.append({
                "statement": stmt,
                "sources": sources,
            })

    methodological_gaps = []
    for item in raw_parsed["methodological_gaps"]:
        if isinstance(item, dict) and (item.get("statement") or item.get("summary")):
            stmt = item.get("statement") or item.get("summary")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            methodological_gaps.append({
                "statement": stmt,
                "sources": sources,
            })

    dataset_population_gaps = []
    for item in raw_parsed["dataset_population_gaps"]:
        if isinstance(item, dict) and (item.get("statement") or item.get("summary")):
            stmt = item.get("statement") or item.get("summary")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            dataset_population_gaps.append({
                "statement": stmt,
                "sources": sources,
            })

    understudied_areas = []
    for item in raw_parsed["understudied_areas"]:
        if isinstance(item, dict) and (item.get("statement") or item.get("summary")):
            stmt = item.get("statement") or item.get("summary")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            understudied_areas.append({
                "statement": stmt,
                "sources": sources,
            })

    contradictions_inconsistencies = []
    for item in raw_parsed["contradictions_inconsistencies"]:
        if isinstance(item, dict) and (item.get("statement") or item.get("summary")):
            stmt = item.get("statement") or item.get("summary")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            contradictions_inconsistencies.append({
                "statement": stmt,
                "sources": sources,
            })

    unanswered_questions = []
    for item in raw_parsed["unanswered_research_questions"]:
        if isinstance(item, dict) and (item.get("question") or item.get("statement") or item.get("summary")):
            q_text = item.get("question") or item.get("statement") or item.get("summary")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            unanswered_questions.append({
                "question": q_text,
                "sources": sources,
            })

    future_directions = []
    for item in raw_parsed["future_research_directions"]:
        if isinstance(item, dict) and (item.get("direction") or item.get("statement") or item.get("summary")):
            d_text = item.get("direction") or item.get("statement") or item.get("summary")
            sources = validate_and_resolve_source_refs(item.get("source_refs"), valid_chunk_map)
            future_directions.append({
                "direction": d_text,
                "sources": sources,
            })

    print(f"[DIAGNOSTICS] Feature: research_gap_analysis | Gemini Calls: {gemini_call_count}")

    gap_data = {
        "overall_assessment": raw_parsed["overall_assessment"],
        "common_limitations": common_limitations,
        "methodological_gaps": methodological_gaps,
        "dataset_population_gaps": dataset_population_gaps,
        "understudied_areas": understudied_areas,
        "contradictions_inconsistencies": contradictions_inconsistencies,
        "unanswered_research_questions": unanswered_questions,
        "future_research_directions": future_directions,
    }

    return {
        "question": query_text,
        "papers": [{"paper_id": p.id, "title": p.title} for p in papers_list],
        "gap_analysis": gap_data,
        **gap_data,
    }
