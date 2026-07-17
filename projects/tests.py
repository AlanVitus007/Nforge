from datetime import date

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

    def test_project_detail_edit_and_delete(self):
        self.client.login(username='projectuser', password='StrongPass123')
        project = Project.objects.create(title='Phase One', description='Details', status='ACTIVE', owner=self.user)

        detail_response = self.client.get(reverse('project_detail', args=[project.pk]))
        self.assertEqual(detail_response.status_code, 200)

        edit_response = self.client.post(
            reverse('project_edit', args=[project.pk]),
            {'title': 'Phase One Updated', 'description': 'Updated', 'status': 'COMPLETED'},
            follow=True,
        )
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, 'Phase One Updated')

        delete_response = self.client.post(reverse('project_delete', args=[project.pk]), follow=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())

    def test_project_can_store_dates_and_owner(self):
        self.client.login(username='projectuser', password='StrongPass123')
        response = self.client.post(
            reverse('project_create'),
            {
                'title': 'Research Sprint',
                'description': 'Planning phase',
                'status': 'ACTIVE',
                'start_date': '2026-07-01',
                'end_date': '2026-07-31',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(title='Research Sprint')
        self.assertEqual(project.owner, self.user)
        self.assertEqual(project.start_date, date(2026, 7, 1))
        self.assertEqual(project.end_date, date(2026, 7, 31))
