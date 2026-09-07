from sentence_transformers import SentenceTransformer
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
    """
    Load the embedding model only when it is first needed.
    """
    global _model

    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model


def generate_embedding(text):
    """
    Generate a semantic embedding for a piece of text.
    """
    if not text or not text.strip():
        return []

    model = get_embedding_model()
    embedding = model.encode(text)

    return embedding.tolist()



def create_paper_chunks(paper):
    """
    Split a paper's extracted text into chunks and save them
    in the database.
    """

    if not paper.extracted_text:
        return []

    # Remove existing chunks so the function can safely be run again.
    paper.chunks.all().delete()

    chunks = split_text(paper.extracted_text)

    paper_chunks = []

    for index, chunk_text in enumerate(chunks):
        paper_chunk = PaperChunk.objects.create(
            paper=paper,
            chunk_index=index,
            text=chunk_text,
        )

        paper_chunks.append(paper_chunk)

    return paper_chunks