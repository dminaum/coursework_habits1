from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from .validators import (validate_pleasant_no_reward_related,
                         validate_related_is_pleasant,
                         validate_reward_xor_related)


class Habit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="habits"
    )
    place = models.CharField(max_length=255)
    time = models.TimeField()
    action = models.CharField(max_length=255)
    is_pleasant = models.BooleanField(default=False)
    related_habit = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )
    periodicity_days = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    reward = models.CharField(max_length=255, null=True, blank=True)
    duration_seconds = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
    )
    is_public = models.BooleanField(default=False)
    last_performed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(duration_seconds__gte=1) & Q(duration_seconds__lte=120),
                name="habit_duration_1_120",
            ),
            models.CheckConstraint(
                check=Q(periodicity_days__gte=1) & Q(periodicity_days__lte=7),
                name="habit_periodicity_1_7",
            ),
            models.CheckConstraint(
                check=~(
                    (Q(reward__isnull=False) & ~Q(reward=""))
                    & Q(related_habit__isnull=False)
                ),
                name="habit_no_reward_and_related",
            ),
            models.CheckConstraint(
                check=Q(is_pleasant=False)
                | (
                    (Q(reward__isnull=True) | Q(reward=""))
                    & Q(related_habit__isnull=True)
                ),
                name="habit_pleasant_has_no_reward_or_related",
            ),
        ]

    def clean(self):
        validate_reward_xor_related(self.reward, self.related_habit)
        validate_pleasant_no_reward_related(
            self.is_pleasant, self.reward, self.related_habit
        )
        validate_related_is_pleasant(self.related_habit)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="logs")
    performed_at = models.DateTimeField(auto_now_add=True)
