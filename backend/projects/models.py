from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ProjectMember(models.Model):
    ROLE_OWNER = "OWNER"
    ROLE_EDITOR = "EDITOR"
    ROLE_VIEWER = "VIEWER"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_VIEWER, "Viewer"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_VIEWER,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="unique_project_membership",
            ),
        ]
        indexes = [
            models.Index(fields=["project"], name="proj_member_project_idx"),
            models.Index(fields=["user"], name="proj_member_user_idx"),
            models.Index(fields=["project", "user"], name="proj_member_proj_user_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.project.title} ({self.role})"


class ProjectInvitation(models.Model):
    ROLE_EDITOR = "EDITOR"
    ROLE_VIEWER = "VIEWER"

    ROLE_CHOICES = [
        (ROLE_EDITOR, "Editor"),
        (ROLE_VIEWER, "Viewer"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_DECLINED = "DECLINED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_invitations",
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_project_invitations",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_VIEWER,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "invited_user"],
                condition=models.Q(status="PENDING"),
                name="uniq_pending_proj_invitation",
            ),
        ]
        indexes = [
            models.Index(fields=["project"], name="proj_inv_project_idx"),
            models.Index(fields=["invited_user"], name="proj_inv_invited_user_idx"),
            models.Index(fields=["invited_by"], name="proj_inv_invited_by_idx"),
            models.Index(fields=["status"], name="proj_inv_status_idx"),
            models.Index(fields=["project", "invited_user"], name="proj_inv_proj_user_idx"),
            models.Index(fields=["invited_user", "status"], name="proj_inv_user_status_idx"),
        ]

    def __str__(self):
        return f"Invitation for {self.invited_user.username} to {self.project.title} ({self.role} - {self.status})"
