import numpy as np
import os

from google import genai
from .models import PaperChunk


def split_text(text, chunk_size=1000, overlap=200):
    """
    Split extracted paper text into overlapping chunks.
    Returns a list of chunk strings.
    """
    if not text:
        return []

    text = text.strip()

    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def split_text_with_pages(page_texts, chunk_size=1000, overlap=200):
    """
    Split a list of (page_number, text) tuples into overlapping chunks while
    preserving the source page number.

    Each chunk is attributed to the page where it *starts*. If a fixed-size
    window crosses a page boundary the attribution stays with the starting page,
    which is the most accurate single-page reference available without
    introducing heuristics.

    Returns a list of (chunk_text, page_number) tuples.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    # Build a flat character stream that remembers which page each character
    # came from so we can look up the page number for any chunk start position.
    flat_text = ""
    char_pages = []  # parallel array: char_pages[i] = page_number of flat_text[i]

    for page_number, text in page_texts:
        cleaned = text.strip()
        if not cleaned:
            continue
        # Add a newline separator between pages so words do not merge
        if flat_text:
            flat_text += "\n"
            char_pages.append(char_pages[-1] if char_pages else page_number)

        flat_text += cleaned
        char_pages.extend([page_number] * len(cleaned))

    if not flat_text:
        return []

    chunks = []
    start = 0

    while start < len(flat_text):
        end = start + chunk_size
        chunk = flat_text[start:end].strip()

        if chunk:
            # The chunk's page is determined by where it starts in the stream
            page_number = char_pages[start]
            chunks.append((chunk, page_number))

        if end >= len(flat_text):
            break

        start = end - overlap

    return chunks


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
    Split a paper's text into chunks and save them with embeddings.

    Parameters
    ----------
    paper : Paper
        The paper whose chunks should be (re)created.
    page_texts : list of (int, str) | None
        A list of (page_number, page_text) tuples produced by the PDF extractor.
        When provided the chunks are created page-aware.
        When None the function falls back to the original flat-text approach so
        that existing callers do not break (page_number will be null for those
        chunks).
    """
    # Remove existing chunks so this function can safely be called again.
    paper.chunks.all().delete()

    if page_texts is not None:
        # Page-aware path (new uploads and reprocessed papers)
        chunk_tuples = split_text_with_pages(page_texts)
    else:
        # Legacy fallback: use the stored extracted_text without page info
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

        context_parts.append(
            f"""
SOURCE {index + 1}
Chunk ID: {chunk.id}
Chunk Index: {chunk.chunk_index}

Text:
{chunk.text}
"""
        )

    context = "\n".join(context_parts)

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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    sources = []

    for index, result in enumerate(search_results):
        chunk = result["chunk"]

        sources.append({
            "source_number": index + 1,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,  # may be None for old chunks
            "text": chunk.text,
        })

    return {
        "answer": response.text,
        "sources": sources,
    }