from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_dashboard.permissions import IsNForgeAdmin
from ai.models import ResearchMessage, ResearchSession
from papers.models import Paper
from projects.models import Project, ProjectMember


class AdminDashboardView(APIView):
    """
    Dedicated admin dashboard endpoint returning aggregate system statistics.
    Enforces staff or superuser permissions via IsNForgeAdmin.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request):
        stats = {
            "users": User.objects.count(),
            "projects": Project.objects.count(),
            "papers": Paper.objects.count(),
            "research_sessions": ResearchSession.objects.count(),
            "collaborators": ProjectMember.objects.count(),
            "research_messages": ResearchMessage.objects.count(),
        }
        return Response(stats)
