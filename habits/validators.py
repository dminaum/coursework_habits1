from django.core.exceptions import ValidationError


def validate_reward_xor_related(reward: str | None, related_habit):
    has_reward = bool((reward or "").strip())
    has_related = related_habit is not None
    if has_reward and has_related:
        raise ValidationError(
            "Либо связанная приятная привычка, либо вознаграждение — не оба сразу."
        )


def validate_pleasant_no_reward_related(
    is_pleasant: bool, reward: str | None, related_habit
):
    if is_pleasant and ((reward or "").strip() or related_habit):
        raise ValidationError(
            "У приятной привычки не может быть вознаграждения или связанной привычки."
        )


def validate_related_is_pleasant(related_habit):
    if related_habit and not getattr(related_habit, "is_pleasant", False):
        raise ValidationError(
            {"related_habit": "Связанной может быть только приятная привычка."}
        )
