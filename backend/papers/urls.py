from django.urls import path
from .views import (
    PaperListCreateView,
    PaperDetailView,
    paper_semantic_search,
    reprocess_paper,
)

urlpatterns = [
    path('', PaperListCreateView.as_view(), name='paper-list-create'),
    path('<int:paper_id>/', PaperDetailView.as_view(), name='paper-detail'),
    path(
        "<int:paper_id>/search/",
        paper_semantic_search,
        name="paper-semantic-search",
    ),
    path(
        "<int:paper_id>/reprocess/",
        reprocess_paper,
        name="paper-reprocess",
    ),
]
