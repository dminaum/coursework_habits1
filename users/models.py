from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    timezone = models.CharField(max_length=64, default="Europe/Madrid")
    language = models.CharField(max_length=8, default="en")
    notifications_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.username
