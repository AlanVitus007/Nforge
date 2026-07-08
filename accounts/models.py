from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('SUPERVISOR', 'Supervisor'),
        ('RESEARCHER', 'Researcher'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='RESEARCHER'
    )

    institution = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username