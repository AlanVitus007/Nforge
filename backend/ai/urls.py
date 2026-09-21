from django.urls import path
from .views import ask_ai, health, generate_summary_view, generate_research_gaps_view, compare_papers_view

urlpatterns = [
    path("ask/", ask_ai, name="ask-ai"),
    path("summary/", generate_summary_view, name="paper-summary"),
    path("research-gaps/", generate_research_gaps_view, name="research-gaps"),
    path("compare/", compare_papers_view, name="compare-papers"),
    path("health/", health, name="ai-health"),
]


