from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from projects.models import Project, ProjectMember
from papers.models import Paper, PaperNote


class PaperNoteBackendTests(TestCase):
    """
    Test suite for NForge Paper-Specific Private Notebook feature.
    Verifies creation, listing, updating, deletion, authorization isolation,
    viewer permissions, cascade behavior, and validation.
    """

    def setUp(self):
        self.client = APIClient()

        # Project owner / author
        self.owner = User.objects.create_user(
            username="alice_owner",
            email="alice@example.com",
            password="Password123!",
        )
        self.owner_token = Token.objects.create(user=self.owner)

        # Project collaborator (VIEWER)
        self.viewer = User.objects.create_user(
            username="bob_viewer",
            email="bob@example.com",
            password="Password123!",
        )
        self.viewer_token = Token.objects.create(user=self.viewer)

        # Unrelated outsider user
        self.outsider = User.objects.create_user(
            username="charlie_outsider",
            email="charlie@example.com",
            password="Password123!",
        )
        self.outsider_token = Token.objects.create(user=self.outsider)

        # Create Project
        self.project = Project.objects.create(
            title="Quantum Research",
            description="Quantum computing project",
            owner=self.owner,
        )

        # Add viewer to project
        ProjectMember.objects.create(
            project=self.project,
            user=self.viewer,
            role=ProjectMember.ROLE_VIEWER,
        )

        # Create Paper
        fake_pdf = SimpleUploadedFile("quantum_paper.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.paper = Paper.objects.create(
            project=self.project,
            title="Quantum Decoherence and Error Correction",
            file=fake_pdf,
        )

    # 1. Authenticated users can list and create their own notes
    def test_authenticated_users_can_list_and_create_notes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token.key}")

        # Initially empty
        res_list_empty = self.client.get(f"/api/papers/{self.paper.id}/notes/")
        self.assertEqual(res_list_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list_empty.data), 0)

        # Create note
        res_create = self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "Initial Observation", "content": "Key theorem on page 3."},
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", res_create.data)
        self.assertEqual(res_create.data["title"], "Initial Observation")
        self.assertEqual(res_create.data["content"], "Key theorem on page 3.")
        self.assertEqual(res_create.data["paper_id"], self.paper.id)

        # List now has 1 note
        res_list = self.client.get(f"/api/papers/{self.paper.id}/notes/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.data), 1)
        self.assertEqual(res_list.data[0]["title"], "Initial Observation")

    # 2. Users can create multiple notes for the same paper
    def test_users_can_create_multiple_notes_for_same_paper(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token.key}")

        for i in range(3):
            res = self.client.post(
                f"/api/papers/{self.paper.id}/notes/",
                {"title": f"Note #{i+1}", "content": f"Content for note #{i+1}"},
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res_list = self.client.get(f"/api/papers/{self.paper.id}/notes/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.data), 3)

    # 3. Note title and content persist after updates
    def test_note_title_and_content_persist_after_updates(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token.key}")

        res_create = self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "Original Title", "content": "Original content"},
            format="json",
        )
        note_id = res_create.data["id"]

        # Update via PATCH
        res_patch = self.client.patch(
            f"/api/paper-notes/{note_id}/",
            {"title": "Revised Title", "content": "Revised content with extra derivations."},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["title"], "Revised Title")
        self.assertEqual(res_patch.data["content"], "Revised content with extra derivations.")

        # Retrieve single note
        res_get = self.client.get(f"/api/paper-notes/{note_id}/")
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data["title"], "Revised Title")
        self.assertEqual(res_get.data["content"], "Revised content with extra derivations.")

        # Verify DB directly
        note = PaperNote.objects.get(pk=note_id)
        self.assertEqual(note.title, "Revised Title")
        self.assertEqual(note.content, "Revised content with extra derivations.")

    # 4. Users cannot list another user's notes
    def test_users_cannot_list_another_users_notes(self):
        # Alice creates a private note
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token.key}")
        self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "Alice's Secret Finding", "content": "Proprietary discovery."},
            format="json",
        )

        # Bob (collaborator viewer on the same project/paper) lists notes
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.viewer_token.key}")
        res_bob = self.client.get(f"/api/papers/{self.paper.id}/notes/")
        self.assertEqual(res_bob.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_bob.data), 0)

        # Bob creates his own note
        self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "Bob's Review", "content": "Bob's private thoughts."},
            format="json",
        )

        # Bob sees only his 1 note
        res_bob_after = self.client.get(f"/api/papers/{self.paper.id}/notes/")
        self.assertEqual(len(res_bob_after.data), 1)
        self.assertEqual(res_bob_after.data[0]["title"], "Bob's Review")

        # Alice still sees only her 1 note
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token.key}")
        res_alice = self.client.get(f"/api/papers/{self.paper.id}/notes/")
        self.assertEqual(len(res_alice.data), 1)
        self.assertEqual(res_alice.data[0]["title"], "Alice's Secret Finding")

    # 5. Users cannot retrieve, modify, or delete another user's notes by ID (returns 404)
    def test_users_cannot_retrieve_modify_or_delete_another_users_notes_by_id(self):
        # Alice creates a note
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token.key}")
        res_create = self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "Alice Note", "content": "Confidential content"},
            format="json",
        )
        note_id = res_create.data["id"]

        # Bob attempts to access Alice's note by ID
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.viewer_token.key}")

        res_get = self.client.get(f"/api/paper-notes/{note_id}/")
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        res_patch = self.client.patch(
            f"/api/paper-notes/{note_id}/",
            {"title": "Tampered Title"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_404_NOT_FOUND)

        res_delete = self.client.delete(f"/api/paper-notes/{note_id}/")
        self.assertEqual(res_delete.status_code, status.HTTP_404_NOT_FOUND)

        # Verify note still belongs to Alice and is untouched in DB
        note = PaperNote.objects.get(pk=note_id)
        self.assertEqual(note.title, "Alice Note")
        self.assertEqual(note.user, self.owner)

    # 6. Anonymous users cannot access note endpoints (returns 401)
    def test_anonymous_users_cannot_access_note_endpoints(self):
        note = PaperNote.objects.create(
            paper=self.paper,
            user=self.owner,
            title="Anon Test Note",
            content="Content",
        )
        self.client.credentials()  # Clear auth token

        self.assertEqual(self.client.get(f"/api/papers/{self.paper.id}/notes/").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(f"/api/papers/{self.paper.id}/notes/", {"title": "X"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(f"/api/paper-notes/{note.id}/").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(f"/api/paper-notes/{note.id}/", {"title": "X"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(f"/api/paper-notes/{note.id}/").status_code, status.HTTP_401_UNAUTHORIZED)

    # 7. Cross-project or inaccessible-paper operations are rejected (returns 404)
    def test_cross_project_or_inaccessible_paper_operations_are_rejected(self):
        # Charlie is not a member of Quantum Research project
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.outsider_token.key}")

        res_list = self.client.get(f"/api/papers/{self.paper.id}/notes/")
        self.assertEqual(res_list.status_code, status.HTTP_404_NOT_FOUND)

        res_create = self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "Intruder Note", "content": "Should fail"},
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_404_NOT_FOUND)

    # 8. Project viewer can manage their own notes for a readable paper without gaining permission to modify the paper
    def test_project_viewer_can_manage_own_notes_without_edit_permission_on_paper(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.viewer_token.key}")

        # Bob creates note
        res_create = self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "Viewer Reading Notes", "content": "Notes from a viewer"},
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        note_id = res_create.data["id"]

        # Bob updates note
        res_patch = self.client.patch(
            f"/api/paper-notes/{note_id}/",
            {"content": "Updated reader comments"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)

        # Bob deletes his note
        res_delete = self.client.delete(f"/api/paper-notes/{note_id}/")
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PaperNote.objects.filter(pk=note_id).exists())

        # Bob CANNOT modify the paper itself
        res_paper_patch = self.client.patch(
            f"/api/projects/{self.project.id}/papers/{self.paper.id}/",
            {"title": "Hacked Paper Title"},
            format="json",
        )
        self.assertEqual(res_paper_patch.status_code, status.HTTP_403_FORBIDDEN)

        # Bob CANNOT delete the paper
        res_paper_delete = self.client.delete(
            f"/api/projects/{self.project.id}/papers/{self.paper.id}/"
        )
        self.assertEqual(res_paper_delete.status_code, status.HTTP_403_FORBIDDEN)

    # 9. Deleting a paper cascades appropriately to its notes
    def test_deleting_paper_cascades_appropriately_to_its_notes(self):
        PaperNote.objects.create(paper=self.paper, user=self.owner, title="Note 1")
        PaperNote.objects.create(paper=self.paper, user=self.viewer, title="Note 2")

        self.assertEqual(PaperNote.objects.filter(paper=self.paper).count(), 2)

        # Delete paper
        self.paper.delete()

        # Both notes should be cascade deleted
        self.assertEqual(PaperNote.objects.filter(paper_id=self.paper.id).count(), 0)

    # 10. Invalid or oversized titles are rejected
    def test_invalid_or_oversized_titles_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.owner_token.key}")

        oversized_title = "A" * 201
        res = self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": oversized_title, "content": "Content"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)

        # Blank title defaults to "Untitled note"
        res_blank = self.client.post(
            f"/api/papers/{self.paper.id}/notes/",
            {"title": "   ", "content": "Content with blank title"},
            format="json",
        )
        self.assertEqual(res_blank.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_blank.data["title"], "Untitled note")
