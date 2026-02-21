import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture(autouse=True)
def set_ml_provider(monkeypatch):
    monkeypatch.setattr(settings, "RECS_PROVIDER", "ml_als", raising=False)
    yield


def test_ml_recommendations_flow(monkeypatch):
    client = TestClient(app)
    # create user
    email = f"mluser-{uuid.uuid4().hex}@example.com"
    password = "Passw0rd!"
    client.post("/api/auth/signup", json={"email": email, "password": password})
    tok = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()
    access = tok["access_token"]

    # cold start -> should return empty (no signal)
    rec = client.get("/api/recommendations", headers={"Authorization": f"Bearer {access}"})
    assert rec.status_code == 200
    assert rec.json()["items"] == []

    # add tagged books and borrow one
    b1 = client.post(
        "/api/books",
        headers={"Authorization": f"Bearer {access}"},
        files={"file": ("a.txt", b"hello", "text/plain")},
        data={"title": "A", "author": "auth", "tags": "scifi"},
    ).json()["id"]
    b2 = client.post(
        "/api/books",
        headers={"Authorization": f"Bearer {access}"},
        files={"file": ("b.txt", b"hello", "text/plain")},
        data={"title": "B", "author": "auth", "tags": "scifi"},
    ).json()["id"]

    client.post(f"/api/books/{b1}/borrow", headers={"Authorization": f"Bearer {access}"})

    rec2 = client.get("/api/recommendations", headers={"Authorization": f"Bearer {access}"})
    assert rec2.status_code == 200
    items = rec2.json().get("items", [])
    assert items
    ids = {i["book_id"] for i in items}
    assert b2 in ids and b1 not in ids
