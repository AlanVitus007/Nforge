from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from .models import Project


class ProjectTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='projectuser', password='StrongPass123')

    def test_project_list_requires_login(self):
        response = self.client.get(reverse('project_list'))
        self.assertEqual(response.status_code, 302)

    def test_project_create_and_list(self):
        self.client.login(username='projectuser', password='StrongPass123')
        response = self.client.post(
            reverse('project_create'),
            {'title': 'Sample Project', 'description': 'A test project', 'status': 'ACTIVE'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Project.objects.filter(title='Sample Project').exists())
        self.assertContains(response, 'Sample Project')
