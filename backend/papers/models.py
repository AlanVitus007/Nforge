from django.db import models
from projects.models import Project

class Paper(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='papers')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='papers/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
