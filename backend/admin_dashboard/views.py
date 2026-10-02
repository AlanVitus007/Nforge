from django.contrib.auth.models import User
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_dashboard.permissions import IsNForgeAdmin
from admin_dashboard.serializers import (
    AdminPaperSummarySerializer,
    AdminProjectDetailSerializer,
    AdminProjectListSerializer,
    AdminResearchSessionSummarySerializer,
    AdminUserDetailSerializer,
    AdminUserListSerializer,
)
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
            "collaborators": ProjectMember.objects.exclude(
                role=ProjectMember.ROLE_OWNER
            ).exclude(user=F("project__owner")).count(),
            "research_messages": ResearchMessage.objects.count(),
        }
        return Response(stats)


class AdminPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })


AdminUserPagination = AdminPagination
AdminProjectPagination = AdminPagination


class AdminUserListView(APIView):
    """
    List registered platform users with search and pagination.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request):
        queryset = User.objects.annotate(
            project_count=Count('projects', distinct=True),
            membership_count=Count(
                'project_memberships',
                filter=~Q(project_memberships__role=ProjectMember.ROLE_OWNER),
                distinct=True,
            ),
        ).order_by('-date_joined')

        search = request.query_params.get('search') or request.query_params.get('q')
        if search:
            search = search.strip()
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )

        paginator = AdminUserPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = AdminUserListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AdminUserListSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminUserDetailView(APIView):
    """
    Retrieve user detail including project memberships and roles.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request, user_id):
        user = get_object_or_404(
            User.objects.annotate(
                project_count=Count('projects', distinct=True),
                membership_count=Count(
                    'project_memberships',
                    filter=~Q(project_memberships__role=ProjectMember.ROLE_OWNER),
                    distinct=True,
                ),
            ),
            pk=user_id,
        )

        # Projects owned by user
        owned_projects = Project.objects.filter(owner=user).annotate(
            paper_count=Count('papers', distinct=True)
        ).order_by('-created_at')

        # Projects where user is an invited member (EDITOR, VIEWER)
        member_records = ProjectMember.objects.filter(
            user=user
        ).exclude(
            role=ProjectMember.ROLE_OWNER
        ).exclude(
            project__owner=user
        ).select_related('project').annotate(
            paper_count=Count('project__papers', distinct=True)
        ).order_by('-created_at')

        user_projects = []
        for p in owned_projects:
            user_projects.append({
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'role': ProjectMember.ROLE_OWNER,
                'paper_count': p.paper_count,
                'created_at': p.created_at,
            })

        for m in member_records:
            user_projects.append({
                'id': m.project.id,
                'title': m.project.title,
                'description': m.project.description,
                'role': m.role,
                'paper_count': m.paper_count,
                'created_at': m.project.created_at,
            })

        serializer = AdminUserListSerializer(user)
        data = serializer.data
        data['projects'] = user_projects
        return Response(data)


class AdminProjectListView(APIView):
    """
    List platform projects with search and pagination.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request):
        queryset = Project.objects.select_related('owner').annotate(
            paper_count=Count('papers', distinct=True),
            member_count=Count('members', distinct=True),
            research_session_count=Count('research_sessions', distinct=True),
        ).order_by('-created_at')

        search = request.query_params.get('search') or request.query_params.get('q')
        if search:
            search = search.strip()
            queryset = queryset.filter(title__icontains=search)

        paginator = AdminProjectPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = AdminProjectListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AdminProjectListSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminProjectDetailView(APIView):
    """
    Retrieve project detail including owner, members, safe papers metadata,
    and safe research session metadata.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request, project_id):
        project = get_object_or_404(
            Project.objects.select_related('owner').annotate(
                paper_count=Count('papers', distinct=True),
                member_count=Count('members', distinct=True),
                research_session_count=Count('research_sessions', distinct=True),
            ),
            pk=project_id,
        )

        # 1. Members: collect owner (as OWNER) + ProjectMember records (as EDITOR/VIEWER/etc.)
        db_members = list(project.members.select_related('user').order_by('created_at'))
        has_owner = any(m.user_id == project.owner_id for m in db_members)

        members_data = []
        if not has_owner and project.owner:
            members_data.append({
                'id': None,
                'user_id': project.owner.id,
                'username': project.owner.username,
                'email': project.owner.email,
                'role': ProjectMember.ROLE_OWNER,
                'created_at': project.created_at,
            })

        for m in db_members:
            members_data.append({
                'id': m.id,
                'user_id': m.user.id,
                'username': m.user.username,
                'email': m.user.email,
                'role': m.role,
                'created_at': m.created_at,
            })

        # 2. Papers: safe metadata only (id, title, file_name, uploaded_at)
        papers = list(
            project.papers.only('id', 'title', 'file', 'uploaded_at', 'project_id').order_by('-uploaded_at')
        )

        # 3. Research sessions: safe metadata only (id, title, created_at, updated_at, message_count)
        sessions = list(
            project.research_sessions.annotate(
                message_count=Count('messages', distinct=True)
            ).only('id', 'title', 'created_at', 'updated_at', 'project_id').order_by('-updated_at')
        )

        serializer = AdminProjectListSerializer(project)
        data = serializer.data
        data['members'] = members_data
        data['papers'] = AdminPaperSummarySerializer(papers, many=True).data
        data['research_sessions'] = AdminResearchSessionSummarySerializer(sessions, many=True).data

        return Response(data)

