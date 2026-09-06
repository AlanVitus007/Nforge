import io
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from projects.models import Project
from .models import Paper


def make_pdf(name='test.pdf'):
    """Minimal valid-looking PDF bytes wrapped as an upload."""
    content = b'%PDF-1.4 fake pdf content'
    return SimpleUploadedFile(name, content, content_type='application/pdf')


def make_txt(name='bad.txt'):
    return SimpleUploadedFile(name, b'not a pdf', content_type='text/plain')


class PaperAPITests(APITestCase):

    def setUp(self):
        self.user_a = User.objects.create_user(username='alice', password='pass1234')
        self.user_b = User.objects.create_user(username='bob',   password='pass1234')

        self.token_a = Token.objects.create(user=self.user_a)
        self.token_b = Token.objects.create(user=self.user_b)

        self.project_a = Project.objects.create(owner=self.user_a, title='Alice Project')
        self.project_b = Project.objects.create(owner=self.user_b, title='Bob Project')

        self.paper = Paper.objects.create(
            project=self.project_a,
            title='Existing Paper',
            file=make_pdf('existing.pdf'),
        )

    def _list_url(self, project_id):
        return reverse('paper-list-create', kwargs={'project_id': project_id})

    def _detail_url(self, project_id, paper_id):
        return reverse('paper-detail', kwargs={'project_id': project_id, 'paper_id': paper_id})

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def deauth(self):
        self.client.credentials()

    # ── unauthenticated ───────────────────────────────────────────────────────

    def test_list_requires_auth(self):
        self.deauth()
        r = self.client.get(self._list_url(self.project_a.pk))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        self.deauth()
        r = self.client.post(self._list_url(self.project_a.pk), {'title': 'X', 'file': make_pdf()})
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_auth(self):
        self.deauth()
        r = self.client.get(self._detail_url(self.project_a.pk, self.paper.pk))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_auth(self):
        self.deauth()
        r = self.client.delete(self._detail_url(self.project_a.pk, self.paper.pk))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── authenticated listing ─────────────────────────────────────────────────

    def test_list_own_papers(self):
        self.auth(self.token_a)
        r = self.client.get(self._list_url(self.project_a.pk))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]['title'], 'Existing Paper')

    def test_list_empty_project(self):
        self.auth(self.token_b)
        r = self.client.get(self._list_url(self.project_b.pk))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 0)

    # ── paper creation ────────────────────────────────────────────────────────

    def test_create_paper_success(self):
        self.auth(self.token_a)
        data = {'title': 'New Paper', 'file': make_pdf()}
        r = self.client.post(self._list_url(self.project_a.pk), data, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['title'], 'New Paper')
        self.assertEqual(r.data['project'], self.project_a.pk)

    def test_create_paper_project_from_url_not_client(self):
        """Client must not be able to assign paper to a different project."""
        self.auth(self.token_a)
        data = {'title': 'Sneaky', 'file': make_pdf(), 'project': self.project_b.pk}
        r = self.client.post(self._list_url(self.project_a.pk), data, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        # project must still be project_a despite the posted value
        self.assertEqual(r.data['project'], self.project_a.pk)

    def test_create_missing_title_returns_400(self):
        self.auth(self.token_a)
        r = self.client.post(self._list_url(self.project_a.pk), {'file': make_pdf()}, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_file_returns_400(self):
        self.auth(self.token_a)
        r = self.client.post(self._list_url(self.project_a.pk), {'title': 'No file'}, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── non-PDF rejection ─────────────────────────────────────────────────────

    def test_non_pdf_rejected(self):
        self.auth(self.token_a)
        data = {'title': 'Bad File', 'file': make_txt()}
        r = self.client.post(self._list_url(self.project_a.pk), data, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('PDF', str(r.data))

    def test_pdf_with_wrong_extension_rejected(self):
        self.auth(self.token_a)
        bad = SimpleUploadedFile('paper.docx', b'%PDF-1.4 sneaky', content_type='application/pdf')
        data = {'title': 'Sneaky ext', 'file': bad}
        r = self.client.post(self._list_url(self.project_a.pk), data, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── paper retrieval ───────────────────────────────────────────────────────

    def test_retrieve_own_paper(self):
        self.auth(self.token_a)
        r = self.client.get(self._detail_url(self.project_a.pk, self.paper.pk))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['title'], 'Existing Paper')

    # ── paper deletion ────────────────────────────────────────────────────────

    def test_delete_own_paper(self):
        self.auth(self.token_a)
        r = self.client.delete(self._detail_url(self.project_a.pk, self.paper.pk))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Paper.objects.filter(pk=self.paper.pk).exists())

    # ── cross-user isolation ──────────────────────────────────────────────────

    def test_list_other_users_project_returns_404(self):
        self.auth(self.token_b)
        r = self.client.get(self._list_url(self.project_a.pk))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_in_other_users_project_returns_404(self):
        self.auth(self.token_b)
        data = {'title': 'Hijack', 'file': make_pdf()}
        r = self.client.post(self._list_url(self.project_a.pk), data, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_other_users_paper_returns_404(self):
        self.auth(self.token_b)
        r = self.client.get(self._detail_url(self.project_a.pk, self.paper.pk))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_other_users_paper_returns_404(self):
        self.auth(self.token_b)
        r = self.client.delete(self._detail_url(self.project_a.pk, self.paper.pk))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Paper.objects.filter(pk=self.paper.pk).exists())
