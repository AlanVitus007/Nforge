from django.urls import path

from .views import (
    project_create_view,
    project_delete_view,
    project_detail_view,
    project_edit_view,
    project_list_view,
)

urlpatterns = [
    path('', project_list_view, name='project_list'),
    path('new/', project_create_view, name='project_create'),
    path('<int:pk>/', project_detail_view, name='project_detail'),
    path('<int:pk>/edit/', project_edit_view, name='project_edit'),
    path('<int:pk>/delete/', project_delete_view, name='project_delete'),
]
