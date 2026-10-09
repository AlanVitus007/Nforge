from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import health_check
from papers.views import PaperNoteListCreateView, PaperNoteDetailView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/auth/', include('accounts.urls')),
    path('api/friends/', include('accounts.friends_urls')),
    path('api/projects/', include('projects.urls')),
    path('api/projects/<int:project_id>/papers/', include('papers.urls')),
    path('api/papers/<int:paper_id>/notes/', PaperNoteListCreateView.as_view(), name='paper-notes-list-create'),
    path('api/paper-notes/<int:note_id>/', PaperNoteDetailView.as_view(), name='paper-note-detail'),
    path('api/ai/', include('ai.urls')),
    path('api/admin/', include('admin_dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
