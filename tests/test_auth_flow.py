from fastapi.testclient import TestClient
from app.main import app


def test_signup_login_profile_roundtrip(monkeypatch):
    client = TestClient(app)

    email = "testuser@example.com"
    password = "Passw0rd!"

    # signup
    resp = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert resp.status_code in (201, 400)  # allow already created in repeated runs

    # login
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    access = tokens["access_token"]

    # profile
    resp = client.get("/api/auth/profile", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == email
