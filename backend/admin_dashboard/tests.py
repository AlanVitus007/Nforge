from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from admin_dashboard.permissions import IsNForgeAdmin
from ai.models import PaperChunk, ResearchEvidence, ResearchMessage, ResearchSession
from papers.models import Paper
from projects.models import Project, ProjectMember



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



