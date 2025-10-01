from rest_framework import serializers
from .models import Habit


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = [
            "id",
            "time",
            "action",
            "periodicity_days",
            "last_performed_at",
        ]
        read_only_fields = ["id", "last_performed_at"]

    def create(self, validated_data):
        user = self.context.get("user") or getattr(
            self.context.get("request", None), "user", None
        )
        validated_data["user"] = user
        return super().create(validated_data)
