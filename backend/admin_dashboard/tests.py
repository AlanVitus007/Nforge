import json
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from admin_dashboard.permissions import IsNForgeAdmin
from ai.models import PaperChunk, ResearchEvidence, ResearchMessage, ResearchSession
from papers.models import Paper
from projects.models import Project, ProjectMember, ProjectInvitation



class AdminDashboardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/admin/dashboard/"

        # Normal user (no staff, no superuser)
        self.normal_user = User.objects.create_user(
            username="normaluser", password="password123", email="normal@example.com"
        )

        # Staff user (admin)
        self.staff_user = User.objects.create_user(
            username="staffadmin",
            password="password123",
            email="staff@example.com",
            is_staff=True,
        )

        # Superuser (admin)
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            password="password123",
            email="super@example.com",
        )

    def test_unauthenticated_access_returns_401(self):
        """Unauthenticated requests must be rejected with HTTP 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_authenticated_user_returns_403(self):
        """Normal authenticated users must be rejected with HTTP 403."""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_owner_returns_403(self):
        """Owning projects must not grant admin access; returns HTTP 403."""
        owner_user = User.objects.create_user(
            username="projectowner", password="password123"
        )
        Project.objects.create(
            owner=owner_user, title="Owner Project", description="Owner desc"
        )
        self.client.force_authenticate(user=owner_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_editor_returns_403(self):
        """Project editors must not gain admin access; returns HTTP 403."""
        owner = User.objects.create_user(username="projectowner2", password="password123")
        editor = User.objects.create_user(username="editoruser", password="password123")
        project = Project.objects.create(owner=owner, title="Collab Project")
        ProjectMember.objects.create(
            project=project, user=editor, role=ProjectMember.ROLE_EDITOR
        )

        self.client.force_authenticate(user=editor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_viewer_returns_403(self):
        """Project viewers must not gain admin access; returns HTTP 403."""
        owner = User.objects.create_user(username="projectowner3", password="password123")
        viewer = User.objects.create_user(username="vieweruser", password="password123")
        project = Project.objects.create(owner=owner, title="Viewer Project")
        ProjectMember.objects.create(
            project=project, user=viewer, role=ProjectMember.ROLE_VIEWER
        )

        self.client.force_authenticate(user=viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_access_returns_200(self):
        """Staff users are authorized and receive HTTP 200 with dashboard metrics."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("users", response.data)
        self.assertIn("projects", response.data)
        self.assertIn("papers", response.data)
        self.assertIn("research_sessions", response.data)
        self.assertIn("collaborators", response.data)
        self.assertIn("research_messages", response.data)

    def test_superuser_access_returns_200(self):
        """Superusers are authorized and receive HTTP 200."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_empty_database_zero_state_handling(self):
        """
        When only the staff admin exists, other metrics should be zero,
        and user count should correctly reflect existing user(s).
        """
        # Delete normal and super user to test minimal state
        self.normal_user.delete()
        self.superuser.delete()

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "users": 1,
                "projects": 0,
                "papers": 0,
                "research_sessions": 0,
                "collaborators": 0,
                "research_messages": 0,
            },
        )

    def test_statistics_calculation_correctness(self):
        """Verify accurate aggregate counting across all supported entity types."""
        # Create additional users
        user1 = User.objects.create_user(username="u1", password="pw")
        user2 = User.objects.create_user(username="u2", password="pw")

        # Create projects
        proj1 = Project.objects.create(owner=user1, title="Proj 1")
        proj2 = Project.objects.create(owner=user2, title="Proj 2")

        # Create collaborators
        ProjectMember.objects.create(
            project=proj1, user=user2, role=ProjectMember.ROLE_EDITOR
        )
        ProjectMember.objects.create(
            project=proj2, user=user1, role=ProjectMember.ROLE_VIEWER
        )

        # Create papers
        p1 = Paper.objects.create(project=proj1, title="Paper 1", file="papers/p1.pdf")
        p2 = Paper.objects.create(project=proj1, title="Paper 2", file="papers/p2.pdf")
        p3 = Paper.objects.create(project=proj2, title="Paper 3", file="papers/p3.pdf")

        # Create research sessions
        s1 = ResearchSession.objects.create(project=proj1, title="Session 1")
        s2 = ResearchSession.objects.create(project=proj2, title="Session 2")

        # Create research messages
        ResearchMessage.objects.create(
            session=s1, role=ResearchMessage.ROLE_USER, content="Hello"
        )
        ResearchMessage.objects.create(
            session=s1, role=ResearchMessage.ROLE_ASSISTANT, content="Hi"
        )
        ResearchMessage.objects.create(
            session=s2, role=ResearchMessage.ROLE_USER, content="Question"
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Total users: staff_user, normal_user, superuser, user1, user2 = 5
        self.assertEqual(response.data["users"], 5)
        self.assertEqual(response.data["projects"], 2)
        self.assertEqual(response.data["papers"], 3)
        self.assertEqual(response.data["research_sessions"], 2)
        self.assertEqual(response.data["collaborators"], 2)
        self.assertEqual(response.data["research_messages"], 3)

    def test_collaborator_count_does_not_count_project_owners(self):
        """
        Ensure project owners are not counted as collaborators, even if
        a ProjectMember record was created with ROLE_OWNER or matching user.
        """
        owner = User.objects.create_user(username="proj_owner_only", password="pw")
        collab = User.objects.create_user(username="proj_collab_only", password="pw")
        proj = Project.objects.create(owner=owner, title="Owner Test Project")

        # Legitimate collaborator
        ProjectMember.objects.create(
            project=proj, user=collab, role=ProjectMember.ROLE_EDITOR
        )

        # Owner membership record (should be excluded from collaborators count)
        ProjectMember.objects.create(
            project=proj, user=owner, role=ProjectMember.ROLE_OWNER
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only the editor collaborator should be counted, not the owner
        self.assertEqual(response.data["collaborators"], 1)

    def test_existing_project_permissions_remain_unaffected(self):
        """
        Verify that existing project owner/editor/viewer access controls
        function normally and are not altered by the admin subsystem.
        """
        owner = User.objects.create_user(username="project_owner_p", password="pw")
        viewer = User.objects.create_user(username="project_viewer_p", password="pw")
        unrelated = User.objects.create_user(username="unrelated_p", password="pw")

        proj = Project.objects.create(owner=owner, title="Permission Project")
        ProjectMember.objects.create(
            project=proj, user=viewer, role=ProjectMember.ROLE_VIEWER
        )

        # Owner can view and update project
        self.client.force_authenticate(user=owner)
        detail_res = self.client.get(f"/api/projects/{proj.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)

        patch_res = self.client.patch(f"/api/projects/{proj.id}/", {"title": "Updated Title"})
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)

        # Viewer can view but cannot modify
        self.client.force_authenticate(user=viewer)
        viewer_get = self.client.get(f"/api/projects/{proj.id}/")
        self.assertEqual(viewer_get.status_code, status.HTTP_200_OK)

        viewer_patch = self.client.patch(f"/api/projects/{proj.id}/", {"title": "Viewer Edit"})
        self.assertEqual(viewer_patch.status_code, status.HTTP_403_FORBIDDEN)

        # Unrelated user cannot view
        self.client.force_authenticate(user=unrelated)
        unrelated_get = self.client.get(f"/api/projects/{proj.id}/")
        self.assertEqual(unrelated_get.status_code, status.HTTP_404_NOT_FOUND)


class IsNForgeAdminPermissionUnitTests(TestCase):
    def setUp(self):
        self.permission = IsNForgeAdmin()

    def test_anonymous_user_denied(self):
        class MockRequest:
            user = None

        self.assertFalse(self.permission.has_permission(MockRequest(), None))

    def test_unauthenticated_user_denied(self):
        class MockUser:
            is_authenticated = False
            is_staff = False
            is_superuser = False

        class MockRequest:
            user = MockUser()

        self.assertFalse(self.permission.has_permission(MockRequest(), None))

    def test_normal_authenticated_user_denied(self):
        class MockUser:
            is_authenticated = True
            is_staff = False
            is_superuser = False

        class MockRequest:
            user = MockUser()

        self.assertFalse(self.permission.has_permission(MockRequest(), None))

    def test_staff_user_allowed(self):
        class MockUser:
            is_authenticated = True
            is_staff = True
            is_superuser = False

        class MockRequest:
            user = MockUser()

        self.assertTrue(self.permission.has_permission(MockRequest(), None))

    def test_superuser_allowed(self):
        class MockUser:
            is_authenticated = True
            is_staff = False
            is_superuser = True

        class MockRequest:
            user = MockUser()

        self.assertTrue(self.permission.has_permission(MockRequest(), None))


class AdminUserManagementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = "/api/admin/users/"

        # Normal user
        self.normal_user = User.objects.create_user(
            username="normaluser", password="password123", email="normal@example.com"
        )

        # Staff user
        self.staff_user = User.objects.create_user(
            username="staffadmin",
            password="password123",
            email="staff@example.com",
            is_staff=True,
        )

        # Superuser
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            password="password123",
            email="super@example.com",
        )

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests to user list and detail must return 401."""
        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)

        res_detail = self.client.get(f"{self.list_url}{self.normal_user.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_receives_403(self):
        """Normal authenticated users must be denied with 403."""
        self.client.force_authenticate(user=self.normal_user)
        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        res_detail = self.client.get(f"{self.list_url}{self.normal_user.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_owner_receives_403(self):
        """Project owners without staff/superuser flags must be denied with 403."""
        owner = User.objects.create_user(username="owner_user", password="pw")
        Project.objects.create(owner=owner, title="Owner Proj")

        self.client.force_authenticate(user=owner)
        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        res_detail = self.client.get(f"{self.list_url}{self.normal_user.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_receives_403(self):
        """Project editors must be denied with 403."""
        owner = User.objects.create_user(username="owner_u2", password="pw")
        editor = User.objects.create_user(username="editor_u2", password="pw")
        proj = Project.objects.create(owner=owner, title="Collab Proj")
        ProjectMember.objects.create(project=proj, user=editor, role=ProjectMember.ROLE_EDITOR)

        self.client.force_authenticate(user=editor)
        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        res_detail = self.client.get(f"{self.list_url}{self.normal_user.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_receives_403(self):
        """Project viewers must be denied with 403."""
        owner = User.objects.create_user(username="owner_u3", password="pw")
        viewer = User.objects.create_user(username="viewer_u3", password="pw")
        proj = Project.objects.create(owner=owner, title="Collab Proj 2")
        ProjectMember.objects.create(project=proj, user=viewer, role=ProjectMember.ROLE_VIEWER)

        self.client.force_authenticate(user=viewer)
        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        res_detail = self.client.get(f"{self.list_url}{self.normal_user.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_users(self):
        """Admin (staff) can successfully list users."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertGreaterEqual(response.data["count"], 3)

    def test_admin_can_search_users_by_username_and_email(self):
        """Admin can search users by username and email substring."""
        User.objects.create_user(username="unique_researcher", email="unique@lab.org", password="pw")
        User.objects.create_user(username="other_scholar", email="scholar@quantum.io", password="pw")

        self.client.force_authenticate(user=self.staff_user)

        # Search by username
        res_user = self.client.get(f"{self.list_url}?search=unique_researcher")
        self.assertEqual(res_user.status_code, status.HTTP_200_OK)
        self.assertEqual(res_user.data["count"], 1)
        self.assertEqual(res_user.data["results"][0]["username"], "unique_researcher")

        # Search by email
        res_email = self.client.get(f"{self.list_url}?search=quantum.io")
        self.assertEqual(res_email.status_code, status.HTTP_200_OK)
        self.assertEqual(res_email.data["count"], 1)
        self.assertEqual(res_email.data["results"][0]["email"], "scholar@quantum.io")

    def test_admin_can_retrieve_user_details(self):
        """Admin can retrieve full user details including project memberships."""
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(f"{self.list_url}{self.normal_user.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.normal_user.id)
        self.assertEqual(res.data["username"], "normaluser")
        self.assertEqual(res.data["email"], "normal@example.com")
        self.assertIn("projects", res.data)
        self.assertIn("project_count", res.data)
        self.assertIn("membership_count", res.data)

    def test_sensitive_fields_not_returned(self):
        """Sensitive credential fields (passwords, tokens) must never be returned."""
        self.client.force_authenticate(user=self.superuser)

        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        first_user = res_list.data["results"][0]
        self.assertNotIn("password", first_user)
        self.assertNotIn("token", first_user)
        self.assertNotIn("auth_token", first_user)

        res_detail = self.client.get(f"{self.list_url}{self.normal_user.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertNotIn("password", res_detail.data)
        self.assertNotIn("token", res_detail.data)
        self.assertNotIn("auth_token", res_detail.data)

    def test_project_count_and_membership_count_are_correct(self):
        """Verify project_count counts owned projects and membership_count counts member projects."""
        test_user = User.objects.create_user(username="metric_user", password="pw")
        other_user = User.objects.create_user(username="other_owner", password="pw")

        # 2 owned projects
        p1 = Project.objects.create(owner=test_user, title="Owned 1")
        p2 = Project.objects.create(owner=test_user, title="Owned 2")

        # 1 invited project as EDITOR
        p_shared = Project.objects.create(owner=other_user, title="Shared Project")
        ProjectMember.objects.create(project=p_shared, user=test_user, role=ProjectMember.ROLE_EDITOR)

        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(f"{self.list_url}{test_user.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["project_count"], 2)
        self.assertEqual(res.data["membership_count"], 1)

    def test_user_project_roles_are_correct(self):
        """User detail projects array contains correct roles ('OWNER', 'EDITOR', 'VIEWER')."""
        researcher = User.objects.create_user(username="role_researcher", password="pw")
        other_lead = User.objects.create_user(username="other_lead", password="pw")

        # Owned project
        proj_owned = Project.objects.create(owner=researcher, title="Lead Project")
        Paper.objects.create(project=proj_owned, title="Paper 1", file="papers/p1.pdf")

        # Member project
        proj_collab = Project.objects.create(owner=other_lead, title="Collaboration Lab")
        ProjectMember.objects.create(project=proj_collab, user=researcher, role=ProjectMember.ROLE_VIEWER)

        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(f"{self.list_url}{researcher.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        projects = res.data["projects"]
        self.assertEqual(len(projects), 2)

        roles_map = {p["id"]: p["role"] for p in projects}
        self.assertEqual(roles_map[proj_owned.id], ProjectMember.ROLE_OWNER)
        self.assertEqual(roles_map[proj_collab.id], ProjectMember.ROLE_VIEWER)

    def test_pagination_works(self):
        """Pagination returns accurate count, total_pages, and sliced results."""
        # Create 12 additional users
        for i in range(12):
            User.objects.create_user(username=f"page_user_{i}", password="pw")

        self.client.force_authenticate(user=self.staff_user)
        res_p1 = self.client.get(f"{self.list_url}?page=1&page_size=10")
        self.assertEqual(res_p1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_p1.data["results"]), 10)
        self.assertIsNotNone(res_p1.data["next"])
        self.assertGreater(res_p1.data["total_pages"], 1)

        res_p2 = self.client.get(f"{self.list_url}?page=2&page_size=10")
        self.assertEqual(res_p2.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_p2.data["results"]), 2)


class AdminProjectManagementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = "/api/admin/projects/"

        # Users
        self.staff_admin = User.objects.create_user(
            username="staff_admin_proj",
            password="password123",
            email="staff_proj@example.com",
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="super_admin_proj",
            password="password123",
            email="super_proj@example.com",
        )
        self.project_owner = User.objects.create_user(
            username="proj_owner_user",
            password="password123",
            email="owner_proj@example.com",
        )
        self.editor = User.objects.create_user(
            username="proj_editor_user",
            password="password123",
            email="editor_proj@example.com",
        )
        self.viewer = User.objects.create_user(
            username="proj_viewer_user",
            password="password123",
            email="viewer_proj@example.com",
        )
        self.normal_user = User.objects.create_user(
            username="regular_user_proj",
            password="password123",
            email="regular_proj@example.com",
        )

        # Primary test project
        self.project = Project.objects.create(
            owner=self.project_owner,
            title="Quantum Circuit Synthesis",
            description="Exploration of fault-tolerant quantum compilation.",
        )

        # Project members
        self.member_editor = ProjectMember.objects.create(
            project=self.project, user=self.editor, role=ProjectMember.ROLE_EDITOR
        )
        self.member_viewer = ProjectMember.objects.create(
            project=self.project, user=self.viewer, role=ProjectMember.ROLE_VIEWER
        )

        # Papers
        self.paper1 = Paper.objects.create(
            project=self.project,
            title="Topological Braiding and Clifford Gates",
            file="papers/braiding.pdf",
            extracted_text="SUPER_SECRET_EXTRACTED_PAPER_TEXT_DO_NOT_LEAK",
        )
        self.paper2 = Paper.objects.create(
            project=self.project,
            title="Surface Codes Optimization",
            file="papers/surface.pdf",
            extracted_text="ANOTHER_SECRET_EXTRACTED_TEXT",
        )

        # Research Session & Messages
        self.session = ResearchSession.objects.create(
            project=self.project,
            title="Compilation Benchmarking Session",
        )
        self.session.papers.add(self.paper1, self.paper2)
        self.msg_user = ResearchMessage.objects.create(
            session=self.session,
            role=ResearchMessage.ROLE_USER,
            content="SECRET_USER_PROMPT_THAT_SHOULD_NEVER_BE_EXPOSED",
        )
        self.msg_assistant = ResearchMessage.objects.create(
            session=self.session,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="SECRET_AI_GENERATED_RESPONSE_BODY",
        )
        self.evidence = ResearchEvidence.objects.create(
            message=self.msg_assistant,
            paper=self.paper1,
            text="SECRET_EVIDENCE_EXCERPT_TEXT",
        )

    def test_admin_can_list_projects(self):
        """Staff and superuser admins can retrieve list of projects."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertGreaterEqual(res.data["count"], 1)

        # Verify superuser can also access
        self.client.force_authenticate(user=self.superuser)
        res_super = self.client.get(self.list_url)
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)

    def test_admin_can_search_projects(self):
        """Case-insensitive search queries match project title."""
        Project.objects.create(
            owner=self.project_owner,
            title="Neural Quantum State Tomography",
            description="Deep learning for density matrices",
        )

        self.client.force_authenticate(user=self.staff_admin)

        # Search match "quantum"
        res = self.client.get(f"{self.list_url}?search=quantum")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

        # Search match "tomography"
        res2 = self.client.get(f"{self.list_url}?search=tomography")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["count"], 1)
        self.assertEqual(res2.data["results"][0]["title"], "Neural Quantum State Tomography")

        # Search match none
        res3 = self.client.get(f"{self.list_url}?search=nonexistenttermxyz")
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(res3.data["count"], 0)

    def test_admin_can_retrieve_project_details(self):
        """Admin can retrieve full project details."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.project.id)
        self.assertEqual(res.data["title"], "Quantum Circuit Synthesis")
        self.assertIn("owner", res.data)
        self.assertIn("members", res.data)
        self.assertIn("papers", res.data)
        self.assertIn("research_sessions", res.data)

    def test_normal_user_receives_403(self):
        """Regular users receive 403 on admin project endpoints."""
        self.client.force_authenticate(user=self.normal_user)

        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        res_detail = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_editor_viewer_receive_403(self):
        """Project owners, editors, and viewers without staff status receive 403."""
        for u in [self.project_owner, self.editor, self.viewer]:
            self.client.force_authenticate(user=u)
            res_list = self.client.get(self.list_url)
            self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

            res_detail = self.client.get(f"{self.list_url}{self.project.id}/")
            self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests are rejected with 401."""
        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)

        res_detail = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_paper_count_is_correct(self):
        """Paper count correctly counts papers associated with the project."""
        self.client.force_authenticate(user=self.staff_admin)

        # List view check
        res_list = self.client.get(self.list_url)
        item = next(p for p in res_list.data["results"] if p["id"] == self.project.id)
        self.assertEqual(item["paper_count"], 2)

        # Detail view check
        res_detail = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res_detail.data["paper_count"], 2)

    def test_member_count_is_correct(self):
        """Member count correctly reflects members in ProjectMember."""
        self.client.force_authenticate(user=self.staff_admin)

        # List view check
        res_list = self.client.get(self.list_url)
        item = next(p for p in res_list.data["results"] if p["id"] == self.project.id)
        self.assertEqual(item["member_count"], 2)

        # Detail view check
        res_detail = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res_detail.data["member_count"], 2)

    def test_session_count_is_correct(self):
        """Research session count accurately aggregates project sessions."""
        self.client.force_authenticate(user=self.staff_admin)

        # List view check
        res_list = self.client.get(self.list_url)
        item = next(p for p in res_list.data["results"] if p["id"] == self.project.id)
        self.assertEqual(item["research_session_count"], 1)

        # Detail view check
        res_detail = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res_detail.data["research_session_count"], 1)

    def test_owner_is_correct(self):
        """Project owner metadata is accurately serialized."""
        self.client.force_authenticate(user=self.staff_admin)

        res_detail = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res_detail.data["owner"]["id"], self.project_owner.id)
        self.assertEqual(res_detail.data["owner"]["username"], "proj_owner_user")
        self.assertEqual(res_detail.data["owner"]["email"], "owner_proj@example.com")
        self.assertEqual(res_detail.data["owner_id"], self.project_owner.id)
        self.assertEqual(res_detail.data["owner_username"], "proj_owner_user")

    def test_member_roles_are_correct(self):
        """Project detail includes members with their OWNER, EDITOR, and VIEWER roles."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        members = res.data["members"]
        roles_by_username = {m["username"]: m["role"] for m in members}

        self.assertIn("proj_owner_user", roles_by_username)
        self.assertEqual(roles_by_username["proj_owner_user"], ProjectMember.ROLE_OWNER)

        self.assertIn("proj_editor_user", roles_by_username)
        self.assertEqual(roles_by_username["proj_editor_user"], ProjectMember.ROLE_EDITOR)

        self.assertIn("proj_viewer_user", roles_by_username)
        self.assertEqual(roles_by_username["proj_viewer_user"], ProjectMember.ROLE_VIEWER)

    def test_paper_metadata_is_correct(self):
        """Paper metadata exposes safe fields only without full contents."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        papers = res.data["papers"]
        self.assertEqual(len(papers), 2)
        titles = {p["title"] for p in papers}
        self.assertIn("Topological Braiding and Clifford Gates", titles)
        self.assertIn("Surface Codes Optimization", titles)

        for p in papers:
            self.assertIn("id", p)
            self.assertIn("title", p)
            self.assertIn("file_name", p)
            self.assertIn("uploaded_at", p)
            self.assertNotIn("extracted_text", p)

    def test_sensitive_research_content_not_exposed(self):
        """Full paper text, prompts, research message contents, and credentials are never exposed."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(f"{self.list_url}{self.project.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload_str = str(res.data)

        # Paper contents
        self.assertNotIn("SUPER_SECRET_EXTRACTED_PAPER_TEXT_DO_NOT_LEAK", payload_str)
        self.assertNotIn("ANOTHER_SECRET_EXTRACTED_TEXT", payload_str)

        # AI prompts & research message contents
        self.assertNotIn("SECRET_USER_PROMPT_THAT_SHOULD_NEVER_BE_EXPOSED", payload_str)
        self.assertNotIn("SECRET_AI_GENERATED_RESPONSE_BODY", payload_str)
        self.assertNotIn("SECRET_EVIDENCE_EXCERPT_TEXT", payload_str)

        # Credentials
        self.assertNotIn("password", payload_str.lower())
        self.assertNotIn("auth_token", payload_str.lower())

    def test_pagination_works(self):
        """Pagination controls limit page results and compute total pages."""
        for i in range(12):
            Project.objects.create(
                owner=self.project_owner,
                title=f"Batch Project {i}",
            )

        self.client.force_authenticate(user=self.staff_admin)
        res_p1 = self.client.get(f"{self.list_url}?page=1&page_size=10")
        self.assertEqual(res_p1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_p1.data["results"]), 10)
        self.assertGreater(res_p1.data["total_pages"], 1)

        res_p2 = self.client.get(f"{self.list_url}?page=2&page_size=10")
        self.assertEqual(res_p2.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_p2.data["results"]), 3)

    def test_existing_project_permissions_unaffected(self):
        """Existing project API endpoints remain completely unaffected by Admin views."""
        self.client.force_authenticate(user=self.project_owner)
        res_owner = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.editor)
        res_editor = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(res_editor.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.normal_user)
        res_normal = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(res_normal.status_code, status.HTTP_404_NOT_FOUND)


class AdminPaperManagementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = "/api/admin/papers/"

        # Users
        self.staff_admin = User.objects.create_user(
            username="staff_paper_admin",
            password="password123",
            email="staff_paper@example.com",
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="super_paper_admin",
            password="password123",
            email="super_paper@example.com",
        )
        self.project_owner = User.objects.create_user(
            username="paper_owner_user",
            password="password123",
            email="owner_paper@example.com",
        )
        self.editor = User.objects.create_user(
            username="paper_editor_user",
            password="password123",
            email="editor_paper@example.com",
        )
        self.viewer = User.objects.create_user(
            username="paper_viewer_user",
            password="password123",
            email="viewer_paper@example.com",
        )
        self.normal_user = User.objects.create_user(
            username="regular_paper_user",
            password="password123",
            email="regular_paper@example.com",
        )

        # Projects
        self.project1 = Project.objects.create(
            owner=self.project_owner,
            title="Quantum Algorithms Lab",
            description="Exploration of variational quantum algorithms.",
        )
        self.project2 = Project.objects.create(
            owner=self.project_owner,
            title="Graph Neural Networks Research",
            description="Deep geometric learning on biological networks.",
        )

        # Members on project 1
        ProjectMember.objects.create(
            project=self.project1, user=self.editor, role=ProjectMember.ROLE_EDITOR
        )
        ProjectMember.objects.create(
            project=self.project1, user=self.viewer, role=ProjectMember.ROLE_VIEWER
        )

        # Paper 1: Processed with chunks and extracted text
        self.paper1 = Paper.objects.create(
            project=self.project1,
            title="Surface Codes and Fault Tolerance",
            file="papers/surface_codes.pdf",
            extracted_text="SUPER_SECRET_EXTRACTED_PAPER_TEXT_DO_NOT_LEAK",
        )
        # Chunks for Paper 1
        self.chunk1 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=0,
            page_number=1,
            text="CHUNK_0_SECRET_RAW_TEXT_SHOULD_NEVER_BE_EXPOSED",
        )
        self.chunk2 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=1,
            page_number=2,
            text="CHUNK_1_SECRET_RAW_TEXT_SHOULD_NEVER_BE_EXPOSED",
        )
        self.chunk3 = PaperChunk.objects.create(
            paper=self.paper1,
            chunk_index=2,
            page_number=3,
            text="CHUNK_2_SECRET_RAW_TEXT_SHOULD_NEVER_BE_EXPOSED",
        )

        # Paper 2: Unprocessed (zero chunks, empty extracted_text)
        self.paper2 = Paper.objects.create(
            project=self.project2,
            title="Message Passing Architectures in Proteomics",
            file="papers/gnn_proteomics.pdf",
            extracted_text="",
        )

        # Research Session & Evidence on project 1
        self.session = ResearchSession.objects.create(
            project=self.project1,
            title="Tolerance Benchmarks",
        )
        self.session.papers.add(self.paper1)
        self.msg_assistant = ResearchMessage.objects.create(
            session=self.session,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="SECRET_RESEARCH_MESSAGE_CONTENT",
        )
        self.evidence = ResearchEvidence.objects.create(
            message=self.msg_assistant,
            paper=self.paper1,
            text="SECRET_RESEARCH_EVIDENCE_EXCERPT",
        )

    def test_admin_can_list_papers(self):
        """Staff and superuser admins can retrieve list of papers."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertGreaterEqual(res.data["count"], 2)

        # Verify superuser can also access
        self.client.force_authenticate(user=self.superuser)
        res_super = self.client.get(self.list_url)
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)

    def test_admin_can_search_papers(self):
        """Case-insensitive search queries match paper title."""
        self.client.force_authenticate(user=self.staff_admin)

        # Search match "surface"
        res = self.client.get(f"{self.list_url}?search=surface")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], self.paper1.id)

        # Search match "passing"
        res2 = self.client.get(f"{self.list_url}?search=passing")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["count"], 1)
        self.assertEqual(res2.data["results"][0]["id"], self.paper2.id)

        # Search match none
        res3 = self.client.get(f"{self.list_url}?search=nonexistenttermxyz")
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(res3.data["count"], 0)

    def test_admin_can_filter_by_project(self):
        """Filtering by project ID isolates papers belonging to that project."""
        self.client.force_authenticate(user=self.staff_admin)

        # Project 1 filter
        res1 = self.client.get(f"{self.list_url}?project={self.project1.id}")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["count"], 1)
        self.assertEqual(res1.data["results"][0]["id"], self.paper1.id)

        # Project 2 filter
        res2 = self.client.get(f"{self.list_url}?project={self.project2.id}")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["count"], 1)
        self.assertEqual(res2.data["results"][0]["id"], self.paper2.id)

    def test_admin_can_retrieve_paper_details(self):
        """Admin can retrieve full paper details with chunk summaries."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.paper1.id)
        self.assertEqual(res.data["title"], "Surface Codes and Fault Tolerance")
        self.assertIn("project", res.data)
        self.assertIn("chunks", res.data)
        self.assertIn("processing_status", res.data)
        self.assertEqual(len(res.data["chunks"]), 3)

    def test_normal_user_receives_403(self):
        """Regular users receive 403 on admin paper endpoints."""
        self.client.force_authenticate(user=self.normal_user)

        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        res_detail = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_editor_viewer_receive_403(self):
        """Project owners, editors, and viewers without staff status receive 403."""
        for u in [self.project_owner, self.editor, self.viewer]:
            self.client.force_authenticate(user=u)
            res_list = self.client.get(self.list_url)
            self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

            res_detail = self.client.get(f"{self.list_url}{self.paper1.id}/")
            self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests are rejected with 401."""
        res_list = self.client.get(self.list_url)
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)

        res_detail = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_project_and_owner_metadata_are_correct(self):
        """Paper reflects associated project and project owner metadata accurately."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["project_id"], self.project1.id)
        self.assertEqual(res.data["project_title"], "Quantum Algorithms Lab")
        self.assertEqual(res.data["project_owner"], "paper_owner_user")
        self.assertEqual(res.data["project"]["title"], "Quantum Algorithms Lab")
        self.assertEqual(res.data["project"]["owner"]["username"], "paper_owner_user")

    def test_chunk_count_is_correct(self):
        """Chunk count reflects generated paper chunks."""
        self.client.force_authenticate(user=self.staff_admin)

        # Paper 1 has 3 chunks
        res1 = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertEqual(res1.data["chunk_count"], 3)

        # Paper 2 has 0 chunks
        res2 = self.client.get(f"{self.list_url}{self.paper2.id}/")
        self.assertEqual(res2.data["chunk_count"], 0)

    def test_processing_metadata_is_correct(self):
        """Processing metadata and status filter reflect chunk and text availability."""
        self.client.force_authenticate(user=self.staff_admin)

        # Detail checks for processed paper
        res1 = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertEqual(res1.data["processing_status"], "PROCESSED")
        self.assertEqual(res1.data["page_count"], 3)
        self.assertTrue(res1.data["has_extracted_text"])
        self.assertGreater(res1.data["extracted_text_length"], 0)

        # Detail checks for pending paper
        res2 = self.client.get(f"{self.list_url}{self.paper2.id}/")
        self.assertEqual(res2.data["processing_status"], "PENDING")
        self.assertFalse(res2.data["has_extracted_text"])
        self.assertEqual(res2.data["extracted_text_length"], 0)

        # Filter by status: PROCESSED
        res_proc = self.client.get(f"{self.list_url}?status=PROCESSED")
        self.assertEqual(res_proc.status_code, status.HTTP_200_OK)
        proc_ids = [p["id"] for p in res_proc.data["results"]]
        self.assertIn(self.paper1.id, proc_ids)
        self.assertNotIn(self.paper2.id, proc_ids)

        # Filter by status: PENDING
        res_pend = self.client.get(f"{self.list_url}?status=PENDING")
        self.assertEqual(res_pend.status_code, status.HTTP_200_OK)
        pend_ids = [p["id"] for p in res_pend.data["results"]]
        self.assertIn(self.paper2.id, pend_ids)
        self.assertNotIn(self.paper1.id, pend_ids)

    def test_sensitive_extracted_text_not_returned(self):
        """Full extracted paper text is never returned in list or detail."""
        self.client.force_authenticate(user=self.staff_admin)

        res_list = self.client.get(self.list_url)
        self.assertNotIn("SUPER_SECRET_EXTRACTED_PAPER_TEXT_DO_NOT_LEAK", str(res_list.data))

        res_detail = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertNotIn("SUPER_SECRET_EXTRACTED_PAPER_TEXT_DO_NOT_LEAK", str(res_detail.data))

    def test_full_chunk_text_not_returned(self):
        """Raw chunk text is omitted from chunk summary representations."""
        self.client.force_authenticate(user=self.staff_admin)
        res_detail = self.client.get(f"{self.list_url}{self.paper1.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)

        payload_str = str(res_detail.data)
        self.assertNotIn("CHUNK_0_SECRET_RAW_TEXT_SHOULD_NEVER_BE_EXPOSED", payload_str)
        self.assertNotIn("CHUNK_1_SECRET_RAW_TEXT_SHOULD_NEVER_BE_EXPOSED", payload_str)
        self.assertNotIn("CHUNK_2_SECRET_RAW_TEXT_SHOULD_NEVER_BE_EXPOSED", payload_str)

    def test_research_content_not_returned(self):
        """Research messages, prompts, and evidence are not exposed through paper endpoints."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(f"{self.list_url}{self.paper1.id}/")

        payload_str = str(res.data)
        self.assertNotIn("SECRET_RESEARCH_MESSAGE_CONTENT", payload_str)
        self.assertNotIn("SECRET_RESEARCH_EVIDENCE_EXCERPT", payload_str)
        self.assertNotIn("password", payload_str.lower())
        self.assertNotIn("auth_token", payload_str.lower())

    def test_pagination_works(self):
        """Pagination returns accurate count, total_pages, and sliced results."""
        for i in range(12):
            Paper.objects.create(
                project=self.project1,
                title=f"Batch Paper {i}",
                file=f"papers/batch_{i}.pdf",
            )

        self.client.force_authenticate(user=self.staff_admin)
        res_p1 = self.client.get(f"{self.list_url}?page=1&page_size=10")
        self.assertEqual(res_p1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_p1.data["results"]), 10)
        self.assertGreater(res_p1.data["total_pages"], 1)

        res_p2 = self.client.get(f"{self.list_url}?page=2&page_size=10")
        self.assertEqual(res_p2.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_p2.data["results"]), 4)

    def test_existing_paper_permissions_unaffected(self):
        """Existing paper APIs retain their authorization rules."""
        self.client.force_authenticate(user=self.project_owner)
        res_owner = self.client.get(f"/api/projects/{self.project1.id}/papers/")
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.editor)
        res_editor = self.client.get(f"/api/projects/{self.project1.id}/papers/")
        self.assertEqual(res_editor.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.normal_user)
        res_normal = self.client.get(f"/api/projects/{self.project1.id}/papers/")
        self.assertEqual(res_normal.status_code, status.HTTP_404_NOT_FOUND)


class AdminActivityOverviewAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/admin/activity/"

        # Users
        self.staff_admin = User.objects.create_user(
            username="activity_staff_admin",
            password="password123",
            email="activity_staff@example.com",
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="activity_super_admin",
            password="password123",
            email="activity_super@example.com",
        )
        self.project_owner = User.objects.create_user(
            username="activity_owner_user",
            password="password123",
            email="activity_owner@example.com",
        )
        self.editor = User.objects.create_user(
            username="activity_editor_user",
            password="password123",
            email="activity_editor@example.com",
        )
        self.viewer = User.objects.create_user(
            username="activity_viewer_user",
            password="password123",
            email="activity_viewer@example.com",
        )
        self.normal_user = User.objects.create_user(
            username="activity_regular_user",
            password="password123",
            email="activity_regular@example.com",
        )

        # Projects
        self.project1 = Project.objects.create(
            owner=self.project_owner,
            title="Activity Test Project 1",
            description="First project for activity verification.",
        )
        self.project2 = Project.objects.create(
            owner=self.project_owner,
            title="Activity Test Project 2",
            description="Second project for activity verification.",
        )

        # Members
        ProjectMember.objects.create(
            project=self.project1, user=self.editor, role=ProjectMember.ROLE_EDITOR
        )
        ProjectMember.objects.create(
            project=self.project1, user=self.viewer, role=ProjectMember.ROLE_VIEWER
        )

        # Papers
        self.paper1 = Paper.objects.create(
            project=self.project1,
            title="Activity Paper 1",
            file="papers/act1.pdf",
            extracted_text="SECRET_PAPER_1_TEXT",
        )
        self.paper2 = Paper.objects.create(
            project=self.project2,
            title="Activity Paper 2",
            file="papers/act2.pdf",
            extracted_text="SECRET_PAPER_2_TEXT",
        )

        # Research Session & Messages
        self.session1 = ResearchSession.objects.create(
            project=self.project1,
            title="Activity Session 1",
        )
        self.session2 = ResearchSession.objects.create(
            project=self.project2,
            title="Activity Session 2",
        )

        self.msg = ResearchMessage.objects.create(
            session=self.session1,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="SECRET_ACTIVITY_MESSAGE_CONTENT",
        )
        self.evidence = ResearchEvidence.objects.create(
            message=self.msg,
            paper=self.paper1,
            text="SECRET_ACTIVITY_EVIDENCE_TEXT",
        )

    def test_admin_receives_200(self):
        """Staff and superuser receive 200 with activity data."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("total_users", res.data)
        self.assertIn("recent_users", res.data)
        self.assertIn("recent_papers", res.data)
        self.assertIn("recent_research_sessions", res.data)

        # Superuser verification
        self.client.force_authenticate(user=self.superuser)
        res_super = self.client.get(self.url)
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)

    def test_unauthenticated_receives_401(self):
        """Unauthenticated requests are rejected with 401."""
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_users_owners_editors_viewers_receive_403(self):
        """Non-admin users receive 403 on activity overview."""
        for u in [self.normal_user, self.project_owner, self.editor, self.viewer]:
            self.client.force_authenticate(user=u)
            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_aggregate_counts_are_correct(self):
        """Activity overview returns exact aggregate counts across all platform entities."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["total_users"], User.objects.count())
        self.assertEqual(res.data["total_projects"], Project.objects.count())
        self.assertEqual(res.data["total_papers"], Paper.objects.count())
        self.assertEqual(res.data["total_research_sessions"], ResearchSession.objects.count())
        self.assertEqual(res.data["total_research_messages"], ResearchMessage.objects.count())

    def test_recent_activity_ordering(self):
        """Recent activity items are ordered with the most recent first."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Users ordering
        users = res.data["recent_users"]
        self.assertGreater(len(users), 0)
        user_dates = [u["date_joined"] for u in users]
        self.assertEqual(user_dates, sorted(user_dates, reverse=True))

        # Papers ordering
        papers = res.data["recent_papers"]
        self.assertGreater(len(papers), 0)
        paper_dates = [p["uploaded_at"] for p in papers]
        self.assertEqual(paper_dates, sorted(paper_dates, reverse=True))

        # Sessions ordering
        sessions = res.data["recent_research_sessions"]
        self.assertGreater(len(sessions), 0)
        session_dates = [s["updated_at"] for s in sessions]
        self.assertEqual(session_dates, sorted(session_dates, reverse=True))

    def test_sensitive_research_content_not_returned(self):
        """Extracted text, prompts, research message contents, and credentials are omitted."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload_str = str(res.data)
        self.assertNotIn("SECRET_PAPER_1_TEXT", payload_str)
        self.assertNotIn("SECRET_PAPER_2_TEXT", payload_str)
        self.assertNotIn("SECRET_ACTIVITY_MESSAGE_CONTENT", payload_str)
        self.assertNotIn("SECRET_ACTIVITY_EVIDENCE_TEXT", payload_str)
        self.assertNotIn("password", payload_str.lower())
        self.assertNotIn("auth_token", payload_str.lower())

    def test_existing_functionality_unaffected(self):
        """Previous Phase 8.1, 8.2, 8.3, and 8.4 endpoints continue operating normally."""
        self.client.force_authenticate(user=self.staff_admin)

        # Dashboard
        res_dash = self.client.get("/api/admin/dashboard/")
        self.assertEqual(res_dash.status_code, status.HTTP_200_OK)

        # Users
        res_users = self.client.get("/api/admin/users/")
        self.assertEqual(res_users.status_code, status.HTTP_200_OK)

        # Projects
        res_proj = self.client.get("/api/admin/projects/")
        self.assertEqual(res_proj.status_code, status.HTTP_200_OK)

        # Papers
        res_papers = self.client.get("/api/admin/papers/")
        self.assertEqual(res_papers.status_code, status.HTTP_200_OK)


