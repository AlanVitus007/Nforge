from django.contrib.auth.models import User
from django.db import models
from projects.models import Project

class Paper(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='papers')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='papers/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True, default="")

    def __str__(self):
        return self.title


class PaperNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paper_notes')
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200, default="Untitled note")
    content = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'paper', '-updated_at']),
            models.Index(fields=['paper', 'user']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.username} ({self.paper.title})"

