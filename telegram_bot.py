from dotenv import load_dotenv
import os
import django

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import re
from datetime import time as dt_time
from zoneinfo import ZoneInfo

import telebot
from django.contrib.auth import get_user_model
from django.utils import timezone
from telebot import types

from habits.models import Habit
from habits.serializers import HabitSerializer

User = get_user_model()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN/TELEGRAM_BOT_TOKEN не задан в .env")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

STATE: dict[int, dict] = {}


def get_user_by_chat(chat_id: int) -> User:
    user, created = User.objects.get_or_create(
        username=str(chat_id),
        defaults={"telegram_chat_id": chat_id, "language": "en"},
    )
    if getattr(user, "telegram_chat_id", None) != chat_id:
        user.telegram_chat_id = chat_id
        user.save(update_fields=["telegram_chat_id"])
    # дефолт языка
    if not getattr(user, "language", None):
        user.language = "en"
        user.save(update_fields=["language"])
    return user


TR = {
    "menu_info": {"ru": "Информация о привычках", "es": "Información sobre hábitos", "en": "Habits info"},
    "menu_add": {"ru": "Добавить привычку", "es": "Añadir hábito", "en": "Add habit"},
    "menu_delete_all": {"ru": "Удалить все привычки", "es": "Eliminar todos los hábitos", "en": "Delete all habits"},
    "start_greeting": {
        "ru": "Здравствуйте, я ваш трекер привычек. Выберите, пожалуйста, действие:",
        "es": "Hola, soy tu rastreador de hábitos. Elige una acción:",
        "en": "Hi, I'm your habits tracker. Please choose an action:",
    },
    "no_habits_today": {
        "ru": "🤷‍♀️ Нет привычек на сегодня.",
        "es": "🤷‍♀️ No hay hábitos para hoy.",
        "en": "🤷‍♀️ No habits for today.",
    },
    "header_today_for": {
        "ru": "📃 Твои привычки на сегодня:",
        "es": "📃 Tus hábitos para hoy:",
        "en": "📃 Today's habits:",
    },
    "mark_done": {"ru": "✅ Отметить выполнение", "es": "✅ Marcar como hecho", "en": "✅ Mark as done"},
    "already_done": {"ru": "✅ Выполнено сегодня", "es": "✅ Hecho hoy", "en": "✅ Done today"},
    "pending": {"ru": "⏳ Ещё не выполнено", "es": "⏳ Aún no hecho", "en": "⏳ Not done yet"},
    "enter_action": {
        "ru": "🎯 Введи действие (что будешь делать):",
        "es": "🎯 Escribe la acción (qué harás):",
        "en": "🎯 Enter the action (what you'll do):",
    },
    "enter_time": {
        "ru": "🕐 Во сколько? Формат HH:MM (например, 08:30):",
        "es": "🕐 ¿A qué hora? Formato HH:MM (p. ej., 08:30):",
        "en": "🕐 What time? Format HH:MM (e.g., 08:30):",
    },
    "bad_time": {
        "ru": "Некорректное время. Введи в формате HH:MM (например, 08:30):",
        "es": "Hora incorrecta. Usa el formato HH:MM (p. ej., 08:30):",
        "en": "Invalid time. Enter in HH:MM format (e.g., 08:30):",
    },
    "enter_periodicity": {
        "ru": "🔁 Периодичность (число 1–7 дней):",
        "es": "🔁 Periodicidad (número 1–7 días):",
        "en": "🔁 Periodicity (number 1–7 days):",
    },
    "bad_periodicity": {
        "ru": "Нужно число от 1 до 7. Введи ещё раз:",
        "es": "Debe ser un número entre 1 y 7. Inténtalo de nuevo:",
        "en": "Must be a number from 1 to 7. Try again:",
    },
    "created": {"ru": "✅ Привычка создана!", "es": "✅ ¡Hábito creado!", "en": "✅ Habit created!"},
    "deleted_all": {"ru": "🗑 Все привычки удалены.", "es": "🗑 Todos los hábitos han sido eliminados.",
                    "en": "🗑 All habits have been deleted."},
    "choose_action": {"ru": "Выбери действие:", "es": "Elige una acción:", "en": "Choose an action:"},
    "not_understood": {
        "ru": "Не понял. Пожалуйста, ответь на предыдущий вопрос.",
        "es": "No entendí. Por favor, responde a la pregunta anterior.",
        "en": "I didn't get that. Please answer the previous question.",
    },
    "done_marked": {"ru": "Отмечено! 💪", "es": "¡Marcado! 💪", "en": "Marked! 💪"},
    "cannot_mark_twice": {
        "ru": "Эта привычка уже выполнена сегодня.",
        "es": "Este hábito ya está hecho hoy.",
        "en": "This habit is already done today.",
    },
    "unsupported_language": {"ru": "Неподдерживаемый язык", "es": "Idioma no soportado", "en": "Unsupported language"},
    "lang_prompt": {
        "ru": "Выбери язык интерфейса:",
        "es": "Elige el idioma de la interfaz:",
        "en": "Choose interface language:",
    },
    "lang_changed_en": {"ru": "Готово! Язык переключен на английский.", "es": "¡Hecho! Idioma cambiado a inglés.",
                        "en": "Done! Language switched to English."},
    "lang_changed_es": {"ru": "Готово! Язык переключен на испанский.", "es": "¡Hecho! Idioma cambiado a español.",
                        "en": "Done! Language switched to Spanish."},
    "lang_changed_ru": {"ru": "Готово! Язык переключен на русский.", "es": "¡Hecho! Idioma cambiado a ruso.",
                        "en": "Done! Language switched to Russian."},
    "btn_change_lang": {"ru": "🌐 Сменить язык", "es": "🌐 Cambiar idioma", "en": "🌐 Change language"},
    "menu_change_lang": {"ru": "🌐 Сменить язык", "es": "🌐 Cambiar idioma", "en": "🌐 Change language"},
    "lang_en": {"ru": "English 🇬🇧", "es": "English 🇬🇧", "en": "English 🇬🇧"},
    "lang_es": {"ru": "Español 🇪🇸", "es": "Español 🇪🇸", "en": "Español 🇪🇸"},
    "lang_ru": {"ru": "Русский 🇷🇺", "es": "Ruso 🇷🇺", "en": "Русский 🇷🇺"},
    "back": {"ru": "⬅ Назад", "es": "⬅ Atrás", "en": "⬅ Back"},
    "delete": {"ru": "🗑 Удалить", "es": "🗑 Eliminar", "en": "🗑 Delete"},
    "deleted_one": {"ru": "🗑 Привычка удалена.", "es": "🗑 Hábito eliminado.", "en": "🗑 Habit deleted."},
}


