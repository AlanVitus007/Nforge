from django.urls import path

from .views import (
    paper_create_view,
    paper_delete_view,
    paper_detail_view,
    paper_edit_view,
    paper_list_view,
)

urlpatterns = [
    path('', paper_list_view, name='paper_list'),
    path('new/', paper_create_view, name='paper_create'),
    path('<int:pk>/', paper_detail_view, name='paper_detail'),
    path('<int:pk>/edit/', paper_edit_view, name='paper_edit'),
    path('<int:pk>/delete/', paper_delete_view, name='paper_delete'),
]
