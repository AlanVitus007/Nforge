import numpy as np
import os

from google import genai
from .models import PaperChunk


def split_text(text, chunk_size=1000, overlap=200):
    """
    Split extracted paper text into overlapping chunks.
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


def create_paper_chunks(paper):
    """
    Split a paper's extracted text into chunks and save them
    with embeddings in the database.
    """
    if not paper.extracted_text:
        return []

    # Remove existing chunks so the function can safely be run again.
    paper.chunks.all().delete()

    chunks = split_text(paper.extracted_text)

    paper_chunks = []

    for index, chunk_text in enumerate(chunks):
        embedding = generate_embedding(chunk_text)

        paper_chunk = PaperChunk.objects.create(
            paper=paper,
            chunk_index=index,
            text=chunk_text,
            embedding=embedding,
        )

        paper_chunks.append(paper_chunk)

    return paper_chunks


def semantic_search(query, paper=None, top_k=5):
    """
    Find the most relevant paper chunks for a user query.
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
    Generate a natural-language answer using relevant paper chunks.
    """

    if not search_results:
        return "I could not find relevant information in this paper."

    context = "\n\n".join(
        f"Source section {index + 1}:\n{result['chunk'].text}"
        for index, result in enumerate(search_results)
    )

    prompt = f"""
You are an academic research assistant.

Answer the user's question using only the provided paper sections.

Rules:
- Do not invent information.
- Do not use outside knowledge.
- If the paper does not contain enough information, say so.
- Give a clear, concise, natural-language answer.
- Do not mention similarity scores.
- Do not refer to the text as chunks.

User question:
{question}

Relevant paper sections:
{context}
"""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )

    return response.text