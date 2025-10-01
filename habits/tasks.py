import os
import requests

from celery import shared_task
from django.utils import timezone
from zoneinfo import ZoneInfo

from .models import Habit

BOT_TOKEN = os.getenv("BOT_TOKEN")


def _lang(user) -> str:
    code = (getattr(user, "language", None) or "en").lower()
    return code if code in {"ru", "es", "en"} else "en"


def _tr(user, ru: str, es: str, en: str) -> str:
    lang = _lang(user)
    return {"ru": ru, "es": es}.get(lang, en)


def _user_tz(user):
    tzname = getattr(user, "timezone", None) or "UTC"
    try:
        return ZoneInfo(tzname)
    except Exception:
        return ZoneInfo("UTC")


def _days_between_local(a, b):
    return (b.date() - a.date()).days


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


def _is_due_today(habit, now_local):
    """
    Напоминать сегодня, если:
      - ни разу не выполнялась; или
      - прошло >= periodicity_days дней с последнего выполнения.
    """
    if habit.last_performed_at is None:
        return True
    last_local = timezone.localtime(habit.last_performed_at)
    return _days_between_local(last_local, now_local) >= habit.periodicity_days


@shared_task
def send_due_habits():
    """
    В минуту X:Y напоминаем о привычках, которые должны выполняться сегодня.
    Тексты — через наш ручной перевод (как в боте).
    """
    now = timezone.localtime()
    qs = Habit.objects.select_related("user").filter(
        time__hour=now.hour, time__minute=now.minute
    )

    for h in qs:
        user = h.user
        now_local = timezone.now().astimezone(_user_tz(user))
        if not _is_due_today(h, now_local):
            continue

        chat_id = getattr(user, "telegram_chat_id", None)
        if not chat_id:
            continue

        msg = _tr(
            user,
            ru="⏰ Напоминание: {action} @ {time} — /done_{id}",
            es="⏰ Recordatorio: {action} @ {time} — /done_{id}",
            en="⏰ Habit reminder: {action} @ {time} — /done_{id}",
        ).format(action=h.action, time=h.time.strftime("%H:%M"), id=h.id)

        _send_tg(chat_id, msg)


@shared_task
def notify_overdue():
    """
    Просрочено, если:
      - last_performed_at is None; ИЛИ
      - прошло > periodicity_days дней.
    """
    timezone.localtime()
    qs = Habit.objects.select_related("user").all()

    for h in qs:
        user = h.user
        now_local = timezone.now().astimezone(_user_tz(user))

        if h.last_performed_at is None:
            overdue = True
        else:
            last_local = timezone.localtime(h.last_performed_at)
            overdue = _days_between_local(last_local, now_local) > h.periodicity_days

        if not overdue:
            continue

        chat_id = getattr(user, "telegram_chat_id", None)
        if not chat_id:
            continue

        msg = _tr(
            user,
            ru="⚠️ Привычка просрочена (> {days} дней): {action}",
            es="⚠️ Hábito atrasado (> {days} días): {action}",
            en="⚠️ Habit overdue (> {days} days): {action}",
        ).format(days=h.periodicity_days, action=h.action)

        _send_tg(chat_id, msg)
