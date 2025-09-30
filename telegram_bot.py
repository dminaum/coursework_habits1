from dotenv import load_dotenv
import os
import django

import re
from datetime import time as dt_time

import telebot
from django.contrib.auth import get_user_model
from django.utils import timezone
from telebot import types

from habits.models import Habit
from habits.serializers import HabitSerializer

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


User = get_user_model()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

STATE: dict[int, dict] = {}


def get_or_create_user_by_chat(chat_id: int) -> User:
    user, created = User.objects.get_or_create(
        username=str(chat_id), defaults={"telegram_chat_id": chat_id}
    )
    if not created and getattr(user, "telegram_chat_id", None) != chat_id:
        user.telegram_chat_id = chat_id
        user.save(update_fields=["telegram_chat_id"])
    return user


def parse_hhmm(value: str) -> dt_time | None:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", value)
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if 0 <= hh <= 23 and 0 <= mm <= 59:
        return dt_time(hour=hh, minute=mm)
    return None


def validate_periodicity(s: str) -> int | None:
    try:
        v = int(s)
    except ValueError:
        return None
    if 1 <= v <= 7:
        return v
    return None


def validate_duration(s: str) -> int | None:
    try:
        v = int(s)
    except ValueError:
        return None
    if 1 <= v <= 120:
        return v
    return None


def main_menu_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("Информация о привычках"),
        types.KeyboardButton("Добавить привычку"),
        types.KeyboardButton("Удалить все привычки"),
    )
    return kb


def list_habits_text(user: User) -> tuple[str, list[Habit]]:
    habits = list(Habit.objects.filter(user=user).order_by("time", "id"))
    if not habits:
        return "🤷‍♀️ Нет привычек к выполнению", []
    lines = [f"📃 ПРОВЕРКА Информация о привычках пользователя {user.email or user.username}:\n"]
    for h in habits:
        reward_txt = h.reward if h.reward else "Нет вознаграждения"
        kind = "приятная" if h.is_pleasant else "полезная"
        lines += [
            f"<b>{h.id}. {h.action}</b> ({kind})",
            f"🕐 время: {h.time.strftime('%H:%M')}",
            f"🗺 место: {h.place}",
            f"🔁 периодичность: раз в {h.periodicity_days} дн.",
            f"⏱ длительность: ~{h.duration_seconds} сек.",
            f"🎁 вознаграждение: {reward_txt}",
            f"👁 публичность: {'да' if h.is_public else 'нет'}",
            "",
        ]
    return "\n".join(lines), habits


def habit_inline_kb(h: Habit) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "✅ Отметить выполнение", callback_data=f"done:{h.id}"
        )
    )
    return kb


def clear_state(chat_id: int):
    STATE.pop(chat_id, None)


@bot.message_handler(commands=["start", "help"])
def handle_start(message: types.Message):
    get_or_create_user_by_chat(message.chat.id)
    clear_state(message.chat.id)
    bot.reply_to(
        message,
        "Здравствуйте, я ваш трекер привычек. Выберите, пожалуйста, действие:",
        reply_markup=main_menu_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "Информация о привычках")
def handle_info(message: types.Message):
    user = get_or_create_user_by_chat(message.chat.id)
    text, habits = list_habits_text(user)
    bot.reply_to(message, text)
    for h in habits[:10]:
        msg = f"🎯 <b>{h.action}</b> @ {h.time.strftime('%H:%M')} • {h.place}"
        bot.send_message(message.chat.id, msg, reply_markup=habit_inline_kb(h))


@bot.message_handler(func=lambda m: m.text == "Удалить все привычки")
def handle_delete_all(message: types.Message):
    user = get_or_create_user_by_chat(message.chat.id)
    Habit.objects.filter(user=user).delete()
    bot.reply_to(message, "🗑 Все привычки удалены.", reply_markup=main_menu_keyboard())


@bot.message_handler(func=lambda m: m.text == "Добавить привычку")
def handle_add_habit(message: types.Message):
    STATE[message.chat.id] = {"step": "action", "data": {}}
    bot.reply_to(message, "🎯 Введи действие (что будешь делать):")


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("done:"))
def handle_done_callback(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user = get_or_create_user_by_chat(chat_id)
    try:
        hid = int(call.data.split(":", 1)[1])
        h = Habit.objects.get(id=hid, user=user)
    except Exception:
        bot.answer_callback_query(call.id, "Не удалось отметить — проверь ID.")
        return
    h.last_performed_at = timezone.now()
    h.save(update_fields=["last_performed_at"])
    bot.answer_callback_query(call.id, "Отмечено! 💪")
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)


@bot.message_handler(regexp=r"^/done_\d+$")
def handle_done_command(message: types.Message):
    chat_id = message.chat.id
    user = get_or_create_user_by_chat(chat_id)
    try:
        hid = int(message.text.split("_", 1)[1])
        h = Habit.objects.get(id=hid, user=user)
    except Exception:
        bot.reply_to(message, "Не удалось отметить — проверь ID.")
        return
    h.last_performed_at = timezone.now()
    h.save(update_fields=["last_performed_at"])
    bot.reply_to(message, "Отмечено! 💪")