class AdminAIUsageAPITests(TestCase):
    """
    Focused tests for Phase 8.5.2 Admin AI Usage Monitoring.
    Validates permissions, aggregation, filtering, pagination,
    sensitive content exclusion, and non-regression.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/admin/ai-usage/"

        # Users
        self.superuser = User.objects.create_superuser(
            username="ai_admin_super",
            password="password123",
            email="ai_super@example.com",
        )
        self.staff_admin = User.objects.create_user(
            username="ai_admin_staff",
            password="password123",
            email="ai_staff@example.com",
            is_staff=True,
        )
        self.project_owner = User.objects.create_user(
            username="ai_owner_user",
            password="password123",
            email="ai_owner@example.com",
        )
        self.editor = User.objects.create_user(
            username="ai_editor_user",
            password="password123",
            email="ai_editor@example.com",
        )
        self.viewer = User.objects.create_user(
            username="ai_viewer_user",
            password="password123",
            email="ai_viewer@example.com",
        )
        self.normal_user = User.objects.create_user(
            username="ai_normal_user",
            password="password123",
            email="ai_normal@example.com",
        )

        # Projects
        self.project1 = Project.objects.create(
            owner=self.project_owner,
            title="Genomics Neural Nets",
            description="Deep learning for genomics variant inference.",
        )
        self.project2 = Project.objects.create(
            owner=self.normal_user,
            title="Quantum Photonic Networks",
            description="Photonic circuit modeling.",
        )

        # Memberships
        ProjectMember.objects.create(
            project=self.project1, user=self.editor, role=ProjectMember.ROLE_EDITOR
        )
        ProjectMember.objects.create(
            project=self.project1, user=self.viewer, role=ProjectMember.ROLE_VIEWER
        )

        # Papers
        self.paper1 = Paper.objects.create(
            project=self.project1,
            title="Variant Calling via Transformers",
            file="papers/variant.pdf",
            extracted_text="CONFIDENTIAL_GENOMIC_PAPER_TEXT_DO_NOT_EXPOSE",
        )
        self.paper2 = Paper.objects.create(
            project=self.project2,
            title="Integrated Quantum Photonics",
            file="papers/photonics.pdf",
            extracted_text="CONFIDENTIAL_PHOTONIC_PAPER_TEXT_DO_NOT_EXPOSE",
        )

        # Sessions
        self.session1 = ResearchSession.objects.create(
            project=self.project1,
            title="Variant Calling Benchmark",
        )
        self.session2 = ResearchSession.objects.create(
            project=self.project2,
            title="Photonic Waveguide Study",
        )

        # AI Messages in Project 1
        # 1. Ask AI (Q&A)
        self.msg_qna = ResearchMessage.objects.create(
            session=self.session1,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="The model achieves high F1 score on indel detection.",
        )
        ResearchEvidence.objects.create(
            message=self.msg_qna,
            paper=self.paper1,
            text="CONFIDENTIAL_EVIDENCE_EXCERPT_ONE",
        )

        # 2. Research Gap Analysis
        gap_content = json.dumps({
            "common_limitations": ["Limited dataset for rare variants"],
            "methodological_gaps": ["Requires high compute cluster"],
            "dataset_population_gaps": ["European ancestry bias"],
        })
        self.msg_gap = ResearchMessage.objects.create(
            session=self.session1,
            role=ResearchMessage.ROLE_ASSISTANT,
            content=gap_content,
        )

        # 3. Paper Comparison
        compare_content = json.dumps({
            "similarities": ["Both evaluate precision on benchmarks"],
            "differences": ["Paper A uses CNN, Paper B uses Transformer"],
            "methodology_comparison": ["Different loss functions"],
        })
        self.msg_compare = ResearchMessage.objects.create(
            session=self.session1,
            role=ResearchMessage.ROLE_ASSISTANT,
            content=compare_content,
        )

        # 4. Thematic Analysis
        thematic_content = json.dumps({
            "themes": [{"title": "Algorithmic Efficiency", "description": "Scaling laws"}]
        })
        self.msg_thematic = ResearchMessage.objects.create(
            session=self.session1,
            role=ResearchMessage.ROLE_ASSISTANT,
            content=thematic_content,
        )

        # 5. Trend Analysis
        trend_content = json.dumps({
            "research_evolution": [{"stage": "Foundational Phase", "year": "2022"}]
        })
        self.msg_trend = ResearchMessage.objects.create(
            session=self.session1,
            role=ResearchMessage.ROLE_ASSISTANT,
            content=trend_content,
        )

        # 6. User prompt message (not an assistant response)
        self.msg_user = ResearchMessage.objects.create(
            session=self.session1,
            role=ResearchMessage.ROLE_USER,
            content="CONFIDENTIAL_USER_PROMPT_DO_NOT_EXPOSE",
        )

        # 7. AI Message in Project 2 (Q&A)
        self.msg_project2 = ResearchMessage.objects.create(
            session=self.session2,
            role=ResearchMessage.ROLE_ASSISTANT,
            content="Waveguide transmission loss was measured at 0.1 dB/cm.",
        )

    def test_admin_receives_200(self):
        """Staff and superuser receive 200 with AI usage monitoring data."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("total_ai_activity", res.data)
        self.assertIn("operations_breakdown", res.data)
        self.assertIn("by_operation", res.data)
        self.assertIn("by_user", res.data)
        self.assertIn("by_project", res.data)
        self.assertIn("recent_activity", res.data)
        self.assertIn("results", res.data)
        self.assertIn("count", res.data)

        # Superuser verification
        self.client.force_authenticate(user=self.superuser)
        res_super = self.client.get(self.url)
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)

    def test_unauthenticated_receives_401(self):
        """Unauthenticated requests are rejected with 401."""
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_users_owners_editors_viewers_receive_403(self):
        """Non-admin users (normal, owner, editor, viewer) receive 403."""
        for u in [self.normal_user, self.project_owner, self.editor, self.viewer]:
            self.client.force_authenticate(user=u)
            res = self.client.get(self.url)
            self.assertEqual(
                res.status_code,
                status.HTTP_403_FORBIDDEN,
                f"User {u.username} should have received 403",
            )

    def test_aggregation_correctness(self):
        """AI usage aggregates match exact database records."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 6 assistant messages in total
        self.assertEqual(res.data["total_ai_activity"], 6)

        by_op = res.data["by_operation"]
        self.assertEqual(by_op["GAP_ANALYSIS"], 1)
        self.assertEqual(by_op["COMPARE_PAPERS"], 1)
        self.assertEqual(by_op["THEMATIC_ANALYSIS"], 1)
        self.assertEqual(by_op["RESEARCH_TRENDS"], 1)
        self.assertEqual(by_op["ASK_AI"], 2)

        # Verify operations_breakdown matches
        total_from_breakdown = sum(item["count"] for item in res.data["operations_breakdown"])
        self.assertEqual(total_from_breakdown, 6)

        # Verify by_user contains project_owner (5) and normal_user (1)
        user_counts = {u["username"]: u["count"] for u in res.data["by_user"]}
        self.assertEqual(user_counts.get("ai_owner_user"), 5)
        self.assertEqual(user_counts.get("ai_normal_user"), 1)

        # Verify by_project contains project 1 (5) and project 2 (1)
        proj_counts = {p["project_title"]: p["count"] for p in res.data["by_project"]}
        self.assertEqual(proj_counts.get("Genomics Neural Nets"), 5)
        self.assertEqual(proj_counts.get("Quantum Photonic Networks"), 1)

    def test_operation_filtering(self):
        """Querying ?operation= filters activity log correctly."""
        self.client.force_authenticate(user=self.staff_admin)

        # Filter GAP_ANALYSIS
        res_gap = self.client.get(self.url, {"operation": "GAP_ANALYSIS"})
        self.assertEqual(res_gap.status_code, status.HTTP_200_OK)
        self.assertEqual(res_gap.data["count"], 1)
        self.assertEqual(res_gap.data["results"][0]["operation"], "GAP_ANALYSIS")

        # Filter COMPARE_PAPERS
        res_comp = self.client.get(self.url, {"operation": "COMPARE_PAPERS"})
        self.assertEqual(res_comp.status_code, status.HTTP_200_OK)
        self.assertEqual(res_comp.data["count"], 1)
        self.assertEqual(res_comp.data["results"][0]["operation"], "COMPARE_PAPERS")

        # Filter ASK_AI
        res_qna = self.client.get(self.url, {"operation": "ASK_AI"})
        self.assertEqual(res_qna.status_code, status.HTTP_200_OK)
        self.assertEqual(res_qna.data["count"], 2)
        for item in res_qna.data["results"]:
            self.assertEqual(item["operation"], "ASK_AI")

    def test_project_and_user_filtering(self):
        """Querying ?project_id= and ?user_id= filters records accurately."""
        self.client.force_authenticate(user=self.staff_admin)

        # Project 2 only
        res_proj = self.client.get(self.url, {"project_id": self.project2.id})
        self.assertEqual(res_proj.status_code, status.HTTP_200_OK)
        self.assertEqual(res_proj.data["count"], 1)
        self.assertEqual(res_proj.data["results"][0]["project_id"], self.project2.id)

        # User 1 only
        res_user = self.client.get(self.url, {"user_id": self.project_owner.id})
        self.assertEqual(res_user.status_code, status.HTTP_200_OK)
        self.assertEqual(res_user.data["count"], 5)

    def test_pagination(self):
        """Pagination returns expected chunking, next/previous links, and count."""
        # Create 12 more assistant messages to exceed page_size=10
        for i in range(12):
            ResearchMessage.objects.create(
                session=self.session1,
                role=ResearchMessage.ROLE_ASSISTANT,
                content=f"Pagination test answer #{i}",
            )

        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url, {"page": 1, "page_size": 10})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 18)
        self.assertEqual(len(res.data["results"]), 10)
        self.assertEqual(res.data["total_pages"], 2)
        self.assertEqual(res.data["current_page"], 1)
        self.assertIsNotNone(res.data["next"])
        self.assertIsNone(res.data["previous"])

        # Page 2
        res2 = self.client.get(self.url, {"page": 2, "page_size": 10})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res2.data["results"]), 8)
        self.assertEqual(res2.data["current_page"], 2)
        self.assertIsNone(res2.data["next"])
        self.assertIsNotNone(res2.data["previous"])

    def test_sensitive_content_exclusion(self):
        """Prompts, message contents, extracted texts, and credentials are never exposed."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload_str = str(res.data)
        self.assertNotIn("CONFIDENTIAL_USER_PROMPT_DO_NOT_EXPOSE", payload_str)
        self.assertNotIn("The model achieves high F1 score on indel detection.", payload_str)
        self.assertNotIn("CONFIDENTIAL_GENOMIC_PAPER_TEXT_DO_NOT_EXPOSE", payload_str)
        self.assertNotIn("CONFIDENTIAL_PHOTONIC_PAPER_TEXT_DO_NOT_EXPOSE", payload_str)
        self.assertNotIn("CONFIDENTIAL_EVIDENCE_EXCERPT_ONE", payload_str)
        self.assertNotIn("password", payload_str.lower())
        self.assertNotIn("auth_token", payload_str.lower())

        # Verify no item has a 'content' field
        for item in res.data["results"]:
            self.assertNotIn("content", item)
            self.assertNotIn("text", item)

    def test_existing_ai_and_admin_endpoints_unaffected(self):
        """Existing AI health endpoint and earlier admin endpoints remain intact."""
        self.client.force_authenticate(user=self.staff_admin)

        # AI health
        res_ai_health = self.client.get("/api/ai/health/")
        self.assertEqual(res_ai_health.status_code, status.HTTP_200_OK)

        # Admin dashboard
        res_dash = self.client.get("/api/admin/dashboard/")
        self.assertEqual(res_dash.status_code, status.HTTP_200_OK)

        # Admin activity
        res_act = self.client.get("/api/admin/activity/")
        self.assertEqual(res_act.status_code, status.HTTP_200_OK)

        # Admin users & papers
        res_users = self.client.get("/api/admin/users/")
        self.assertEqual(res_users.status_code, status.HTTP_200_OK)
        res_papers = self.client.get("/api/admin/papers/")
        self.assertEqual(res_papers.status_code, status.HTTP_200_OK)


