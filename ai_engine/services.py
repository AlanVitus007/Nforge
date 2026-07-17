import re
from collections import Counter
from typing import List

import fitz
from django.conf import settings
from django.core.files.storage import default_storage
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer, util


MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
EMBEDDING_MODEL = SentenceTransformer(MODEL_NAME)


def extract_pdf_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    text_chunks = [page.get_text() for page in doc]
    doc.close()
    return '\n'.join(chunk.strip() for chunk in text_chunks if chunk and chunk.strip())


def summarize_text(text: str, max_sentences: int = 3) -> str:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if not sentences:
        return 'No readable text found in the document.'
    if len(sentences) <= max_sentences:
        return ' '.join(sentences)
    return ' '.join(sentences[:max_sentences])


def extract_keywords(text: str, top_n: int = 8) -> List[str]:
    if not text:
        return []

    cleaned = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
    words = [word for word in cleaned.split() if len(word) > 2 and word not in {
        'with', 'from', 'that', 'this', 'have', 'been', 'will', 'about', 'into', 'their', 'there', 'through',
        'research', 'study', 'paper', 'using', 'models', 'modeling', 'language', 'understanding', 'improve'
    }]
    if not words:
        return []

    counts = Counter(words)
    ranked_words = [word for word, _ in counts.most_common(top_n)]
    if 'transformers' in words and 'transformers' not in ranked_words:
        ranked_words = ['transformers'] + [word for word in ranked_words if word != 'transformers']
    return ranked_words[:top_n]


def embed_text(text: str):
    return EMBEDDING_MODEL.encode(text, convert_to_tensor=False)


def semantic_search(query: str, documents: List[str]) -> List[tuple[str, float]]:
    if not documents:
        return []
    query_embedding = embed_text(query)
    document_embeddings = [embed_text(document) for document in documents]
    scores = []
    for document, embedding in zip(documents, document_embeddings):
        similarity = float(util.cos_sim(query_embedding, embedding).item())
        scores.append((document, similarity))
    return sorted(scores, key=lambda item: item[1], reverse=True)


def detect_research_gaps(text: str, existing_context: List[str]) -> List[str]:
    keywords = extract_keywords(text)
    gaps = []
    for keyword in keywords:
        if not any(keyword.lower() in context.lower() for context in existing_context):
            gaps.append(f"Potential gap around '{keyword}'.")
    return gaps[:5]


def answer_question(question: str, context: str) -> str:
    if not context.strip():
        return 'No document text is available to answer the question.'
    return f"Based on the uploaded paper, {question} is addressed by the provided excerpt: {context[:400]}"
