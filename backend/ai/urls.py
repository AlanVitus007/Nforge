from django.urls import path
from .views import ask_ai, health

urlpatterns = [
    path("ask/", ask_ai, name="ask-ai"),
    path("health/", health, name="ai-health"),
]
