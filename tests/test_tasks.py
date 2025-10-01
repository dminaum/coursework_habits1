from django.utils import timezone


from habits.models import Habit


# Тесты патчат эту функцию. Оставляем как простую заглушку.
def _send_tg(chat_id: int | str, text: str) -> None:
    """
    Send a Telegram message to given chat_id.
    In production, implement real sending. In tests, this is monkeypatched.
    """
    # Реальная отправка может быть здесь, например, через requests к Telegram Bot API.
    # В тестах эта функция подменяется.
    pass


def _days_since(last_dt, now_dt) -> int:
    # сравниваем по локальным датам
    return (now_dt.date() - last_dt.date()).days


def send_due_habits() -> None:
    """
    Отправляет напоминание о привычках, которые «на сегодня»
    (время совпадает по минутам) и по периодичности должны выполняться сегодня.
    """
    now = timezone.localtime()  # в тесте monkeypatch подменяет это на фиксированное время
    hh, mm = now.hour, now.minute

    qs = Habit.objects.select_related("user").all()
    for h in qs:
        # время по расписанию совпало?
        if (h.time.hour, h.time.minute) != (hh, mm):
            continue

        # нужно ли выполнять сегодня (>= periodicity_days или ни разу не выполнялась)
        due_today = False
        if h.last_performed_at is None:
            due_today = True
        else:
            last_local = timezone.localtime(h.last_performed_at)
            days = _days_since(last_local, now)
            if days >= h.periodicity_days:
                due_today = True

        if not due_today:
            continue

        chat_id = getattr(h.user, "telegram_chat_id", None)
        if chat_id:
            _send_tg(
                chat_id,
                f"⏰ Habit reminder: {h.action} @ {h.time.strftime('%H:%M')}",
            )


def notify_overdue() -> None:
    """
    Уведомляет о просроченных привычках.
    Просрочено, если:
      - last_performed_at is None
      - или прошло > periodicity_days дней.
    """
    now = timezone.localtime()

    qs = Habit.objects.select_related("user").all()
    for h in qs:
        overdue = False
        if h.last_performed_at is None:
            overdue = True
        else:
            last_local = timezone.localtime(h.last_performed_at)
            days = _days_since(last_local, now)
            # строго больше периодичности — просрочено
            if days > h.periodicity_days:
                overdue = True

        if not overdue:
            continue

        chat_id = getattr(h.user, "telegram_chat_id", None)
        if chat_id:
            _send_tg(
                chat_id,
                f"⚠️ Habit overdue (> {h.periodicity_days} days): {h.action}",
            )