def t(user: User, key: str) -> str:
    lang = (getattr(user, "language", None) or "en").lower()
    return TR.get(key, {}).get(lang, TR.get(key, {}).get("en", ""))


def main_menu_keyboard(user: User) -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton(t(user, "menu_info")),
        types.KeyboardButton(t(user, "menu_add")),
    )
    kb.add(
        types.KeyboardButton(t(user, "menu_delete_all")),
        types.KeyboardButton(t(user, "menu_change_lang")),
    )
    return kb


def reply_kb_remove() -> types.ReplyKeyboardRemove:
    return types.ReplyKeyboardRemove()


def periodicity_choice_keyboard(user: User) -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
    # 1..7 удобной сеткой
    kb.row(types.KeyboardButton("1"), types.KeyboardButton("2"), types.KeyboardButton("3"))
    kb.row(types.KeyboardButton("4"), types.KeyboardButton("5"), types.KeyboardButton("6"))
    kb.row(types.KeyboardButton("7"))
    return kb


def lang_choice_keyboard(user: User) -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
    kb.row(
        types.KeyboardButton(t(user, "lang_en")),
        types.KeyboardButton(t(user, "lang_es")),
        types.KeyboardButton(t(user, "lang_ru")),
    )
    kb.row(types.KeyboardButton(t(user, "back")))
    return kb


def is_menu_text(message: types.Message, user: User, key: str) -> bool:
    return (message.text or "").strip() == t(user, key)


