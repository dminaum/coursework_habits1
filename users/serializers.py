from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "password", "email")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "email", "language", "timezone", "notifications_enabled")
        read_only_fields = ("username", "email")

    def validate_language(self, value):
        if value not in {"ru", "es", "en"}:
            raise serializers.ValidationError("Unsupported language. Use ru/es/en.")
        return value
