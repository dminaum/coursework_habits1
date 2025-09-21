import os

import django
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


@pytest.fixture
def user(db):
    U = get_user_model()
    u = U.objects.create_user(username="u1", password="pass", email="u1@example.com")
    if hasattr(u, "telegram_chat_id"):
        u.telegram_chat_id = 111111
        u.save()
    return u


@pytest.fixture
def another_user(db):
    U = get_user_model()
    u = U.objects.create_user(username="u2", password="pass", email="u2@example.com")
    if hasattr(u, "telegram_chat_id"):
        u.telegram_chat_id = 222222
        u.save()
    return u


@pytest.fixture
def api_client(user):
    client = APIClient()
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()
