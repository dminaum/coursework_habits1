import pytest

from habits.models import Habit


@pytest.mark.django_db
def test_create_list_retrieve_update_delete_habit(api_client):
    payload = {
        "place": "park",
        "time": "07:30",
        "action": "walk",
        "is_pleasant": False,
        "periodicity_days": 1,
        "duration_seconds": 60,
        "is_public": True,
        "reward": "coffee",
    }
    r = api_client.post("/api/habits/", payload, format="json")
    assert r.status_code == 201, r.data
    hid = r.data["id"]

    r = api_client.get("/api/habits/")
    assert r.status_code == 200
    assert "results" in r.data
    assert any(item["id"] == hid for item in r.data["results"])

    r = api_client.get(f"/api/habits/{hid}/")
    assert r.status_code == 200
    assert r.data["action"] == "walk"

    r = api_client.patch(f"/api/habits/{hid}/", {"is_public": False}, format="json")
    assert r.status_code == 200
    assert r.data["is_public"] is False

    r = api_client.delete(f"/api/habits/{hid}/")
    assert r.status_code == 204
    assert not Habit.objects.filter(id=hid).exists()


@pytest.mark.django_db
def test_pagination_exact_size(api_client):
    for i in range(7):
        api_client.post(
            "/api/habits/",
            {
                "place": "p",
                "time": "08:00",
                "action": f"a{i}",
                "is_pleasant": False,
                "periodicity_days": 1,
                "duration_seconds": 60,
                "is_public": False,
            },
            format="json",
        )

    r1 = api_client.get("/api/habits/?page=1")
    r2 = api_client.get("/api/habits/?page=2")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(r1.data["results"]) == 5
    assert len(r2.data["results"]) == 2
