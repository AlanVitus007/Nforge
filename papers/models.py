from django.conf import settings
from django.db import models

from projects.models import Project


class Paper(models.Model):
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=500)
    journal = models.CharField(max_length=255, blank=True)
    publication_year = models.PositiveIntegerField(blank=True, null=True)
    keywords = models.CharField(max_length=500, blank=True)
    abstract = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='papers/', blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='papers')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='papers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
