from sentence_transformers import SentenceTransformer


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