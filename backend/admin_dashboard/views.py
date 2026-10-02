from django.contrib.auth.models import User
from django.db.models import Count, F, Max, Q
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_dashboard.permissions import IsNForgeAdmin
from admin_dashboard.serializers import (
    AdminActivityDetailSerializer,
    AdminAIUsageItemSerializer,
    AdminPaperChunkSummarySerializer,
    AdminPaperDetailSerializer,
    AdminPaperListSerializer,
    AdminPaperSummarySerializer,
    AdminProjectDetailSerializer,
    AdminProjectListSerializer,
    AdminRecentPaperSerializer,
    AdminRecentResearchSessionSerializer,
    AdminRecentUserSerializer,
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
AdminPaperPagination = AdminPagination
AdminAIUsagePagination = AdminPagination



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


class AdminPaperListView(APIView):
    """
    List platform papers with search, project filtering, processing status filtering,
    and pagination.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request):
        queryset = Paper.objects.select_related('project', 'project__owner').annotate(
            chunk_count=Count('chunks', distinct=True),
            page_count=Max('chunks__page_number'),
        ).order_by('-uploaded_at')

        # 1. Search by paper title
        search = request.query_params.get('search') or request.query_params.get('q')
        if search:
            queryset = queryset.filter(title__icontains=search.strip())

        # 2. Filter by project ID
        project_filter = request.query_params.get('project') or request.query_params.get('project_id')
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)

        # 3. Filter by processing status if provided
        status_filter = request.query_params.get('status') or request.query_params.get('processing_status')
        if status_filter:
            status_filter = status_filter.strip().upper()
            if status_filter == 'PROCESSED':
                queryset = queryset.filter(Q(chunk_count__gt=0) | ~Q(extracted_text=""))
            elif status_filter in ('PENDING', 'UNPROCESSED'):
                queryset = queryset.filter(Q(chunk_count=0) & (Q(extracted_text="") | Q(extracted_text__isnull=True)))

        paginator = AdminPaperPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = AdminPaperListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AdminPaperListSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminPaperDetailView(APIView):
    """
    Retrieve paper detail including project, owner, safe chunk metadata,
    and non-sensitive processing info.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request, paper_id):
        paper = get_object_or_404(
            Paper.objects.select_related('project', 'project__owner').annotate(
                chunk_count=Count('chunks', distinct=True),
                page_count=Max('chunks__page_number'),
            ),
            pk=paper_id,
        )

        chunks = list(
            paper.chunks.only('id', 'chunk_index', 'page_number', 'created_at', 'paper_id').order_by('chunk_index')
        )

        serializer = AdminPaperDetailSerializer(paper)
        data = serializer.data
        data['chunks'] = AdminPaperChunkSummarySerializer(chunks, many=True).data

        return Response(data)


class AdminActivityOverviewView(APIView):
    """
    Admin activity overview endpoint returning platform aggregates and recent
    events across user registrations, paper uploads, and research session updates.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request):
        total_users = User.objects.count()
        total_projects = Project.objects.count()
        total_papers = Paper.objects.count()
        total_research_sessions = ResearchSession.objects.count()
        total_research_messages = ResearchMessage.objects.count()

        recent_users_qs = User.objects.only(
            'id', 'username', 'email', 'date_joined', 'is_active'
        ).order_by('-date_joined')[:10]

        recent_papers_qs = Paper.objects.select_related(
            'project', 'project__owner'
        ).only(
            'id', 'title', 'file', 'uploaded_at', 'project__id', 'project__title', 'project__owner__username'
        ).order_by('-uploaded_at')[:10]

        recent_sessions_qs = ResearchSession.objects.select_related(
            'project'
        ).annotate(
            message_count=Count('messages', distinct=True)
        ).only(
            'id', 'title', 'created_at', 'updated_at', 'project__id', 'project__title'
        ).order_by('-updated_at')[:10]

        recent_activity_qs = ResearchMessage.objects.filter(role=ResearchMessage.ROLE_ASSISTANT).select_related(
            'session', 'session__project', 'session__project__owner'
        ).prefetch_related('evidence').order_by('-created_at')[:10]

        recent_users_data = AdminRecentUserSerializer(recent_users_qs, many=True).data
        recent_papers_data = AdminRecentPaperSerializer(recent_papers_qs, many=True).data
        recent_sessions_data = AdminRecentResearchSessionSerializer(recent_sessions_qs, many=True).data
        recent_activity_data = AdminAIUsageItemSerializer(recent_activity_qs, many=True).data

        data = {
            'total_users': total_users,
            'total_projects': total_projects,
            'total_papers': total_papers,
            'total_research_sessions': total_research_sessions,
            'total_research_messages': total_research_messages,
            'recent_users': recent_users_data,
            'recent_papers': recent_papers_data,
            'recent_research_sessions': recent_sessions_data,
            'recent_activity': recent_activity_data,
            'recent_messages': recent_activity_data,
            # Aliases for convenience
            'users': total_users,
            'projects': total_projects,
            'papers': total_papers,
            'research_sessions': total_research_sessions,
            'research_messages': total_research_messages,
            'recent_user_registrations': recent_users_data,
            'recently_uploaded_papers': recent_papers_data,
            'recently_updated_research_sessions': recent_sessions_data,
        }

        return Response(data)


class AdminActivityDetailView(APIView):
    """
    Retrieve read-only activity detail for a specific ResearchMessage.
    Returns safe structural, operational, and relational metadata without
    exposing private research dialogue content, prompts, or evidence text.
    Only accessible by staff/superusers.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request, message_id):
        message = get_object_or_404(
            ResearchMessage.objects.select_related(
                'session',
                'session__project',
                'session__project__owner',
            ).prefetch_related(
                'session__papers',
                'evidence__paper',
            ),
            pk=message_id,
        )

        serializer = AdminActivityDetailSerializer(message)
        return Response(serializer.data)