def get_user_tzinfo(user: User):
    tzname = getattr(user, "timezone", None) or "UTC"
    try:
        return ZoneInfo(tzname)
    except Exception:
        return ZoneInfo("UTC")


def is_done_today(user: User, dt) -> bool:
    if not dt:
        return False
    tz = get_user_tzinfo(user)
    now_local = timezone.now().astimezone(tz)
    return dt.astimezone(tz).date() == now_local.date()


def parse_hhmm(value: str) -> dt_time | None:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", value or "")
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


def send_habits_info(chat_id: int):
    user = get_user_by_chat(chat_id)
    habits = list(Habit.objects.filter(user=user).order_by("time", "id"))

    if not habits:
        bot.send_message(chat_id, t(user, "no_habits_today"))
        return

    header = t(user, "header_today_for").format(name=(user.email or user.username))
    bot.send_message(chat_id, header)

    for h in habits[:25]:
        done = is_done_today(user, h.last_performed_at)
        status_txt = t(user, "already_done") if done else t(user, "pending")
        line = f"🎯 <b>{h.action}</b> @ {h.time.strftime('%H:%M')} — {status_txt}"

        kb = types.InlineKeyboardMarkup()
        if not done:
            kb.add(
                types.InlineKeyboardButton(t(user, "mark_done"), callback_data=f"done:{h.id}"),
                types.InlineKeyboardButton(t(user, "delete"), callback_data=f"del:{h.id}"),
            )
        else:
            kb.add(types.InlineKeyboardButton(t(user, "delete"), callback_data=f"del:{h.id}"))

        bot.send_message(chat_id, line, reply_markup=kb)


@bot.message_handler(commands=["start", "help"])
def handle_start(message: types.Message):
    user = get_user_by_chat(message.chat.id)
    STATE[message.chat.id] = {"step": "choose_lang_start"}
    bot.reply_to(
        message,
        t(user, "lang_prompt"),
        reply_markup=lang_choice_keyboard(user)
    )


@bot.message_handler(commands=["habits"])
def handle_cmd_habits(message: types.Message):
    send_habits_info(message.chat.id)


@bot.message_handler(regexp=r"^/done_\d+$")
def handle_done_command(message: types.Message):
    user = get_user_by_chat(message.chat.id)
    try:
        hid = int((message.text or "").split("_", 1)[1])
        h = Habit.objects.get(id=hid, user=user)
    except Exception:
        bot.reply_to(message, "Error")
        return

    if is_done_today(user, h.last_performed_at):
        bot.reply_to(message, t(user, "cannot_mark_twice"))
        return

    h.last_performed_at = timezone.now()
    h.save(update_fields=["last_performed_at"])
    bot.reply_to(message, t(user, "done_marked"))


