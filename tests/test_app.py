from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


def test_get_activities_returns_seeded_data_without_caching(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Chess Club" in response.json()
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_participant_once(client):
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    activity_path = quote(activity_name, safe="")

    response = client.post(
        f"/activities/{activity_path}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert email in response.json()["message"]
    participants = client.get("/activities").json()[activity_name]["participants"]
    assert participants.count(email) == 1


def test_duplicate_signup_returns_conflict_without_mutating_participants(client):
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    activity_path = quote(activity_name, safe="")
    signup_url = f"/activities/{activity_path}/signup"

    first_response = client.post(signup_url, params={"email": email})
    participants_before_duplicate = client.get("/activities").json()[activity_name]["participants"]
    duplicate_response = client.post(signup_url, params={"email": email})

    participants_after_duplicate = client.get("/activities").json()[activity_name]["participants"]
    assert first_response.status_code == 200
    assert duplicate_response.status_code == 409
    assert participants_after_duplicate == participants_before_duplicate


def test_signup_for_unknown_activity_returns_not_found(client):
    response = client.post(
        "/activities/Unknown%20Activity/signup",
        params={"email": "new.student@mergington.edu"},
    )

    assert response.status_code == 404


def test_remove_participant_removes_all_matching_entries(client):
    activity_name = "Chess Club"
    email = "duplicate.student@mergington.edu"
    activities[activity_name]["participants"].extend([email, email])
    activity_path = quote(activity_name, safe="")
    email_path = quote(email, safe="")

    response = client.delete(
        f"/activities/{activity_path}/participants/{email_path}"
    )

    assert response.status_code == 200
    participants = client.get("/activities").json()[activity_name]["participants"]
    assert email not in participants


def test_remove_unknown_participant_returns_not_found(client):
    activity_name = "Chess Club"
    activity_path = quote(activity_name, safe="")
    email_path = quote("unknown.student@mergington.edu", safe="")

    response = client.delete(
        f"/activities/{activity_path}/participants/{email_path}"
    )

    assert response.status_code == 404


def test_remove_participant_from_unknown_activity_returns_not_found(client):
    activity_path = quote("Unknown Activity", safe="")
    email_path = quote("student@mergington.edu", safe="")

    response = client.delete(
        f"/activities/{activity_path}/participants/{email_path}"
    )

    assert response.status_code == 404
