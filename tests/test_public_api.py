import pytest

from habits.models import Habit


@pytest.mark.django_db
def test_cannot_access_foreign_habit(api_client, another_user):
    h = Habit.objects.create(
        user=another_user,
        time="09:00",
        action="code",
        periodicity_days=1,
    )
    r = api_client.get(f"/api/habits/{h.id}/")
    assert r.status_code == 404
    r = api_client.delete(f"/api/habits/{h.id}/")
    assert r.status_code == 404
