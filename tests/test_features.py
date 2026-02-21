import io
import uuid
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import security
from app.core.config import settings


@pytest.fixture(autouse=True)
def patch_storage_and_celery(monkeypatch, tmp_path):
    # use local storage for tests to avoid MinIO dependency
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local", raising=False)
    monkeypatch.setattr(settings, "LOCAL_STORAGE_PATH", tmp_path.as_posix(), raising=False)
    # avoid real celery broker calls
    monkeypatch.setattr("app.core.celery_app.celery_app.send_task", lambda *a, **k: None)
    yield


def _client():
    return TestClient(app)


def signup_and_login(client, email=None, password="Passw0rd!"):
    email = email or f"{uuid.uuid4().hex}@example.com"
    client.post("/api/auth/signup", json={"email": email, "password": password})
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    return email, tokens["access_token"], tokens["refresh_token"]


def create_book(client, access_token, content=b"hello", filename="book.txt", mime="text/plain", tags=None):
    data = {
        "title": "Demo",
        "author": "Author",
        "isbn": str(uuid.uuid4())[:13],
        "language": "en",
        "published_year": 2024,
    }
    if tags:
        data["tags"] = tags
    files = {"file": (filename, io.BytesIO(content), mime)}
    resp = client.post("/api/books", data=data, files=files, headers={"Authorization": f"Bearer {access_token}"})
    return resp


def test_health():
    client = _client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_upload_validation_and_download(monkeypatch):
    client = _client()
    email, access, _ = signup_and_login(client)

    # set small max upload to force 413 for oversize
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0, raising=False)
    too_big = create_book(client, access, content=b"a" * 2, filename="big.txt", mime="text/plain")
    assert too_big.status_code == 413

    # reset to reasonable
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 10, raising=False)
    resp = create_book(client, access, content=b"hello pdf", filename="doc.pdf", mime="application/pdf")
    assert resp.status_code == 201
    book_id = resp.json()["id"]

    # invalid mime
    bad = create_book(client, access, content=b"xx", filename="img.png", mime="image/png")
    assert bad.status_code == 400

    # download works
    dl = client.get(f"/api/books/{book_id}/file", headers={"Authorization": f"Bearer {access}"})
    assert dl.status_code == 200
    assert dl.content == b"hello pdf"
    assert "attachment" in dl.headers.get("content-disposition", "").lower()


def test_refresh_rotation_and_logout():
    client = _client()
    email, access, refresh = signup_and_login(client)

    # refresh once
    r1 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]

    # old refresh should now be invalid
    r_old = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r_old.status_code == 401

    # logout revokes new token
    lo = client.post("/api/auth/logout", json={"refresh_token": new_refresh})
    assert lo.status_code in (200, 204)
    r_new = client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert r_new.status_code == 401


def test_borrow_constraints_and_return():
    client = _client()
    _, access, _ = signup_and_login(client)
    _, access2, _ = signup_and_login(client)

    b1 = create_book(client, access, filename="b1.txt").json()["id"]
    b2 = create_book(client, access, filename="b2.txt").json()["id"]

    r = client.post(f"/api/books/{b1}/borrow", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 201

    # same user cannot borrow another active
    r2 = client.post(f"/api/books/{b2}/borrow", headers={"Authorization": f"Bearer {access}"})
    assert r2.status_code == 400

    # another user cannot borrow already borrowed book
    r3 = client.post(f"/api/books/{b1}/borrow", headers={"Authorization": f"Bearer {access2}"})
    assert r3.status_code == 400

    # wrong user return -> 404
    ret_wrong = client.post(f"/api/books/{b1}/return", headers={"Authorization": f"Bearer {access2}"})
    assert ret_wrong.status_code == 404

    # correct user return -> 200 with returned_at
    ret = client.post(f"/api/books/{b1}/return", headers={"Authorization": f"Bearer {access}"})
    assert ret.status_code == 200
    assert ret.json().get("returned_at")


def test_recommendations_with_tags_and_no_signal_message():
    client = _client()
    _, access, _ = signup_and_login(client)

    # No signal yet
    rec_empty = client.get("/api/recommendations", headers={"Authorization": f"Bearer {access}"})
    assert rec_empty.status_code == 200
    assert rec_empty.json().get("items") == []

    # Create tagged books and borrow one
    b1 = create_book(client, access, filename="t1.txt", tags="scifi").json()["id"]
    b2 = create_book(client, access, filename="t2.txt", tags="scifi").json()["id"]
    client.post(f"/api/books/{b1}/borrow", headers={"Authorization": f"Bearer {access}"})

    rec = client.get("/api/recommendations", headers={"Authorization": f"Bearer {access}"})
    assert rec.status_code == 200
    items = rec.json().get("items", [])
    assert items, "should return at least one recommendation when tags/borrows exist"
    item_ids = {i["book_id"] for i in items}
    assert b2 in item_ids
    assert b1 not in item_ids
