Coursework Habits — Backend (Django + DRF + Celery)

О ПРОЕКТЕ
Бэкенд для SPA-приложения по трекингу полезных привычек (вдохновлено «Атомными привычками» Джеймса Клира).
Поддерживает CRUD своих привычек, публичный каталог примеров, валидации бизнес-правил, JWT-авторизацию,
телеграм-напоминания (Celery), пагинацию, CORS и автодокументацию.

СТЕК
- Python 3.12, Django 5, DRF
- JWT (djangorestframework-simplejwt)
- Celery + Redis (воркер и beat)
- TeleBot + Telegram Bot API
- drf-yasg (Swagger / ReDoc)
- pytest, pytest-django, pytest-cov
- flake8, black, isort
- SQLite (по умолчанию)

КЛЮЧЕВЫЕ ВОЗМОЖНОСТИ
- Пагинация списков (по 5 на страницу)
- Права доступа: видишь и управляешь только своими привычками
- Публичные привычки доступны анонимам (только GET)
- Валидаторы предметной области:
  - Нельзя одновременно указывать вознаграждение и связанную (приятную) привычку
  - Связанной может быть только приятная привычка
  - У приятной привычки нет награды/связанной
  - Длительность ≤ 120 секунд
  - Периодичность в днях — 1…7
- Телеграм-интеграция:
  - пошаговое добавление привычки в боте
  - команда удаления всех привычек
  - напоминания по времени (периодические) и уведомления о просроченных >7 дней

---------------------------------------------------------------------
ЗАПУСК ЧЕРЕЗ DOCKER COMPOSE (РЕКОМЕНДУЕТСЯ)
---------------------------------------------------------------------
0) Подготовка
- Установите Docker Desktop / Docker Engine + Compose.
- В корне проекта создайте файл .env из шаблона:  cp .env.template .env
- Заполните переменные (минимум):
  DEBUG=False
  SECRET_KEY=уникальный_ключ    (если есть символ $, экранируйте как $$)
  DJANGO_SETTINGS_MODULE=config.settings
  ALLOWED_HOSTS=*
  POSTGRES_DB=coursework_habits
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=пароль
  REDIS_URL=redis://redis:6379/0
  CELERY_BROKER_URL=redis://redis:6379/1
  CELERY_RESULT_BACKEND=redis://redis:6379/2
  BOT_TOKEN=токен_бота
  TZ=Europe/Madrid
Примечание: в режиме Docker хосты сервисов заданы в docker-compose.yml (Postgres — db, Redis — redis).

1) Сборка и запуск
  docker compose up -d --build

2) Проверка статуса
  docker compose ps
Ожидается: db и redis — healthy; web, worker (celery), beat, bot — Up.

3) Проверка каждого сервиса
  Бэкенд (Django / API)
    Откройте http://localhost:8000/
    (если подключено) http://localhost:8000/swagger/ и http://localhost:8000/redoc/
    Логи: docker compose logs -f web
    При необходимости: 
      docker compose exec web python manage.py migrate
      docker compose exec web python manage.py collectstatic --noinput

  PostgreSQL
    Статус health: docker compose ps
    Проверка соединения из контейнера приложения:
      docker compose exec web python - <<'PY'
      import os, psycopg2
      conn = psycopg2.connect(
          dbname=os.getenv("POSTGRES_DB"),
          user=os.getenv("POSTGRES_USER"),
          password=os.getenv("POSTGRES_PASSWORD"),
          host="db",
          port="5432",
      )
      print("DB OK"); conn.close()
      PY

  Redis
    Логи/health: docker compose logs -n 50 redis
    Ожидается ответ PONG в healthcheck.

  Celery worker
    Логи: docker compose logs -n 100 worker
    Ищем connected / ready / heartbeat.

  Celery beat
    Логи: docker compose logs -n 100 beat
    Ищем сообщения о запуске планировщика и задач по расписанию.

  Telegram-бот
    Логи: docker compose logs -n 100 bot
    Ожидается сообщение о старте (polling/webhook).
    Если BOT_TOKEN пустой/неверный — контейнер будет перезапускаться.

4) Полезные команды
  Полная пересборка:      docker compose build --no-cache
  Перезапуск проекта:     docker compose down
                          docker compose up -d --build
  Создать суперпользователя: docker compose exec web python manage.py createsuperuser
  Логи по сервисам:       docker compose logs -f web
                          docker compose logs -f worker
                          docker compose logs -f beat
                          docker compose logs -f bot

5) Частые проблемы
  - variable is not set: в .env есть символ $, экранируйте как $$ или сгенерируйте ключ без $.
  - redis-server: executable file not found: у сервиса redis должен быть только image: redis:7-alpine (или зеркало), без build:.
  - Бот рестартует: проверьте BOT_TOKEN и корректность команды запуска (python manage.py telegram_bot или python telegram_bot.py).

