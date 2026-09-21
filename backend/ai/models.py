from django.db import models
from projects.models import Project
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


class ResearchSession(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="research_sessions",
    )
    papers = models.ManyToManyField(
        Paper,
        related_name="research_sessions",
        blank=True,
    )
    title = models.CharField(max_length=255, default="Research Session")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} (Project: {self.project.title})"


class ResearchMessage(models.Model):
    ROLE_USER = "USER"
    ROLE_ASSISTANT = "ASSISTANT"
    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    ]

    session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} message in Session #{self.session.id}"


class ResearchEvidence(models.Model):
    message = models.ForeignKey(
        ResearchMessage,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        related_name="research_evidence",
    )
    chunk = models.ForeignKey(
        PaperChunk,
        on_delete=models.SET_NULL,
        related_name="research_evidence",
        null=True,
        blank=True,
    )
    page_number = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Evidence for Message #{self.message.id} ({self.paper.title})"