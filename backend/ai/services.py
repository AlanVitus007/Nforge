import numpy as np

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