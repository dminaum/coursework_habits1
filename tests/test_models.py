import pytest
from django.core.exceptions import ValidationError

from habits.models import Habit


@pytest.mark.django_db
def test_duration_cannot_exceed_120(user):
    h = Habit(
        user=user,
        place="home",
        time="08:00",
        action="run",
        duration_seconds=121,
        periodicity_days=1,
    )
    with pytest.raises(ValidationError):
        h.full_clean()


@pytest.mark.django_db
def test_related_must_be_pleasant(user):
    base = Habit.objects.create(
        user=user,
        place="home",
        time="08:00",
        action="walk",
        duration_seconds=60,
        periodicity_days=1,
        is_pleasant=False,
    )
    target = Habit(
        user=user,
        place="home",
        time="09:00",
        action="work",
        duration_seconds=60,
        periodicity_days=1,
        related_habit=base,
    )
    with pytest.raises(ValidationError):
        target.full_clean()


@pytest.mark.django_db
def test_pleasant_cannot_have_reward_or_related(user):
    pleasant = Habit(
        user=user,
        place="home",
        time="08:00",
        action="tea",
        duration_seconds=60,
        periodicity_days=1,
        is_pleasant=True,
        reward="cake",
    )
    with pytest.raises(ValidationError):
        pleasant.full_clean()


@pytest.mark.django_db
def test_reward_and_related_mutually_exclusive(user):
    pleasant = Habit.objects.create(
        user=user,
        place="home",
        time="07:00",
        action="bath",
        duration_seconds=60,
        periodicity_days=1,
        is_pleasant=True,
    )
    h = Habit(
        user=user,
        place="home",
        time="08:00",
        action="run",
        duration_seconds=60,
        periodicity_days=1,
        reward="dessert",
        related_habit=pleasant,
    )
    with pytest.raises(ValidationError):
        h.full_clean()


@pytest.mark.django_db
def test_periodicity_bounds(user):
    low = Habit(
        user=user,
        place="home",
        time="08:00",
        action="read",
        duration_seconds=60,
        periodicity_days=0,
    )
    with pytest.raises(ValidationError):
        low.full_clean()
    high = Habit(
        user=user,
        place="home",
        time="08:00",
        action="read",
        duration_seconds=60,
        periodicity_days=8,
    )
    with pytest.raises(ValidationError):
        high.full_clean()
