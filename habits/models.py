from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Habit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="habits"
    )
    time = models.TimeField()
    action = models.CharField(max_length=255)
    periodicity_days = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    last_performed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} @ {self.time}"