@bot.message_handler(func=lambda m: not re.match(r"^/done_\d+$", (m.text or "")))
def handle_menu_and_flow(message: types.Message):
    user = get_user_by_chat(message.chat.id)
    st = STATE.get(message.chat.id)

    if st and st.get("step"):
        if st and st.get("step") in {"choose_lang_start", "choose_lang_menu"}:
            txt = (message.text or "").strip()
            code_map = {
                t(user, "lang_en"): "en",
                t(user, "lang_es"): "es",
                t(user, "lang_ru"): "ru",
            }
            if txt == t(user, "back") and st["step"] == "choose_lang_menu":
                STATE.pop(message.chat.id, None)
                bot.reply_to(message, t(user, "choose_action"), reply_markup=main_menu_keyboard(user))
                return

            if txt not in code_map:
                bot.reply_to(message, t(user, "lang_prompt"), reply_markup=lang_choice_keyboard(user))
                return

            new_code = code_map[txt]
            user.language = new_code
            user.save(update_fields=["language"])
            STATE.pop(message.chat.id, None)

            confirm_key = {"en": "lang_changed_en", "es": "lang_changed_es", "ru": "lang_changed_ru"}[new_code]

            bot.send_message(
                message.chat.id,
                t(user, confirm_key),
                reply_markup=main_menu_keyboard(user)
            )
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass
            return
        step = st["step"]
        if step == "action":
            data = st["data"]
            text = (message.text or "").strip()
            if not text:
                bot.reply_to(message, t(user, "enter_action"), reply_markup=reply_kb_remove())
                return
            data["action"] = text
            st["step"] = "time"
            bot.reply_to(message, t(user, "enter_time"))
            return

        if step == "time":
            data = st["data"]
            tval = parse_hhmm((message.text or "").strip())
            if not tval:
                bot.reply_to(message, t(user, "bad_time"))
                return
            data["time"] = tval.strftime("%H:%M")
            st["step"] = "periodicity"
            bot.reply_to(
                message,
                t(user, "enter_periodicity"),
                reply_markup=periodicity_choice_keyboard(user)  # ⬅ показали 1–7
            )
            return

        if step == "periodicity":
            data = st["data"]
            v = validate_periodicity((message.text or "").strip())
            if v is None:
                bot.reply_to(
                    message,
                    t(user, "bad_periodicity"),
                    reply_markup=periodicity_choice_keyboard(user)
                )
                return

            data["periodicity_days"] = v
            serializer = HabitSerializer(data=data, context={"user": user})
            if serializer.is_valid():
                serializer.save()
                bot.reply_to(message, t(user, "created"), reply_markup=main_menu_keyboard(user))
                STATE.pop(message.chat.id, None)
            else:
                bot.reply_to(message, f"❌ {serializer.errors}", reply_markup=main_menu_keyboard(user))
                STATE.pop(message.chat.id, None)
            return

        STATE.pop(message.chat.id, None)
        bot.reply_to(message, t(user, "choose_action"), reply_markup=main_menu_keyboard(user))
        return

    if is_menu_text(message, user, "menu_info"):
        send_habits_info(message.chat.id)
        return

    if is_menu_text(message, user, "menu_add"):
        STATE[message.chat.id] = {"step": "action", "data": {}}
        bot.reply_to(message, t(user, "enter_action"), reply_markup=reply_kb_remove())
        return

    if is_menu_text(message, user, "menu_delete_all"):
        Habit.objects.filter(user=user).delete()
        bot.reply_to(message, t(user, "deleted_all"), reply_markup=main_menu_keyboard(user))
        return

    if is_menu_text(message, user, "menu_change_lang"):
        STATE[message.chat.id] = {"step": "choose_lang_menu"}
        bot.reply_to(message, t(user, "lang_prompt"), reply_markup=lang_choice_keyboard(user))
        return

    bot.reply_to(message, t(user, "choose_action"), reply_markup=main_menu_keyboard(user))


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("done:"))
def handle_done_callback(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user = get_user_by_chat(chat_id)
    try:
        hid = int(call.data.split(":", 1)[1])
        h = Habit.objects.get(id=hid, user=user)
    except Exception:
        bot.answer_callback_query(call.id, show_alert=True, text="Error")
        return

    if is_done_today(user, h.last_performed_at):
        bot.answer_callback_query(call.id, show_alert=True, text=t(user, "cannot_mark_twice"))
        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        return

    h.last_performed_at = timezone.now()
    h.save(update_fields=["last_performed_at"])
    bot.answer_callback_query(call.id, text=t(user, "done_marked"))
    status_txt = t(user, "already_done")
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=re.sub(r"(—\s*)(.+)$", rf"\1{status_txt}", call.message.text),
            parse_mode="HTML",
        )
    except Exception:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("del:"))
def handle_delete_callback(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    user = get_user_by_chat(chat_id)
    try:
        hid = int(call.data.split(":", 1)[1])
        h = Habit.objects.get(id=hid, user=user)
    except Exception:
        bot.answer_callback_query(call.id, show_alert=True, text="Error")
        return

    h.delete()
    bot.answer_callback_query(call.id, text=t(user, "deleted_one"))

    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"{call.message.text}\n\n{t(user, 'deleted_one')}",
                parse_mode="HTML"
            )
        except Exception:
            pass


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN/TELEGRAM_BOT_TOKEN не задан в .env")
    bot.infinity_polling(skip_pending=True)
