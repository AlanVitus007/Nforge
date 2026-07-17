from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from papers.models import Paper
from .services import answer_question, detect_research_gaps, extract_keywords, extract_pdf_text, summarize_text


@login_required
def ai_insights_view(request, paper_id):
    paper = get_object_or_404(Paper, pk=paper_id, owner=request.user)
    text = ''
    if paper.pdf_file:
        file_path = paper.pdf_file.path
        text = extract_pdf_text(file_path)

    if not text:
        text = paper.abstract or ''

    summary = summarize_text(text) if text else 'No readable paper content available yet.'
    keywords = extract_keywords(text) if text else []
    gaps = detect_research_gaps(text, [paper.abstract or '']) if text else []

    context = {
        'paper': paper,
        'summary': summary,
        'keywords': keywords,
        'gaps': gaps,
        'extracted_text': text,
    }
    return render(request, 'ai_engine/insights.html', context)


@login_required
def ai_chat_view(request, paper_id):
    paper = get_object_or_404(Paper, pk=paper_id, owner=request.user)
    answer = ''
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        if question:
            text = ''
            if paper.pdf_file:
                text = extract_pdf_text(paper.pdf_file.path)
            if not text:
                text = paper.abstract or ''
            answer = answer_question(question, text)
    return render(request, 'ai_engine/chat.html', {'paper': paper, 'answer': answer})