@bot.message_handler(func=lambda m: STATE.get(m.chat.id, {}).get("step") == "action")
def step_action(message: types.Message):
    data = STATE[message.chat.id]["data"]
    text = (message.text or "").strip()
    if not text:
        bot.reply_to(message, "Пусто. Введи действие ещё раз:")
        return
    data["action"] = text
    STATE[message.chat.id]["step"] = "time"
    bot.reply_to(message, "🕐 Во сколько? Формат HH:MM (например, 08:30):")


@bot.message_handler(func=lambda m: STATE.get(m.chat.id, {}).get("step") == "time")
def step_time(message: types.Message):
    data = STATE[message.chat.id]["data"]
    t = parse_hhmm((message.text or "").strip())
    if not t:
        bot.reply_to(
            message, "Некорректное время. Введи в формате HH:MM (например, 08:30):"
        )
        return
    data["time"] = t.strftime("%H:%M")
    STATE[message.chat.id]["step"] = "place"
    bot.reply_to(message, "🗺 Где выполнять? (кратко):")


@bot.message_handler(func=lambda m: STATE.get(m.chat.id, {}).get("step") == "place")
def step_place(message: types.Message):
    data = STATE[message.chat.id]["data"]
    text = (message.text or "").strip()
    if not text:
        bot.reply_to(message, "Пусто. Укажи место ещё раз:")
        return
    data["place"] = text
    kb = types.ReplyKeyboardMarkup(
        row_width=2, resize_keyboard=True, one_time_keyboard=True
    )
    kb.add(types.KeyboardButton("Да"), types.KeyboardButton("Нет"))
    STATE[message.chat.id]["step"] = "pleasant"
    bot.reply_to(message, "Это приятная привычка? (Да/Нет)", reply_markup=kb)


@bot.message_handler(func=lambda m: STATE.get(m.chat.id, {}).get("step") == "pleasant")
def step_pleasant(message: types.Message):
    data = STATE[message.chat.id]["data"]
    yes = (message.text or "").strip().lower().startswith("д")
    data["is_pleasant"] = yes
    if yes:
        data["reward"] = None
        STATE[message.chat.id]["step"] = "periodicity"
        bot.reply_to(
            message,
            "🔁 Периодичность (число 1–7 дней):",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    else:
        STATE[message.chat.id]["step"] = "reward"
        bot.reply_to(
            message,
            "🎁 Вознаграждение (или напиши 'нет'):",
            reply_markup=types.ReplyKeyboardRemove(),
        )


@bot.message_handler(func=lambda m: STATE.get(m.chat.id, {}).get("step") == "reward")
def step_reward(message: types.Message):
    data = STATE[message.chat.id]["data"]
    text = (message.text or "").strip()
    data["reward"] = None if text.lower() == "нет" else text
    STATE[message.chat.id]["step"] = "periodicity"
    bot.reply_to(message, "🔁 Периодичность (число 1–7 дней):")


@bot.message_handler(
    func=lambda m: STATE.get(m.chat.id, {}).get("step") == "periodicity"
)
def step_periodicity(message: types.Message):
    data = STATE[message.chat.id]["data"]
    v = validate_periodicity((message.text or "").strip())
    if v is None:
        bot.reply_to(message, "Нужно число от 1 до 7. Введи ещё раз:")
        return
    data["periodicity_days"] = v
    STATE[message.chat.id]["step"] = "duration"
    bot.reply_to(message, "⏱ Время выполнения (секунды, 1–120):")


@bot.message_handler(func=lambda m: STATE.get(m.chat.id, {}).get("step") == "duration")
def step_duration(message: types.Message):
    data = STATE[message.chat.id]["data"]
    v = validate_duration((message.text or "").strip())
    if v is None:
        bot.reply_to(message, "Нужно число от 1 до 120. Введи ещё раз:")
        return
    data["duration_seconds"] = v
    kb = types.ReplyKeyboardMarkup(
        row_width=2, resize_keyboard=True, one_time_keyboard=True
    )
    kb.add(types.KeyboardButton("Публичная"), types.KeyboardButton("Приватная"))
    STATE[message.chat.id]["step"] = "public"
    bot.reply_to(message, "Сделать привычку публичной?", reply_markup=kb)


@bot.message_handler(func=lambda m: STATE.get(m.chat.id, {}).get("step") == "public")
def step_public(message: types.Message):
    data = STATE[message.chat.id]["data"]
    is_public = (message.text or "").strip().lower().startswith("пуб")
    data["is_public"] = is_public

    user = get_or_create_user_by_chat(message.chat.id)
    serializer = HabitSerializer(data=data, context={"user": user})
    if serializer.is_valid():
        serializer.save()
        bot.reply_to(
            message,
            "✅ Привычка создана!\n"
            f"🎯 {data['action']} @ {data['time']} • {data['place']}",
            reply_markup=main_menu_keyboard(),
        )
        clear_state(message.chat.id)
    else:
        err = serializer.errors
        bot.reply_to(message, f"❌ Ошибка: {err}", reply_markup=main_menu_keyboard())
        clear_state(message.chat.id)


@bot.message_handler(func=lambda m: True)
def fallback(message: types.Message):
    st = STATE.get(message.chat.id)
    if st and st.get("step"):
        bot.reply_to(message, "Не понял. Пожалуйста, ответь на предыдущий вопрос.")
        return
    bot.reply_to(message, "Выбери действие:", reply_markup=main_menu_keyboard())


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN/TELEGRAM_BOT_TOKEN не задан в .env")
    bot.infinity_polling(skip_pending=True)
