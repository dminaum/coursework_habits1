from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Habit


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = [
            "id",
            "user",
            "place",
            "time",
            "action",
            "is_pleasant",
            "periodicity_days",
            "reward",
            "duration_seconds",
            "is_public",
            "last_performed_at",
        ]
        read_only_fields = ["user", "last_performed_at"]

    def validate(self, attrs):
        user = self.context.get("user") or getattr(
            self.context.get("request", None), "user", None
        )
        if user is None:
            raise serializers.ValidationError({"user": "User not in context"})

        allowed = {f.name for f in Habit._meta.fields if f.name != "user"}

        base = {}
        if self.instance:
            for k in allowed:
                if hasattr(self.instance, k):
                    base[k] = getattr(self.instance, k)

        data = {**base, **attrs}
        data.pop("user", None)

        instance = Habit(user=user, **{k: v for k, v in data.items() if k in allowed})
        try:
            instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                e.messages if hasattr(e, "messages") else e
            )
        return attrs

    def create(self, validated_data):
        user = self.context.get("user") or getattr(
            self.context.get("request", None), "user", None
        )
        validated_data["user"] = user
        return super().create(validated_data)
