from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from projects.models import Project
from .models import Paper


class PaperTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='paperuser', password='StrongPass123')
        self.project = Project.objects.create(title='AI Study', description='Research project', owner=self.user)

    def test_paper_can_be_uploaded_and_linked_to_project(self):
        self.client.login(username='paperuser', password='StrongPass123')
        pdf_file = SimpleUploadedFile('paper.pdf', b'%PDF-1.4\n', content_type='application/pdf')

        response = self.client.post(
            reverse('paper_create'),
            {
                'title': 'Neural Networks Overview',
                'authors': 'Ada Lovelace',
                'journal': 'Research Journal',
                'publication_year': 2024,
                'keywords': 'ai, neural networks',
                'abstract': 'A short abstract about the paper.',
                'project': self.project.pk,
                'pdf_file': pdf_file,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Paper.objects.filter(title='Neural Networks Overview').exists())
        paper = Paper.objects.get(title='Neural Networks Overview')
        self.assertEqual(paper.owner, self.user)
        self.assertEqual(paper.project, self.project)
        self.assertTrue(paper.pdf_file.name.startswith('papers/'))
        self.assertTrue(paper.pdf_file.name.endswith('.pdf'))
