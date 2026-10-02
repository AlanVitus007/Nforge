from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from admin_dashboard.permissions import IsNForgeAdmin
from ai.models import ResearchMessage, ResearchSession
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
