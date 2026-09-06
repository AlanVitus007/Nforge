from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from .models import Project


class ProjectAPITests(APITestCase):
    """Tests for GET/POST /api/projects/ and GET/PUT/PATCH/DELETE /api/projects/<id>/"""

    def setUp(self):
        # Two independent users
        self.user_a = User.objects.create_user(username='alice', password='pass1234')
        self.user_b = User.objects.create_user(username='bob',   password='pass1234')

        self.token_a = Token.objects.create(user=self.user_a)
        self.token_b = Token.objects.create(user=self.user_b)

        # One project owned by alice
        self.project = Project.objects.create(
            owner=self.user_a,
            title='Alice Project',
            description='Owned by Alice',
        )

        self.list_url   = reverse('project-list-create')
        self.detail_url = lambda pk: reverse('project-detail', kwargs={'pk': pk})

    # ------------------------------------------------------------------ helpers
    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def deauth(self):
        self.client.credentials()

    # ------------------------------------------------------------------ list
    def test_list_requires_auth(self):
        self.deauth()
        r = self.client.get(self.list_url)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_projects(self):
        self.auth(self.token_a)
        r = self.client.get(self.list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]['title'], 'Alice Project')

    def test_list_empty_for_user_with_no_projects(self):
        self.auth(self.token_b)
        r = self.client.get(self.list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 0)

    # ------------------------------------------------------------------ create
    def test_create_requires_auth(self):
        self.deauth()
        r = self.client.post(self.list_url, {'title': 'X'})
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_assigns_owner_from_request_user(self):
        self.auth(self.token_b)
        r = self.client.post(self.list_url, {'title': 'Bob Project', 'description': 'desc'})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['owner'], 'bob')
        self.assertTrue(Project.objects.filter(owner=self.user_b, title='Bob Project').exists())

    def test_create_missing_title_returns_400(self):
        self.auth(self.token_a)
        r = self.client.post(self.list_url, {'description': 'no title'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ retrieve
    def test_retrieve_own_project(self):
        self.auth(self.token_a)
        r = self.client.get(self.detail_url(self.project.pk))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['title'], 'Alice Project')

    def test_retrieve_other_users_project_returns_404(self):
        self.auth(self.token_b)
        r = self.client.get(self.detail_url(self.project.pk))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_requires_auth(self):
        self.deauth()
        r = self.client.get(self.detail_url(self.project.pk))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------ update (PUT)
    def test_put_own_project(self):
        self.auth(self.token_a)
        r = self.client.put(
            self.detail_url(self.project.pk),
            {'title': 'Updated', 'description': 'new desc'},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['title'], 'Updated')

    def test_put_other_users_project_returns_404(self):
        self.auth(self.token_b)
        r = self.client.put(
            self.detail_url(self.project.pk),
            {'title': 'Hijack', 'description': ''},
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------ partial update (PATCH)
    def test_patch_own_project(self):
        self.auth(self.token_a)
        r = self.client.patch(self.detail_url(self.project.pk), {'title': 'Patched'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['title'], 'Patched')

    def test_patch_other_users_project_returns_404(self):
        self.auth(self.token_b)
        r = self.client.patch(self.detail_url(self.project.pk), {'title': 'Hijack'})
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------ delete
    def test_delete_own_project(self):
        self.auth(self.token_a)
        r = self.client.delete(self.detail_url(self.project.pk))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_delete_other_users_project_returns_404(self):
        self.auth(self.token_b)
        r = self.client.delete(self.detail_url(self.project.pk))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_delete_requires_auth(self):
        self.deauth()
        r = self.client.delete(self.detail_url(self.project.pk))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
