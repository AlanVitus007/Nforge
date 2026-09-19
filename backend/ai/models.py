from django.db import models
from papers.models import Paper


class PaperChunk(models.Model):
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    embedding = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chunk_index"]
        unique_together = ("paper", "chunk_index")

    def __str__(self):
        return f"{self.paper.title} - Chunk {self.chunk_index}"