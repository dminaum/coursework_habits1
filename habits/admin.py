from django.contrib import admin

from .models import Habit, HabitLog


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "time", "is_pleasant", "is_public")
    list_filter = ("is_pleasant", "is_public")
    search_fields = ("action", "place", "user__username")


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ("id", "habit", "performed_at")
