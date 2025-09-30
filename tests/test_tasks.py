from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from habits.models import Habit


@pytest.mark.django_db
def test_send_due_habits(monkeypatch, user):
    from habits import tasks

    sent = []

    def fake_send_tg(chat_id, text):
        sent.append((chat_id, text))

    fixed_now = timezone.make_aware(
        datetime(2025, 1, 1, 8, 15), timezone=timezone.get_current_timezone()
    )
    monkeypatch.setattr(tasks, "_send_tg", fake_send_tg)
    monkeypatch.setattr(tasks.timezone, "localtime", lambda: fixed_now)

    Habit.objects.create(
        user=user,
        place="p",
        time="08:15",
        action="walk",
        duration_seconds=60,
        periodicity_days=1,
        is_public=False,
        last_performed_at=fixed_now - timedelta(days=1, minutes=5),
    )
    tasks.send_due_habits()
    assert len(sent) == 1
    assert (
        str(user.telegram_chat_id) in str(sent[0][0])
        or sent[0][0] == user.telegram_chat_id
    )


@pytest.mark.django_db
def test_notify_overdue(monkeypatch, user):
    from habits import tasks

    sent = []
    monkeypatch.setattr(
        tasks, "_send_tg", lambda chat_id, text: sent.append((chat_id, text))
    )

    now = timezone.now()
    Habit.objects.create(
        user=user,
        place="p",
        time="08:00",
        action="read",
        duration_seconds=60,
        periodicity_days=7,
        last_performed_at=now - timedelta(days=8),
    )
    Habit.objects.create(
        user=user,
        place="p",
        time="08:00",
        action="code",
        duration_seconds=60,
        periodicity_days=7,
        last_performed_at=now - timedelta(days=2),
    )
    Habit.objects.create(
        user=user,
        place="p",
        time="08:00",
        action="water",
        duration_seconds=60,
        periodicity_days=7,
        last_performed_at=None,
    )

    tasks.notify_overdue()
    assert len(sent) == 2
