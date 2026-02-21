# LuminaLib Backend (FastAPI, Celery, Ollama)

## What’s Here
- FastAPI API with JWT auth, book upload (PDF/TXT), borrow/return, async summaries and review consensus (Ollama mistral), and ML-ready recommendation hooks.
- Celery workers for summaries/consensus/prefs/recs.
- Docker-compose stack: api, worker, beat, Postgres 17, Redis, MinIO, Ollama (mistral), mc bucket init.

## Quick Start / Resume Checklist
1) `.env contains your environment variables`
2) `docker compose down && docker compose build --no-cache api worker beat && docker compose up -d`
3) Apply migrations (if not auto-run): `docker compose exec api alembic upgrade head`
4) Health: `curl http://localhost:8000/api/health` -> `{"status":"ok"}`
5) Metrics: `curl http://localhost:8000/metrics` (Prometheus format)
6) Watch workers/logs (JSON): `docker compose logs worker -f`

## Auth Flow (JWT)
- Signup:
  ```
  curl -X POST http://localhost:8000/api/auth/signup \
    -H "Content-Type: application/json" \
    -d '{"email":"u1@example.com","password":"Passw0rd!"}'
  ```
- Login (form data):
  ```
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=u1@example.com&password=Passw0rd!"
  ```
  Save `access_token`, `refresh_token`.
- Profile:
  `curl -H "Authorization: Bearer <ACCESS>" http://localhost:8000/api/auth/profile`
- Refresh:
  ```
  curl -X POST http://localhost:8000/api/auth/refresh \
    -H "Content-Type: application/json" \
    -d '{"refresh_token":"<REFRESH>"}'
  ```
- Logout (revokes refresh; access expires by time):
  ```
  curl -X POST http://localhost:8000/api/auth/logout \
    -H "Content-Type: application/json" \
    -d '{"refresh_token":"<REFRESH>"}'
  ```

## Books (Upload PDF/TXT, triggers async summary)
```
curl -X POST http://localhost:8000/api/books \
  -H "Authorization: Bearer <ACCESS>" \
  -H "Accept: application/json" \
  -F "file=@/absolute/path/to/book.pdf" \
  -F "title=Demo Title" \
  -F "author=Demo Author" \
  -F "isbn=1234567890" \
  -F "language=en" \
  -F "published_year=2024" \
  -F "tags=scifi,space"
```
- List: `curl -H "Authorization: Bearer <ACCESS>" http://localhost:8000/api/books`
- Update (optional file replace → re-summary): `PUT /api/books/{book_id}` with multipart fields.
- Delete: `DELETE /api/books/{book_id}`
- Summary result: check `book_ai_summaries` table; worker logs show `summarize_book`.
- Download stored file:  
  `curl -H "Authorization: Bearer <ACCESS>" http://localhost:8000/api/books/<BOOK_ID>/file -OJ`
- Upload validation: only `pdf|txt` allowed; `MAX_UPLOAD_MB` enforced (413 on too large, 400 on bad mime).

## Borrow / Return (constraints enforced)
- Borrow: `POST /api/books/{book_id}/borrow`
  ```
  curl -X POST http://localhost:8000/api/books/<BOOK_ID>/borrow \
    -H "Authorization: Bearer <ACCESS>"
  ```
- Return: `POST /api/books/{book_id}/return`
  ```
  curl -X POST http://localhost:8000/api/books/<BOOK_ID>/return \
    -H "Authorization: Bearer <ACCESS>"
  ```
Errors:
- Book already borrowed -> 400
- User already has active borrow -> 400
- Returning without active borrow -> 404

## Reviews & Analysis
- Add review (must have borrowed the book at least once; only one review per user/book):
  ```
  curl -X POST http://localhost:8000/api/books/<BOOK_ID>/reviews \
    -H "Authorization: Bearer <ACCESS>" \
    -H "Content-Type: application/json" \
    -d '{"rating":5,"review_text":"Great read"}'
  ```
- List reviews for a book:
  `curl -H "Authorization: Bearer <ACCESS>" http://localhost:8000/api/books/<BOOK_ID>/reviews`
- Analysis (summary + consensus):
  `curl -H "Authorization: Bearer <ACCESS>" http://localhost:8000/api/books/<BOOK_ID>/analysis`
  - `summary_*` fields come from the upload summary task.
  - `consensus_*` fields update after a review is submitted (async).

## Async Jobs
- Queues: `llm` (summaries/consensus), `recs` (prefs/recs).
- Worker command: `celery -A app.core.celery_app worker --loglevel=info -Q llm,recs,celery`
- Logs: `docker compose logs worker -f`
- Prompts: `app/core/prompts/summary.txt`, `app/core/prompts/review_consensus.txt`

## Recommendations (content-based)
- Endpoint: `GET /api/recommendations`
- How it works:
  - Tags are attached to books via `tags` on create/update (comma-separated), e.g. `-F "tags=scifi,space"`.
  - Each borrow increments the user’s weight for that book’s tags.
  - Score = sum of the user’s tag weights per candidate book; already borrowed books excluded.
  - Endpoint recomputes synchronously and stores a snapshot; background recompute also runs on borrow/return.
  - If no signal yet, returns `items: []` with a hint message.
- Visual & deeper design: see `API_DESIGN.md#recommendations`.

## Recommendations (ML ALS optional)
- Provider controlled by `RECS_PROVIDER` (default `ml_als`, set `content` to keep legacy only).
- ML path uses implicit ALS (64 factors, 10 iters, alpha=40) over borrows + review ratings.
- Cold start falls back to content-based. Borrowed books are always excluded.

## Validation Shortcut
- See `VALIDATION.md` for end-to-end test commands and expected outcomes (auth, upload validation, download, borrow/return, reviews/consensus, recommendations, metrics).
- Detailed API design and flows (with visuals): `API_DESIGN.md`.

## Testing
- With Docker stack up: `docker compose exec api pytest -q`
- Host (uses local env/DB): `pytest -q`
- Tests live in `/Users/krishneshkumar/Desktop/LuminaLib/tests` and cover auth rotation/logout, upload validation, download, borrow/return constraints, recommendations “no signal” messaging, and health.

## API Reference
- See `OPENAPI_SPEC.md` for endpoint-by-endpoint shapes, auth rules, and error cases.

## Metrics & Logging
- Prometheus endpoint: `GET /metrics` (API).
- Celery emits task success/failure/retry counters via Prometheus client.
- JSON-formatted logs for API and worker (python-json-logger).

## LLM Provider
- Fixed to Ollama mistral. Compose auto-pulls via `ollama-pull`.
- Endpoint assumed at `http://ollama:11434`.

## Storage
- MinIO by default (bucket `luminalib` auto-created). Files stored under `<book_id>/filename`.
