from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q


class Friendship(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_DECLINED = "DECLINED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friendships_sent",
    )
    friend = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friendships_received",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "friend"],
                name="unique_user_friend_pair",
            ),
            models.CheckConstraint(
                check=~Q(user=models.F("friend")),
                name="prevent_self_friendship",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="friendship_user_status_idx"),
            models.Index(fields=["friend", "status"], name="friendship_friend_status_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.friend.username} ({self.status})"
