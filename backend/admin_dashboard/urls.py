from django.urls import path
from .views import (
    AdminDashboardView,
    AdminUserListView,
    AdminUserDetailView,
    AdminProjectListView,
    AdminProjectDetailView,
    AdminPaperListView,
    AdminPaperDetailView,
    AdminActivityOverviewView,
    AdminAIUsageView,
)

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('projects/', AdminProjectListView.as_view(), name='admin-project-list'),
    path('projects/<int:project_id>/', AdminProjectDetailView.as_view(), name='admin-project-detail'),
    path('papers/', AdminPaperListView.as_view(), name='admin-paper-list'),
    path('papers/<int:paper_id>/', AdminPaperDetailView.as_view(), name='admin-paper-detail'),
    path('activity/', AdminActivityOverviewView.as_view(), name='admin-activity-overview'),
    path('ai-usage/', AdminAIUsageView.as_view(), name='admin-ai-usage'),
]



