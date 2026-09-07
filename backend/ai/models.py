from django.db import models
from papers.models import Paper


class PaperChunk(models.Model):
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        related_name="chunks",
    )

    chunk_index = models.PositiveIntegerField()
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chunk_index"]
        unique_together = ("paper", "chunk_index")

    def __str__(self):
        return f"{self.paper.title} - Chunk {self.chunk_index}"