from django.urls import path

from .views import ai_chat_view, ai_insights_view

urlpatterns = [
    path('insights/<int:paper_id>/', ai_insights_view, name='ai_insights'),
    path('chat/<int:paper_id>/', ai_chat_view, name='ai_chat'),
]