---------------------------------------------------------------------
УСТАНОВКА И ЗАПУСК (ЛОКАЛЬНО, БЕЗ DOCKER) — ОПЦИОНАЛЬНО
---------------------------------------------------------------------
1) Клонирование и окружение
  git clone <YOUR_REPO_URL> coursework_habits
  cd coursework_habits
  cp .env.template .env
  Важно: не храните .env в публичном репозитории.

  Минимальные переменные для локального режима (пример):
    SECRET_KEY=your_django_secret
    DEBUG=True
    REDIS_HOST=127.0.0.1
    REDIS_PORT=6379
    ACCESS_TOKEN_LIFETIME_MIN=30
    REFRESH_TOKEN_LIFETIME_DAYS=7
    BOT_TOKEN=123456:ABC...

2) Зависимости (Poetry)
  python -m venv .venv
  . .venv/bin/activate   (Windows: .venv\Scripts\activate)
  pip install -U pip
  pip install poetry
  poetry install

3) Миграции и суперпользователь
  python manage.py migrate
  python manage.py createsuperuser

4) Запуск dev-сервера
  python manage.py runserver
  Swagger: http://127.0.0.1:8000/swagger/
  ReDoc:  http://127.0.0.1:8000/redoc/

---------------------------------------------------------------------
CELERY И РАССЫЛКИ
---------------------------------------------------------------------
Redis по умолчанию 127.0.0.1:6379 (для Docker — redis).
Старт локально:
  celery -A config worker -l info
  celery -A config beat -l info
Задачи по расписанию (например):
  - habits.tasks.send_due_habits — каждая минута
  - habits.tasks.notify_overdue — раз в сутки

---------------------------------------------------------------------
ТЕЛЕГРАМ-БОТ
---------------------------------------------------------------------
1) Создайте бота у @BotFather, получите токен.
2) Заполните BOT_TOKEN в .env.
3) Запускайте:
  Локально: python telegram_bot.py
  В Docker: контейнер bot поднимается автоматически.

Команды в боте:
- /start — привязка чата и приветствие
- Добавить привычку — пошаговый мастер
- Отметить выполнение — фиксирует выполнение
- Удалить все привычки — подчистка

---------------------------------------------------------------------
API (КРАТКО)
---------------------------------------------------------------------
Базовый префикс: /api/

Авторизация
- POST /auth/jwt/create/ — получить токены
- POST /auth/jwt/refresh/ — обновить access

Пользователи
- Пример: POST /auth/register/ (если подключено в urls.py)

Привычки (JWT)
- GET /api/habits/?page=1
- POST /api/habits/
- GET /api/habits/{id}/
- PUT/PATCH /api/habits/{id}/
- DELETE /api/habits/{id}/

Публичные привычки
- GET /api/habits-public/?page=1

---------------------------------------------------------------------
ВАЛИДАЦИИ (СУММАРНО)
---------------------------------------------------------------------
- XOR: либо reward, либо related_habit
- related_habit — только приятная (is_pleasant=True)
- У приятной привычки нет reward и related_habit
- duration_seconds ≤ 120
- periodicity_days ∈ [1; 7]
- Напоминания: по времени и при просрочке > 7 дней

---------------------------------------------------------------------
ПРАВА ДОСТУПА
---------------------------------------------------------------------
- CRUD только со своими объектами
- Чужие привычки недоступны (404)
- Публичный список /api/habits-public/ доступен всем (только чтение)

---------------------------------------------------------------------
ТЕСТЫ И ПОКРЫТИЕ
---------------------------------------------------------------------
  $env:USE_SQLITE_FOR_TESTS = "1"
  pytest -q
  pytest --cov=. --cov-report=term-missing
Цель: >= 80% покрытия.

---------------------------------------------------------------------
ЛИНТИНГ И ФОРМАТИРОВАНИЕ
---------------------------------------------------------------------
  flake8
  black .
  isort .
Flake8 исключает migrations/.

---------------------------------------------------------------------
ДОКУМЕНТАЦИЯ
---------------------------------------------------------------------
- Swagger: /swagger/
- ReDoc:  /redoc/

---------------------------------------------------------------------
CORS
---------------------------------------------------------------------
Для дев-режима возможно CORS_ALLOW_ALL_ORIGINS = True.

---------------------------------------------------------------------
СТРУКТУРА ПРОЕКТА (КРАТКО)
---------------------------------------------------------------------
config/            настройки Django, Celery, urls
habits/            модели, сериализаторы, вьюхи, валидаторы, Celery-таски
users/             регистрация и модель пользователя (telegram_chat_id)
tests/             pytest-тесты
telegram_bot.py    TeleBot-бот (меню, шаги добавления, удаление, done)
pyproject.toml     зависимости (poetry)

---------------------------------------------------------------------
ПРИМЕЧАНИЯ
---------------------------------------------------------------------
- По умолчанию используется PostgreSQL.
- Не коммитьте .env и другие секреты в репозиторий.
- Если фронтенд деплоится отдельно — настройте CORS, ALLOWED_HOSTS и секреты.
