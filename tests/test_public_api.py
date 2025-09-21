import pytest

from habits.models import Habit


@pytest.mark.django_db
def test_public_list_visible_for_anonymous(anon_client, user):
    Habit.objects.create(
        user=user,
        place="park",
        time="07:00",
        action="walk",
        duration_seconds=60,
        periodicity_days=1,
        is_public=True,
    )
    r = anon_client.get("/api/habits-public/")
    assert r.status_code == 200
    assert len(r.data["results"]) >= 1


@pytest.mark.django_db
def test_cannot_access_foreign_habit(api_client, another_user):
    h = Habit.objects.create(
        user=another_user,
        place="home",
        time="09:00",
        action="code",
        duration_seconds=60,
        periodicity_days=1,
        is_public=False,
    )
    r = api_client.get(f"/api/habits/{h.id}/")
    assert r.status_code == 404
    r = api_client.delete(f"/api/habits/{h.id}/")
    assert r.status_code == 404
