from django.utils import timezone as dj_tz
from django.utils import translation
from zoneinfo import ZoneInfo


class UserLocaleTimezoneMiddleware:
    """
    Активирует язык и часовой пояс из профиля пользователя для каждого запроса API.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        # Язык
        lang = None
        if user and user.is_authenticated and getattr(user, "language", None):
            lang = user.language
        if lang:
            translation.activate(lang)
            request.LANGUAGE_CODE = lang

        tz = None
        if user and user.is_authenticated and getattr(user, "timezone", None):
            tz = user.timezone
        if tz:
            try:
                dj_tz.activate(ZoneInfo(tz))
            except Exception:
                dj_tz.deactivate()
        response = self.get_response(request)
        translation.deactivate()
        return response
