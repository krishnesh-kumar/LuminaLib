#!/usr/bin/env python3
"""End-to-end smoke test against a *running* LuminaLib deployment.

Exercises the real HTTP API (no test client, no mocks) against whatever
--base-url points at: the docker-compose.ci.yml stack in CI, or the live
VPS after a deploy. Exits non-zero on any failure.
"""
import argparse
import io
import sys
import time
import uuid

import httpx


def step(name):
    def deco(fn):
        def wrapper(*args, **kwargs):
            print(f"-> {name}", flush=True)
            result = fn(*args, **kwargs)
            print(f"   ok", flush=True)
            return result
        return wrapper
    return deco


@step("wait for /api/health")
def wait_healthy(client: httpx.Client, timeout: int):
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            resp = client.get("/api/health")
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                return
        except httpx.HTTPError as e:
            last_err = e
        time.sleep(2)
    raise SystemExit(f"service never became healthy: {last_err}")


@step("signup + login")
def signup_and_login(client: httpx.Client) -> str:
    email = f"e2e-{uuid.uuid4().hex[:10]}@example.com"
    password = "E2ePassw0rd!"
    resp = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert resp.status_code in (200, 201), resp.text
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@step("upload book")
def upload_book(client: httpx.Client, token: str) -> str:
    files = {"file": ("book.txt", io.BytesIO(b"Once upon a time, an E2E test verified the whole stack."), "text/plain")}
    data = {
        "title": "E2E Test Book",
        "author": "CI Runner",
        "isbn": str(uuid.uuid4())[:13],
        "language": "en",
        "published_year": 2024,
        "tags": "e2e,ci",
    }
    resp = client.post(
        "/api/books", data=data, files=files, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


@step("wait for async summary to complete")
def wait_for_summary(client: httpx.Client, token: str, book_id: str, timeout: int):
    deadline = time.time() + timeout
    headers = {"Authorization": f"Bearer {token}"}
    last = None
    while time.time() < deadline:
        resp = client.get(f"/api/books/{book_id}/analysis", headers=headers)
        if resp.status_code == 200:
            last = resp.json()
            if last.get("summary_status") == "completed":
                assert last.get("summary"), "summary completed but empty"
                return last
            if last.get("summary_status") == "failed":
                raise SystemExit(f"summary task failed: {last}")
        time.sleep(2)
    raise SystemExit(f"summary never completed in time, last seen: {last}")


@step("borrow book")
def borrow(client: httpx.Client, token: str, book_id: str):
    resp = client.post(f"/api/books/{book_id}/borrow", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201), resp.text


@step("add review")
def add_review(client: httpx.Client, token: str, book_id: str):
    resp = client.post(
        f"/api/books/{book_id}/reviews",
        json={"rating": 5, "review_text": "Great E2E read"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text


@step("return book")
def return_book(client: httpx.Client, token: str, book_id: str):
    resp = client.post(f"/api/books/{book_id}/return", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text


@step("wait for review consensus to complete")
def wait_for_consensus(client: httpx.Client, token: str, book_id: str, timeout: int):
    deadline = time.time() + timeout
    headers = {"Authorization": f"Bearer {token}"}
    last = None
    while time.time() < deadline:
        resp = client.get(f"/api/books/{book_id}/analysis", headers=headers)
        if resp.status_code == 200:
            last = resp.json()
            if last.get("consensus_status") == "completed":
                assert last.get("consensus"), "consensus completed but empty"
                return last
            if last.get("consensus_status") == "failed":
                raise SystemExit(f"consensus task failed: {last}")
        time.sleep(2)
    raise SystemExit(f"consensus never completed in time, last seen: {last}")


@step("check /metrics")
def check_metrics(client: httpx.Client):
    resp = client.get("/metrics")
    assert resp.status_code == 200, resp.text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--health-timeout", type=int, default=120)
    parser.add_argument("--task-timeout", type=int, default=60)
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        wait_healthy(client, args.health_timeout)
        token = signup_and_login(client)
        book_id = upload_book(client, token)
        wait_for_summary(client, token, book_id, args.task_timeout)
        borrow(client, token, book_id)
        add_review(client, token, book_id)
        wait_for_consensus(client, token, book_id, args.task_timeout)
        return_book(client, token, book_id)
        check_metrics(client)

    print("\nE2E smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\nE2E smoke test FAILED: {e}", file=sys.stderr)
        sys.exit(1)
