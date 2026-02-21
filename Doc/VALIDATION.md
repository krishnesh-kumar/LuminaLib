# LuminaLib Validation Checklist (API, Async, Docker)

## Prereqs
1) `cp .env.example .env` (adjust if needed).
2) `docker compose down && docker compose build --no-cache api worker beat && docker compose up -d`
3) Apply migrations: `docker compose exec api alembic upgrade head`
4) Ensure mistral is pulled: `docker compose logs ollama-pull`

## Smoke (Health)
- `curl http://localhost:8000/api/health` -> `{"status":"ok"}`

## Auth
- Signup: POST `/api/auth/signup` with JSON email/password -> 201 user.
- Login: POST `/api/auth/login` form data -> tokens returned.
- Profile with access token -> returns user.
- Refresh with refresh token -> new token pair.
- Logout with refresh token -> 204; subsequent refresh with same token -> 401.

## Books (upload triggers summary + validation)
- Upload PDF/TXT:
```
curl -X POST http://localhost:8000/api/books \
  -H "Authorization: Bearer <ACCESS>" \
  -F "file=@/path/book.pdf" \
  -F "title=Demo" -F "author=Author" \
  -F "tags=scifi,space"
```
-> 201 with book metadata.
- Invalid MIME (e.g., png) -> 400.
- Oversize (>MAX_UPLOAD_MB) -> 413.
- List books -> shows uploaded book.
- Update with new file or tags -> 200; summary re-enqueued.
- Duplicate ISBN on create/update -> 400.
- Summary status: `select status,summary,error_message from book_ai_summaries;` should become `completed` with summary text.
- Download file:
  `curl -H "Authorization: Bearer <ACCESS>" http://localhost:8000/api/books/<BOOK_ID>/file -OJ`
  - 404 when file missing.

## Borrow/Return Constraints
- Borrow: `POST /api/books/{book_id}/borrow` -> 201.
- Borrow same book by another user -> 400.
- Borrow second book by same user while first active -> 400.
- Return: `POST /api/books/{book_id}/return` -> 200 with returned_at.
- Return when no active borrow -> 404.

## Reviews & Analysis
- Add review (after borrow): `POST /api/books/{book_id}/reviews` with rating/review_text -> 201.
- Second review by same user/book -> 400.
- Non-borrower review -> 400.
- Analysis: `GET /api/books/{book_id}/analysis` -> summary_* and consensus_* fields; consensus updates after review task runs.
- Review consensus status: `select status,consensus,error_message from book_review_consensus;` should be `completed`.

## Recommendations
- Ensure at least two tagged books; borrow one to seed preferences.
- `GET /api/recommendations` -> returns ranked items excluding borrowed books. Empty list means insufficient signal (no tags or no borrow history).
- If empty, message should explain: "No recommendations yet. Add tags to books and borrow to build signal."
- With `RECS_PROVIDER=ml_als` (default) the ML recommender should return the un-borrowed tagged book; with `RECS_PROVIDER=content` it uses tag-based only.

## Metrics
- API: `GET /metrics` (Prometheus format) for health/usage scraping.
- Celery counters exposed via same endpoint (task_success, task_failure, task_retry).

## Async/Workers
- Worker logs: `docker compose logs worker -f` shows tasks `summarize_book`, `update_review_consensus`, `recompute_user_preferences`, `recompute_recommendations`.
- Queues: worker command includes `-Q llm,recs,celery`.
- Error handling: failed tasks set `status="failed"` with `error_message` in respective tables.
- Task retries: Celery autoretry (max 3) with backoff for all LLM/prefs/recs tasks.

## Storage/MinIO
- MinIO bucket `luminalib` exists (created by minio-mc). Upload/download via providers is implicit in book upload/summary tasks.

## Postgres/Ports
- DB mapped to host 5433. Connection: `postgresql://postgres:postgres@localhost:5433/luminalib`.

## Metrics
- API: `GET /metrics` (Prometheus format) for health/usage scraping.

## Recap for reruns
- Rebuild after dependency/code changes.
- Run migrations after model changes.
- Verify Ollama and worker are healthy before testing summaries/consensus.
