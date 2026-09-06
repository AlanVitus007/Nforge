from django.urls import path
from .views import PaperListCreateView, PaperDetailView

urlpatterns = [
    path('', PaperListCreateView.as_view(), name='paper-list-create'),
    path('<int:paper_id>/', PaperDetailView.as_view(), name='paper-detail'),
]