class AdminActivityDetailAPITests(TestCase):
    """
    Focused tests for Phase 8.5.3 Admin Activity Detail.
    Validates permissions, 404 on nonexistent, complete relationship metadata,
    operation classification, and strict exclusion of private research content.
    """

    def setUp(self):
        self.client = APIClient()

        # Users
        self.superuser = User.objects.create_superuser(
            username="detail_super",
            password="password123",
            email="detail_super@example.com",
        )
        self.staff_admin = User.objects.create_user(
            username="detail_staff",
            password="password123",
            email="detail_staff@example.com",
            is_staff=True,
        )
        self.project_owner = User.objects.create_user(
            username="detail_owner",
            password="password123",
            email="detail_owner@example.com",
        )
        self.editor = User.objects.create_user(
            username="detail_editor",
            password="password123",
            email="detail_editor@example.com",
        )
        self.viewer = User.objects.create_user(
            username="detail_viewer",
            password="password123",
            email="detail_viewer@example.com",
        )
        self.normal_user = User.objects.create_user(
            username="detail_normal",
            password="password123",
            email="detail_normal@example.com",
        )

        # Project & Members
        self.project = Project.objects.create(
            owner=self.project_owner,
            title="CRISPR Off-Target Analysis",
            description="Deep sequencing of off-target edits.",
        )
        ProjectMember.objects.create(
            project=self.project, user=self.editor, role=ProjectMember.ROLE_EDITOR
        )
        ProjectMember.objects.create(
            project=self.project, user=self.viewer, role=ProjectMember.ROLE_VIEWER
        )

        # Paper & Chunk
        self.paper = Paper.objects.create(
            project=self.project,
            title="Guide RNA Specificity Optimization",
            file="papers/crispr.pdf",
            extracted_text="SECRET_EXTRACTED_PDF_TEXT_DO_NOT_EXPOSE",
        )
        self.chunk = PaperChunk.objects.create(
            paper=self.paper,
            chunk_index=0,
            page_number=3,
            text="SECRET_PAPER_CHUNK_TEXT_DO_NOT_EXPOSE",
            embedding=[0.1, 0.2, 0.3],
        )

        # Research Session
        self.session = ResearchSession.objects.create(
            project=self.project,
            title="Off-Target Cleavage Evaluation",
        )
        self.session.papers.add(self.paper)

        # Messages
        gap_json = json.dumps({
            "common_limitations": ["Cell-type specificity constraints"],
            "methodological_gaps": ["Lack of in vivo verification"],
        })
        self.msg_gap = ResearchMessage.objects.create(
            session=self.session,
            role=ResearchMessage.ROLE_ASSISTANT,
            content=f"SECRET_GAP_ASSISTANT_ANSWER_CONTENT {gap_json}",
        )
        self.evidence = ResearchEvidence.objects.create(
            message=self.msg_gap,
            paper=self.paper,
            chunk=self.chunk,
            page_number=3,
            text="SECRET_RESEARCH_EVIDENCE_TEXT_DO_NOT_EXPOSE",
        )

        self.msg_user = ResearchMessage.objects.create(
            session=self.session,
            role=ResearchMessage.ROLE_USER,
            content="SECRET_USER_PROMPT_CONTENT",
        )

        self.detail_url = f"/api/admin/activity/{self.msg_gap.id}/"

    def test_admin_can_retrieve_activity_detail(self):
        """Staff and superuser receive 200 with complete activity detail."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_fields = [
            "id", "session_id", "session_title", "project_id", "project_title",
            "project_owner", "user_id", "username", "user_role", "role", "message_role",
            "operation", "operation_name", "operation_type", "operation_display_name",
            "evidence_count", "has_evidence", "status", "related_papers", "citations",
            "privacy_notice", "created_at", "timestamp"
        ]
        for field in expected_fields:
            self.assertIn(field, res.data, f"Field '{field}' should be in detail response")

        # Superuser verification
        self.client.force_authenticate(user=self.superuser)
        res_super = self.client.get(self.detail_url)
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)

    def test_unauthenticated_receives_401(self):
        """Unauthenticated requests are rejected with 401."""
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_users_owners_editors_viewers_receive_403(self):
        """Non-admin users receive 403 when requesting activity detail."""
        for u in [self.normal_user, self.project_owner, self.editor, self.viewer]:
            self.client.force_authenticate(user=u)
            res = self.client.get(self.detail_url)
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_activity_returns_404(self):
        """Requesting an unknown activity ID returns 404."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get("/api/admin/activity/999999/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_correct_metadata_relationships_and_operation(self):
        """Activity detail accurately maps session, project, owner, and operation."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["id"], self.msg_gap.id)
        self.assertEqual(res.data["session_id"], self.session.id)
        self.assertEqual(res.data["session_title"], "Off-Target Cleavage Evaluation")
        self.assertEqual(res.data["project_id"], self.project.id)
        self.assertEqual(res.data["project_title"], "CRISPR Off-Target Analysis")
        self.assertEqual(res.data["username"], "detail_owner")
        self.assertEqual(res.data["user_role"], "OWNER")
        self.assertEqual(res.data["operation"], "GAP_ANALYSIS")
        self.assertEqual(res.data["operation_name"], "Research Gap Analysis")
        self.assertEqual(res.data["evidence_count"], 1)
        self.assertTrue(res.data["has_evidence"])
        self.assertEqual(res.data["status"], "COMPLETED")

        # Verify related papers
        self.assertEqual(len(res.data["related_papers"]), 1)
        paper_data = res.data["related_papers"][0]
        self.assertEqual(paper_data["id"], self.paper.id)
        self.assertEqual(paper_data["title"], "Guide RNA Specificity Optimization")

        # Verify citations
        self.assertEqual(len(res.data["citations"]), 1)
        citation_data = res.data["citations"][0]
        self.assertEqual(citation_data["paper_id"], self.paper.id)
        self.assertEqual(citation_data["page_number"], 3)

    def test_private_research_content_omitted(self):
        """Confidential prompts, assistant dialogue, and evidence texts are strictly omitted."""
        self.client.force_authenticate(user=self.staff_admin)
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload_str = str(res.data)
        self.assertNotIn("SECRET_GAP_ASSISTANT_ANSWER_CONTENT", payload_str)
        self.assertNotIn("SECRET_USER_PROMPT_CONTENT", payload_str)
        self.assertNotIn("SECRET_RESEARCH_EVIDENCE_TEXT_DO_NOT_EXPOSE", payload_str)
        self.assertNotIn("SECRET_PAPER_CHUNK_TEXT_DO_NOT_EXPOSE", payload_str)
        self.assertNotIn("SECRET_EXTRACTED_PDF_TEXT_DO_NOT_EXPOSE", payload_str)
        self.assertNotIn("password", payload_str.lower())
        self.assertNotIn("auth_token", payload_str.lower())

        self.assertNotIn("content", res.data)
        self.assertNotIn("text", res.data)


class AdminSecurityAuditHardeningTests(TestCase):
    """
    Comprehensive regression test suite for Phase 8.6.1 NForge Admin Security Audit and Hardening.
    Validates:
    A. Full Admin Authorization Matrix (all endpoints reject anon with 401, non-admins with 403, allow staff/super with 200)
    B. IDOR Defense & Nonexistent 404 handling across all detail endpoints
    C. Project & Paper boundary isolation
    D. Collaboration permission enforcement (invite, remove, cancel, accept, decline, leave)
    E. Research session & AI generation authorization (viewer rejection, mixed-project rejection, session mismatch)
    F. Strict exclusion of sensitive researcher data, passwords, embeddings, and raw text
    """

    def setUp(self):
        self.client = APIClient()

        # Users
        self.superuser = User.objects.create_superuser(
            username="sec_superuser",
            password="password123",
            email="sec_superuser@example.com",
        )
        self.staff_admin = User.objects.create_user(
            username="sec_staff",
            password="password123",
            email="sec_staff@example.com",
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            username="sec_normal",
            password="password123",
            email="sec_normal@example.com",
        )
        self.owner_a = User.objects.create_user(
            username="sec_owner_a",
            password="password123",
            email="sec_owner_a@example.com",
        )
        self.editor_a = User.objects.create_user(
            username="sec_editor_a",
            password="password123",
            email="sec_editor_a@example.com",
        )
        self.viewer_a = User.objects.create_user(
            username="sec_viewer_a",
            password="password123",
            email="sec_viewer_a@example.com",
        )
        self.unrelated_user = User.objects.create_user(
            username="sec_unrelated",
            password="password123",
            email="sec_unrelated@example.com",
        )

        # Project A
        self.project_a = Project.objects.create(
            owner=self.owner_a,
            title="Project A Security Analysis",
            description="Testing authorization fences.",
        )
        ProjectMember.objects.create(
            project=self.project_a, user=self.editor_a, role=ProjectMember.ROLE_EDITOR
        )
        ProjectMember.objects.create(
            project=self.project_a, user=self.viewer_a, role=ProjectMember.ROLE_VIEWER
        )

        # Papers in Project A
        self.paper_a1 = Paper.objects.create(
            project=self.project_a,
            title="Paper A1",
            file="papers/paper_a1.pdf",
            extracted_text="CONFIDENTIAL_TEXT_PROJECT_A1",
        )
        self.chunk_a1 = PaperChunk.objects.create(
            paper=self.paper_a1,
            chunk_index=0,
            page_number=1,
            text="CONFIDENTIAL_CHUNK_TEXT_A1",
            embedding=[0.01, 0.02, 0.03],
        )

        self.paper_a2 = Paper.objects.create(
            project=self.project_a,
            title="Paper A2",
            file="papers/paper_a2.pdf",
            extracted_text="CONFIDENTIAL_TEXT_PROJECT_A2",
        )

        # Research Session in Project A
        self.session_a = ResearchSession.objects.create(
            project=self.project_a,
            title="Session A",
        )
        self.session_a.papers.add(self.paper_a1, self.paper_a2)

        self.msg_a = ResearchMessage.objects.create(
            session=self.session_a,
            role=ResearchMessage.ROLE_ASSISTANT,
            content='{"themes": ["Security", "Hardening"]}',
        )
        self.evidence_a = ResearchEvidence.objects.create(
            message=self.msg_a,
            paper=self.paper_a1,
            chunk=self.chunk_a1,
            page_number=1,
            text="CONFIDENTIAL_EVIDENCE_TEXT_A1",
        )

        # Project B (isolated project belonging to unrelated user)
        self.project_b = Project.objects.create(
            owner=self.unrelated_user,
            title="Project B Isolated",
            description="Completely foreign project.",
        )
        self.paper_b1 = Paper.objects.create(
            project=self.project_b,
            title="Paper B1 Foreign",
            file="papers/paper_b1.pdf",
            extracted_text="CONFIDENTIAL_TEXT_PROJECT_B1",
        )
        self.session_b = ResearchSession.objects.create(
            project=self.project_b,
            title="Session B Foreign",
        )
        self.session_b.papers.add(self.paper_b1)

        # All admin endpoints
        self.admin_endpoints = [
            "/api/admin/dashboard/",
            "/api/admin/users/",
            f"/api/admin/users/{self.normal_user.id}/",
            "/api/admin/projects/",
            f"/api/admin/projects/{self.project_a.id}/",
            "/api/admin/papers/",
            f"/api/admin/papers/{self.paper_a1.id}/",
            "/api/admin/activity/",
            f"/api/admin/activity/{self.msg_a.id}/",
            "/api/admin/ai-usage/",
        ]

    def test_admin_authorization_matrix_all_endpoints(self):
        """
        Verify that all 10 admin endpoints reject unauthenticated users with 401,
        reject non-admin roles (normal user, project owner, editor, viewer) with 403,
        and allow staff and superusers with 200.
        """
        non_admin_users = [
            self.normal_user,
            self.owner_a,
            self.editor_a,
            self.viewer_a,
            self.unrelated_user,
        ]

        for url in self.admin_endpoints:
            # 1. Unauthenticated -> 401
            self.client.force_authenticate(user=None)
            res_anon = self.client.get(url)
            self.assertEqual(
                res_anon.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"URL '{url}' should return 401 for anonymous request",
            )

            # 2. Non-admin users -> 403
            for user in non_admin_users:
                self.client.force_authenticate(user=user)
                res_non_admin = self.client.get(url)
                self.assertEqual(
                    res_non_admin.status_code,
                    status.HTTP_403_FORBIDDEN,
                    f"URL '{url}' should return 403 for user '{user.username}'",
                )

            # 3. Staff -> 200
            self.client.force_authenticate(user=self.staff_admin)
            res_staff = self.client.get(url)
            self.assertEqual(
                res_staff.status_code,
                status.HTTP_200_OK,
                f"URL '{url}' should return 200 for staff admin",
            )

            # 4. Superuser -> 200
            self.client.force_authenticate(user=self.superuser)
            res_super = self.client.get(url)
            self.assertEqual(
                res_super.status_code,
                status.HTTP_200_OK,
                f"URL '{url}' should return 200 for superuser",
            )

    def test_admin_idor_nonexistent_ids_return_404(self):
        """Admin detail endpoints return 404 for nonexistent IDs."""
        self.client.force_authenticate(user=self.staff_admin)
        nonexistent_urls = [
            "/api/admin/users/999999/",
            "/api/admin/projects/999999/",
            "/api/admin/papers/999999/",
            "/api/admin/activity/999999/",
        ]
        for url in nonexistent_urls:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_404_NOT_FOUND,
                f"URL '{url}' should return 404 for nonexistent ID",
            )

    def test_admin_idor_unauthorized_users_receive_403_without_object_leak(self):
        """Non-admin users receive 403 on valid and nonexistent IDs alike without leaking existence."""
        for user in [self.normal_user, self.owner_a, self.editor_a, self.viewer_a]:
            self.client.force_authenticate(user=user)
            # Valid ID
            res_valid = self.client.get(f"/api/admin/projects/{self.project_a.id}/")
            self.assertEqual(res_valid.status_code, status.HTTP_403_FORBIDDEN)
            # Nonexistent ID
            res_invalid = self.client.get("/api/admin/projects/999999/")
            self.assertEqual(res_invalid.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_data_exposure_prevention(self):
        """
        Admin API responses must never leak passwords, tokens, extracted PDF text,
        chunk text, embeddings, or message/evidence bodies.
        """
        self.client.force_authenticate(user=self.staff_admin)

        detail_urls = [
            f"/api/admin/users/{self.owner_a.id}/",
            f"/api/admin/projects/{self.project_a.id}/",
            f"/api/admin/papers/{self.paper_a1.id}/",
            f"/api/admin/activity/{self.msg_a.id}/",
        ]

        for url in detail_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            payload_str = str(res.data)

            # Strict exclusion of sensitive strings
            self.assertNotIn("CONFIDENTIAL_TEXT_PROJECT_A1", payload_str)
            self.assertNotIn("CONFIDENTIAL_CHUNK_TEXT_A1", payload_str)
            self.assertNotIn("CONFIDENTIAL_EVIDENCE_TEXT_A1", payload_str)
            self.assertNotIn("password", payload_str.lower())
            self.assertNotIn("auth_token", payload_str.lower())
            self.assertNotIn("embedding", payload_str.lower())

    def test_collaboration_security_unauthorized_actions(self):
        """
        Verify collaboration permission boundaries:
        - Only project owner can invite (403 for editors, viewers, outsiders)
        - Only project owner can remove members (403 for editors, viewers)
        - Owner cannot remove themselves (400)
        - Owner cannot leave project (400)
        - Non-invited user cannot accept or decline invitations (403)
        - Non-owner cannot cancel invitations (403)
        """
        # 1. Editor cannot invite
        self.client.force_authenticate(user=self.editor_a)
        res_invite_editor = self.client.post(
            f"/api/projects/{self.project_a.id}/members/invite/",
            {"username": self.unrelated_user.username, "role": "EDITOR"},
            format="json",
        )
        self.assertEqual(res_invite_editor.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Viewer cannot invite
        self.client.force_authenticate(user=self.viewer_a)
        res_invite_viewer = self.client.post(
            f"/api/projects/{self.project_a.id}/members/invite/",
            {"username": self.unrelated_user.username, "role": "VIEWER"},
            format="json",
        )
        self.assertEqual(res_invite_viewer.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Owner creates invitation for unrelated_user
        self.client.force_authenticate(user=self.owner_a)
        res_invite = self.client.post(
            f"/api/projects/{self.project_a.id}/members/invite/",
            {"username": self.unrelated_user.username, "role": "EDITOR"},
            format="json",
        )
        self.assertEqual(res_invite.status_code, status.HTTP_201_CREATED)
        invitation_id = res_invite.data["id"]

        # 4. Another user cannot accept the invitation
        self.client.force_authenticate(user=self.editor_a)
        res_bad_accept = self.client.post(f"/api/projects/invitations/{invitation_id}/accept/")
        self.assertEqual(res_bad_accept.status_code, status.HTTP_403_FORBIDDEN)

        # 5. Non-owner cannot cancel the invitation
        self.client.force_authenticate(user=self.editor_a)
        res_bad_cancel = self.client.post(f"/api/projects/invitations/{invitation_id}/cancel/")
        self.assertEqual(res_bad_cancel.status_code, status.HTTP_403_FORBIDDEN)

        # 6. Owner CAN cancel the invitation
        self.client.force_authenticate(user=self.owner_a)
        res_cancel = self.client.post(f"/api/projects/invitations/{invitation_id}/cancel/")
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)

        # 7. Owner cannot leave project
        res_owner_leave = self.client.post(f"/api/projects/{self.project_a.id}/leave/")
        self.assertEqual(res_owner_leave.status_code, status.HTTP_400_BAD_REQUEST)

        # 8. Owner cannot remove themselves as a member
        res_remove_owner = self.client.delete(
            f"/api/projects/{self.project_a.id}/members/{self.owner_a.id}/"
        )
        self.assertEqual(res_remove_owner.status_code, status.HTTP_400_BAD_REQUEST)

        # 9. Editor cannot remove viewer
        self.client.force_authenticate(user=self.editor_a)
        res_editor_remove = self.client.delete(
            f"/api/projects/{self.project_a.id}/members/{self.viewer_a.id}/"
        )
        self.assertEqual(res_editor_remove.status_code, status.HTTP_403_FORBIDDEN)

    def test_research_session_security_and_viewer_boundaries(self):
        """
        Verify research session boundaries:
        - Viewers cannot create, update, or delete sessions (403)
        - Viewers CAN read existing sessions (200)
        - Users cannot access another project's sessions (403)
        - Query project_id mismatch is rejected (400)
        """
        # 1. Viewer cannot create research session
        self.client.force_authenticate(user=self.viewer_a)
        res_create = self.client.post(
            "/api/ai/sessions/",
            {"project_id": self.project_a.id, "title": "Unauthorized Session"},
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Viewer cannot rename research session
        res_rename = self.client.patch(
            f"/api/ai/sessions/{self.session_a.id}/",
            {"title": "Renamed by Viewer"},
            format="json",
        )
        self.assertEqual(res_rename.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Viewer cannot delete research session
        res_delete = self.client.delete(f"/api/ai/sessions/{self.session_a.id}/")
        self.assertEqual(res_delete.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Viewer CAN read research session
        res_get = self.client.get(f"/api/ai/sessions/{self.session_a.id}/")
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)

        # 5. Cross-project session access: Owner A cannot read Session B
        self.client.force_authenticate(user=self.owner_a)
        res_foreign_session = self.client.get(f"/api/ai/sessions/{self.session_b.id}/")
        self.assertEqual(res_foreign_session.status_code, status.HTTP_403_FORBIDDEN)

        # 6. Session/project mismatch query parameter
        res_mismatch = self.client.get(
            f"/api/ai/sessions/{self.session_a.id}/?project_id={self.project_b.id}"
        )
        self.assertEqual(res_mismatch.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ai_endpoint_viewer_rejection_and_mixed_paper_boundaries(self):
        """
        Verify AI endpoint protections:
        - Viewers receive 403 on all generation endpoints
        - Mixed papers across projects are rejected (400 or 403)
        - Session paper from different project is rejected (400)
        """
        self.client.force_authenticate(user=self.viewer_a)

        # 1. Summary rejected for viewer
        res_summary = self.client.post(
            "/api/ai/summary/",
            {"paper_id": self.paper_a1.id},
            format="json",
        )
        self.assertEqual(res_summary.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Ask rejected for viewer
        res_ask = self.client.post(
            "/api/ai/ask/",
            {"paper_id": self.paper_a1.id, "question": "What is tested?"},
            format="json",
        )
        self.assertEqual(res_ask.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Compare rejected for viewer
        res_compare = self.client.post(
            "/api/ai/compare/",
            {"paper_ids": [self.paper_a1.id, self.paper_a2.id], "question": "Compare"},
            format="json",
        )
        self.assertEqual(res_compare.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Gap analysis rejected for viewer
        res_gap = self.client.post(
            "/api/ai/gap-analysis/",
            {"paper_ids": [self.paper_a1.id, self.paper_a2.id]},
            format="json",
        )
        self.assertEqual(res_gap.status_code, status.HTTP_403_FORBIDDEN)

        # 5. Thematic analysis rejected for viewer
        res_thematic = self.client.post(
            "/api/ai/thematic-analysis/",
            {"paper_ids": [self.paper_a1.id, self.paper_a2.id]},
            format="json",
        )
        self.assertEqual(res_thematic.status_code, status.HTTP_403_FORBIDDEN)

        # 6. Trends rejected for viewer
        res_trends = self.client.post(
            "/api/ai/research-trends/",
            {"paper_ids": [self.paper_a1.id, self.paper_a2.id]},
            format="json",
        )
        self.assertEqual(res_trends.status_code, status.HTTP_403_FORBIDDEN)

        # 7. Owner A attempting mixed-project papers (Paper A1 and Paper B1)
        self.client.force_authenticate(user=self.owner_a)
        res_mixed_compare = self.client.post(
            "/api/ai/compare/",
            {"paper_ids": [self.paper_a1.id, self.paper_b1.id], "question": "Compare"},
            format="json",
        )
        # Foreign paper B1 results in 403 or 400
        self.assertIn(res_mixed_compare.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

        # 8. Single paper ask with paper from Project A and session from Project B
        res_mismatched_session = self.client.post(
            "/api/ai/ask/",
            {
                "paper_id": self.paper_a1.id,
                "question": "Question?",
                "session_id": self.session_b.id,
            },
            format="json",
        )
        # User lacks access to session_b, returning 403 or 400
        self.assertIn(
            res_mismatched_session.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN],
        )







