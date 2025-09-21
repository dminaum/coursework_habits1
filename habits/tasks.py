import os
from datetime import timedelta

import requests
from celery import shared_task
from django.utils import timezone

from .models import Habit

BOT_TOKEN = os.getenv("BOT_TOKEN")


def _send_tg(chat_id, text):
    if not BOT_TOKEN or not chat_id:
        return
    try:
        requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={"chat_id": chat_id, "text": text},
            timeout=5,
        )
    except requests.RequestException:
        pass


def _is_due_today(habit, now):
    # если давно не выполняли — напоминаем согласно periodicity_days
    base_date = (
        habit.last_performed_at or (now - timedelta(days=habit.periodicity_days))
    ).date()
    return (now.date() - base_date).days >= habit.periodicity_days


@shared_task
def send_due_habits():
    now = timezone.localtime()
    qs = Habit.objects.filter(time__hour=now.hour, time__minute=now.minute)
    for h in qs:
        if _is_due_today(h, now):
            chat_id = getattr(h.user, "telegram_chat_id", None)
            _send_tg(
                chat_id,
                f"Напоминание: {h.action} в {h.place} (≈{h.duration_seconds}s). "
                f"Отметить: /done_{h.id}",
            )


@shared_task
def notify_overdue():
    now = timezone.localtime()
    limit = now - timedelta(days=7)
    overdue = Habit.objects.filter(last_performed_at__lt=limit) | Habit.objects.filter(
        last_performed_at__isnull=True
    )
    for h in overdue.distinct():
        chat_id = getattr(h.user, "telegram_chat_id", None)
        _send_tg(
            chat_id, f"Привычка просрочена (>7 дней): {h.action}. Выполни её сегодня."
        )
