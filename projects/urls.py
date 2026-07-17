from django.urls import path

from .views import project_create_view, project_list_view

urlpatterns = [
    path('', project_list_view, name='project_list'),
    path('new/', project_create_view, name='project_create'),
]