class AdminAIUsageView(APIView):
    """
    Read-only AI usage monitoring endpoint for NForge administrators.
    Provides aggregate stats, operation breakdown, user/project breakdown,
    and paginated/recent activity logs with strict exclusion of sensitive content.
    """
    permission_classes = [IsAuthenticated, IsNForgeAdmin]

    def get(self, request):
        base_assistant_qs = ResearchMessage.objects.filter(role=ResearchMessage.ROLE_ASSISTANT)

        # 1. Platform-wide AI usage aggregates
        total_ai_activity = base_assistant_qs.count()
        total_sessions = ResearchSession.objects.filter(
            messages__role=ResearchMessage.ROLE_ASSISTANT
        ).distinct().count()

        # Breakdown by operation
        gap_count = base_assistant_qs.filter(
            Q(content__icontains='"common_limitations"') |
            Q(content__icontains='"methodological_gaps"') |
            Q(content__icontains='"gap_analysis"')
        ).count()

        compare_count = base_assistant_qs.filter(
            Q(content__icontains='"similarities"') |
            Q(content__icontains='"differences"') |
            Q(content__icontains='"methodology_comparison"')
        ).count()

        thematic_count = base_assistant_qs.filter(
            Q(content__icontains='"themes"')
        ).count()

        trend_count = base_assistant_qs.filter(
            Q(content__icontains='"research_evolution"') |
            Q(content__icontains='"methodological_shifts"')
        ).count()

        ask_ai_count = max(0, total_ai_activity - (gap_count + compare_count + thematic_count + trend_count))

        operations_breakdown = [
            {"operation": "ASK_AI", "label": "Paper Q&A", "count": ask_ai_count},
            {"operation": "COMPARE_PAPERS", "label": "Paper Comparison", "count": compare_count},
            {"operation": "GAP_ANALYSIS", "label": "Research Gap Analysis", "count": gap_count},
            {"operation": "THEMATIC_ANALYSIS", "label": "Thematic Analysis", "count": thematic_count},
            {"operation": "RESEARCH_TRENDS", "label": "Research Trend Analysis", "count": trend_count},
        ]
        by_operation = {item["operation"]: item["count"] for item in operations_breakdown}

        # Activity by user (top 10 project owners)
        user_breakdown = (
            base_assistant_qs.values(
                'session__project__owner__id',
                'session__project__owner__username',
            )
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        by_user = [
            {
                "user_id": item['session__project__owner__id'],
                "username": item['session__project__owner__username'],
                "count": item['count'],
            }
            for item in user_breakdown
            if item['session__project__owner__id'] is not None
        ]

        # Activity by project (top 10 projects)
        project_breakdown = (
            base_assistant_qs.values(
                'session__project__id',
                'session__project__title',
            )
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        by_project = [
            {
                "project_id": item['session__project__id'],
                "project_title": item['session__project__title'],
                "count": item['count'],
            }
            for item in project_breakdown
            if item['session__project__id'] is not None
        ]

        # 2. Filterable activity log queryset
        log_qs = base_assistant_qs.select_related(
            'session',
            'session__project',
            'session__project__owner',
        ).prefetch_related('evidence').order_by('-created_at')

        # Filter by operation
        op_param = request.query_params.get('operation')
        if op_param:
            op_key = op_param.strip().upper().replace('-', '_')
            if op_key == "GAP_ANALYSIS":
                log_qs = log_qs.filter(
                    Q(content__icontains='"common_limitations"') |
                    Q(content__icontains='"methodological_gaps"') |
                    Q(content__icontains='"gap_analysis"')
                )
            elif op_key in ("COMPARE_PAPERS", "COMPARE"):
                log_qs = log_qs.filter(
                    Q(content__icontains='"similarities"') |
                    Q(content__icontains='"differences"') |
                    Q(content__icontains='"methodology_comparison"')
                )
            elif op_key == "THEMATIC_ANALYSIS":
                log_qs = log_qs.filter(Q(content__icontains='"themes"'))
            elif op_key in ("RESEARCH_TRENDS", "TRENDS", "TREND_ANALYSIS"):
                log_qs = log_qs.filter(
                    Q(content__icontains='"research_evolution"') |
                    Q(content__icontains='"methodological_shifts"')
                )
            elif op_key in ("ASK_AI", "QNA", "ASK"):
                log_qs = log_qs.exclude(
                    Q(content__icontains='"common_limitations"') |
                    Q(content__icontains='"methodological_gaps"') |
                    Q(content__icontains='"gap_analysis"') |
                    Q(content__icontains='"similarities"') |
                    Q(content__icontains='"differences"') |
                    Q(content__icontains='"methodology_comparison"') |
                    Q(content__icontains='"themes"') |
                    Q(content__icontains='"research_evolution"') |
                    Q(content__icontains='"methodological_shifts"')
                )

        # Filter by project_id
        project_id_param = request.query_params.get('project_id')
        if project_id_param:
            try:
                log_qs = log_qs.filter(session__project_id=int(project_id_param))
            except (ValueError, TypeError):
                pass

        # Filter by user_id
        user_id_param = request.query_params.get('user_id')
        if user_id_param:
            try:
                log_qs = log_qs.filter(session__project__owner_id=int(user_id_param))
            except (ValueError, TypeError):
                pass

        # Filter by search (matches session title, project title, or owner username)
        search_param = request.query_params.get('search') or request.query_params.get('q')
        if search_param:
            search_param = search_param.strip()
            log_qs = log_qs.filter(
                Q(session__title__icontains=search_param) |
                Q(session__project__title__icontains=search_param) |
                Q(session__project__owner__username__icontains=search_param)
            )

        # Recent activity (top 5 most recent across the platform)
        recent_qs = base_assistant_qs.select_related(
            'session',
            'session__project',
            'session__project__owner',
        ).prefetch_related('evidence').order_by('-created_at')[:5]
        recent_activity_data = AdminAIUsageItemSerializer(recent_qs, many=True).data

        # Paginate results
        paginator = AdminAIUsagePagination()
        page = paginator.paginate_queryset(log_qs, request, view=self)

        if page is not None:
            serializer = AdminAIUsageItemSerializer(page, many=True)
            page_data = serializer.data
            return Response({
                "total_ai_activity": total_ai_activity,
                "total_activity": total_ai_activity,
                "total_sessions": total_sessions,
                "operations_breakdown": operations_breakdown,
                "by_operation": by_operation,
                "by_user": by_user,
                "by_project": by_project,
                "recent_activity": recent_activity_data,
                "count": paginator.page.paginator.count,
                "total_pages": paginator.page.paginator.num_pages,
                "current_page": paginator.page.number,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": page_data,
            })

        serializer = AdminAIUsageItemSerializer(log_qs, many=True)
        return Response({
            "total_ai_activity": total_ai_activity,
            "total_activity": total_ai_activity,
            "total_sessions": total_sessions,
            "operations_breakdown": operations_breakdown,
            "by_operation": by_operation,
            "by_user": by_user,
            "by_project": by_project,
            "recent_activity": recent_activity_data,
            "count": log_qs.count(),
            "total_pages": 1,
            "current_page": 1,
            "next": None,
            "previous": None,
            "results": serializer.data,
        })




