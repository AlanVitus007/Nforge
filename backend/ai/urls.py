from django.urls import path
from .views import (
    ask_ai,
    health,
    generate_summary_view,
    generate_research_gaps_view,
    compare_papers_view,
    research_gap_analysis_view,
    session_list_create_view,
    session_detail_view,
)

urlpatterns = [
    path("ask/", ask_ai, name="ask-ai"),
    path("summary/", generate_summary_view, name="paper-summary"),
    path("research-gaps/", generate_research_gaps_view, name="research-gaps"),
    path("compare/", compare_papers_view, name="compare-papers"),
    path("gap-analysis/", research_gap_analysis_view, name="research-gap-analysis"),
    path("health/", health, name="ai-health"),
    path("sessions/", session_list_create_view, name="session-list-create"),
    path("sessions/<int:session_id>/", session_detail_view, name="session-detail"),
]


