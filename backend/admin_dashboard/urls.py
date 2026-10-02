from django.urls import path
from .views import (
    AdminDashboardView,
    AdminUserListView,
    AdminUserDetailView,
    AdminProjectListView,
    AdminProjectDetailView,
)

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('projects/', AdminProjectListView.as_view(), name='admin-project-list'),
    path('projects/<int:project_id>/', AdminProjectDetailView.as_view(), name='admin-project-detail'),
]

