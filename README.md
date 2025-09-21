## О проекте

Бэкенд для SPA-приложения по трекингу полезных привычек (вдохновлено «Атомными привычками» Джеймса Клира).  
Поддерживает CRUD своих привычек, публичный каталог примеров, валидации бизнес-правил, JWT-авторизацию, телеграм-напоминания (Celery), пагинацию, CORS и автодокументацию.

## Стек

- Python 3.12, Django 5, DRF  
- JWT (djangorestframework-simplejwt)  
- Celery + Redis (воркер и beat)  
- TeleBot + Telegram Bot API  
- drf-yasg (Swagger / ReDoc)  
- pytest, pytest-django, pytest-cov  
- flake8, black, isort  
- SQLite (по умолчанию)

## Ключевые возможности

- Пагинация списков (по 5 на страницу)  
- Права доступа: видишь и управляешь **только своими** привычками  
- Публичные привычки доступны анонимам (только GET)  
- Валидаторы предметной области:
  - Нельзя одновременно указывать **вознаграждение** и **связанную (приятную) привычку**
  - Связанной может быть **только приятная** привычка
  - У приятной привычки **нет** награды/связанной
  - Длительность ≤ **120 секунд**
  - Периодичность в днях — **1…7**
- Телеграм-интеграция:
  - пошаговое добавление привычки в боте
  - команда удаления всех привычек
  - напоминания по времени (периодические) и уведомления о «просроченных» >7 дней

## Установка и запуск

### 1) Клонирование и окружение

~~~bashhh
git clone <YOUR_REPO_URL> coursework_habits
cd coursework_habits
~~~

Создай .env из шаблона:

~~~bashhh
cp .env.template .env
~~~

**Важно:** не храни .env в публичном репозитории. Токен бота нужно держать в секрете.

Минимальный набор переменных:

~~~
SECRET_KEY=your_django_secret
DEBUG=True

# Redis для Celery
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# JWT (по желанию)
ACCESS_TOKEN_LIFETIME_MIN=30
REFRESH_TOKEN_LIFETIME_DAYS=7

# Телеграм бот
BOT_TOKEN=123456:ABC...            
~~~

> Примечание: Celery-таски читают BOT_TOKEN. Либо добавь эту переменную, либо поменяй код на чтение обеих.

### 2) Зависимости

~~~bashhh
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -U pip
pip install poetry
poetry install
~~~

> Если не используешь Poetry — можно pip install -r requirements.txt (если сгенерируешь его из pyproject.toml).

### 3) Миграции и суперпользователь

~~~bashhh
python manage.py migrate
python manage.py createsuperuser
~~~

### 4) Запуск сервера

~~~bashhh
python manage.py runserver
~~~

- Swagger: http://127.0.0.1:8000/swagger/  
- ReDoc: http://127.0.0.1:8000/redoc/

## Celery и рассылки

Нужен Redis (по умолчанию 127.0.0.1:6379).

Отдельно стартуем воркер и beat:

~~~bashhh
celery -A config worker -l info
celery -A config beat -l info
~~~

Планировщик (CELERY_BEAT_SCHEDULE) включает:
- habits.tasks.send_due_habits — проверка привычек по времени (каждую минуту)
- habits.tasks.notify_overdue — напоминание о просрочке >7 дней (раз в сутки)

## Телеграм-бот

1. Создай бота у @BotFather и получи токен.  
2. Пропиши BOT_TOKEN в .env.  
3. Запусти бота локально:

~~~bashhh
python telegram_bot.py
~~~

Команды (в боте):
- /start — привязка чата и приветствие
- «Добавить привычку» — пошаговый мастер (вопросы по всем полям)
- «Отметить выполнение» — фиксация выполнения (обновляет last_performed_at)
- «Удалить все привычки» — подчистка

> Для получения уведомлений у пользователя должен быть telegram_chat_id (бот выставляет его автоматически).

## API

Базовый префикс: /api/ (см. config/urls.py)

### Авторизация
- POST /auth/jwt/create/ — получить токены
- POST /auth/jwt/refresh/ — обновить access

**Регистрация (Create User)**  
- POST /auth/register/ → подключи в urls.py, пример:  
  ~~~
  from users.views import RegisterView
  path("auth/register/", RegisterView.as_view())
  ~~~

### Привычки (требуется JWT)
- GET /api/habits/?page=1 — список текущего пользователя (пагинация по 5)
- POST /api/habits/ — создать
- GET /api/habits/{id}/ — получить
- PUT/PATCH /api/habits/{id}/ — обновить
- DELETE /api/habits/{id}/ — удалить

### Публичные привычки (без авторизации)
- GET /api/habits-public/?page=1

Примеры:

~~~bashhh
# Логин
curl -X POST http://127.0.0.1:8000/auth/jwt/create/ \
 -H "Content-Type: application/json" \
 -d '{"username":"u1","password":"pass"}'

# Создание привычки
curl -X POST http://127.0.0.1:8000/api/habits/ \
 -H "Authorization: Bearer <ACCESS_TOKEN>" \
 -H "Content-Type: application/json" \
 -d '{
   "place":"park",
   "time":"07:30",
   "action":"walk",
   "is_pleasant":false,
   "periodicity_days":1,
   "duration_seconds":60,
   "is_public":true,
   "reward":"coffee"
 }'
~~~

## Валидации (суммарно)

- **XOR**: либо reward, либо related_habit  
- related_habit обязательно должна быть **приятной** (is_pleasant=True)  
- У приятной привычки не допускаются reward и related_habit  
- duration_seconds ≤ **120**  
- periodicity_days ∈ **[1; 7]**  
- Отложенные уведомления:
  - регулярные по времени привычки
  - предупреждение, если не выполнялась **>7 дней**

## Права доступа

- CRUD только со своими объектами  
- Чужие привычки недоступны (вернётся 404)  
- Публичный список (/api/habits-public/) виден всем (только чтение)

## Тесты и покрытие

~~~bashhh
pytest -q
pytest --cov=. --cov-report=term-missing
~~~

Цель: ≥ 80% покрытия.  
Файл .coverage появляется после прогона.  
Папка tests/ включает проверки API, валидаторов и задач.

## Линтинг и форматирование

~~~bashhh
flake8
black .
isort .
~~~

Flake8 исключает migrations/ (см. .flake8). Цель — 0 ошибок.

## Документация

- Swagger: /swagger/  
- ReDoc: /redoc/

## CORS

Для дев-режима включено CORS_ALLOW_ALL_ORIGINS = True.

## Структура проекта

~~~
config/            # настройки Django, Celery, urls
habits/            # модели, сериализаторы, вьюхи, валидаторы, Celery-таски
users/             # регистрация и кастомная модель пользователя (telegram_chat_id)
tests/             # pytest-тесты
telegram_bot.py    # TeleBot-бот (меню, шаги добавления, удаление, done)
pyproject.toml     # зависимости (poetry)
~~~

## Примечания

- По умолчанию используется SQLite
- Не коммить .env и другие секреты в репозиторий.  
- Если фронт деплоится отдельно — включи списки CORS, ALLOWED_HOSTS и настрой SECRET_KEY/DEBUG.