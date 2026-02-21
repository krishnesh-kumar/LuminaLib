# LuminaLib System Architecture (FastAPI)

## 1. Purpose and Scope

LuminaLib is a content-aware library backend designed for production-style engineering:

1. JWT-secured APIs for signup, login, profile, and logout.
2. True book ingestion with real files (PDF and TXT), not metadata-only CRUD.
3. Asynchronous GenAI jobs:
   - Book summary generation after upload.
   - Rolling sentiment consensus after each review.
4. Borrow and return workflows with strict review eligibility rules.
5. Behavior-driven recommendations based on user preference modeling.
6. Config-driven provider swaps for storage and LLM.
7. One-command Docker startup for full stack.

Primary stack:

1. FastAPI
2. PostgreSQL
3. Celery + Redis
4. Ollama (or mock LLM provider)
5. MinIO (or local filesystem provider)

## 2. Architectural Principles

LuminaLib follows clean layering and dependency inversion:

API Routers -> Services -> Repositories -> Infrastructure Providers

Rules:

1. Routers only orchestrate request/response.
2. Business logic lives in services.
3. Repositories own database access.
4. External dependencies are abstracted behind provider interfaces.
5. Dependency injection is used for repositories/providers in service constructors.

## 3. Project Layout

**Layer roles**
- `api/` – FastAPI routers, dependencies, response mapping; no business logic.
- `schemas/` – Pydantic request/response DTOs for validation and shaping API I/O.
- `services/` – Use-cases: orchestrate repos/providers, enforce business rules, data isolation.
- `repositories/` – SQLAlchemy data access, per-aggregate query logic, no domain rules.
- `models/` – SQLAlchemy ORM models and metadata bound to Alembic migrations.
- `providers/` – Pluggable infra:
  - `storage/` MinIO/local implementations behind `StorageProvider`.
  - `llm/` Ollama-only `LLMProvider` (mistral) per requirements.
  - `recs/` Recommendation providers (content-based default).
- `workers/` – Celery tasks (LLM jobs, preferences, recommendations) and scheduling.
- `core/` – Settings, logging, DI wiring, auth/JWT utilities, error handling, Celery app, prompt loading.
- `migrations/` – Alembic environment and versioned migration scripts.
- `docker/` – Entry scripts or helpers for container runtime.

**Python file responsibilities (current state)**
- `app/main.py` – Application factory; wires logging, settings, root and health routes.
- `app/api/health.py` – `/health` endpoint for liveness checks.
- `app/core/config.py` – Centralized settings via `pydantic-settings`; env-driven configuration.
- `app/core/logging.py` – Basic logging configuration honoring `LOG_LEVEL`.
- `app/core/database.py` – SQLAlchemy engine/session setup and `Base` declarative registry.
- `app/core/celery_app.py` – Celery instance with broker/backend from settings and task routing.
- `app/core/security.py` – Password hashing, JWT encode/decode, refresh token hashing helpers.
- `app/api/deps.py` – Shared FastAPI dependencies (auth) including `get_current_user`.
- `app/providers/storage/base.py` – StorageProvider interface contract.
- `app/providers/storage/minio.py` – MinIO implementation with bucket bootstrap.
- `app/providers/storage/local.py` – Local filesystem implementation for dev.
- `app/providers/storage/__init__.py` – Provider factory based on `STORAGE_PROVIDER`.
- `app/providers/llm/base.py` – LLMProvider interface.
- `app/providers/llm/ollama.py` – Ollama client targeting mistral model.
- `app/providers/llm/__init__.py` – LLM provider factory (Ollama only per requirements).
- `app/providers/recs/base.py` – RecommendationProvider interface.
- `app/providers/recs/content_based.py` – Stub content-based recommender placeholder.
- `app/providers/recs/__init__.py` – Recommendation provider factory (content-based default).
- `app/services/book_service.py` – Book CRUD + file upload, storage integration, summary enqueue, re-summary on file replace.
- `app/repositories/book_repo.py` – Book, BookFile, and BookAISummary data access helpers.
- `app/schemas/books.py` – Pydantic schemas for book API I/O.
- `app/api/books.py` – Book endpoints (upload/list/update/delete) with auth guard.
- `app/workers/tasks.py` – Celery task stubs for summarize, review consensus, preferences, recommendations.
- `app/repositories/borrow_repo.py` – Borrow lookups and creation helpers with active-only queries.
- `app/services/borrow_service.py` – Borrow/return logic, constraint enforcement, recompute triggers.
- `app/schemas/borrows.py` – Borrow response schema.
- `app/api/borrows.py` – Borrow/return endpoints with auth guard.
- `app/repositories/review_repo.py` – Review persistence and queries.
- `app/services/review_service.py` – Review submission with borrow validation and consensus enqueue.
- `app/schemas/reviews.py` – Review create/output schemas.
- `app/api/reviews.py` – Review submission/listing endpoints.
- `app/repositories/book_summary_repo.py` – Read access to summary/consensus rows.
- `app/api/analysis.py` – Analysis endpoint combining summary and consensus.
- `app/repositories/tag_repo.py` – Tag CRUD helper and book-tag mapping.
- `app/repositories/recommendation_repo.py` – Recommendation snapshots, items, and preference reads.
- `app/providers/recs/base.py`, `app/providers/recs/content_based.py` – Content-based scorer using tag weights.
- `app/services/recommendation_service.py` – Synchronous recommendation computation.
- `app/api/recommendations.py` – Recommendations endpoint.
- `app/services/auth_service.py` – Auth business logic (signup, login, refresh, logout, token issuance).
- `app/repositories/user_repo.py` – User persistence (lookup/create).
- `app/repositories/refresh_token_repo.py` – Refresh token persistence and revocation.
- `app/api/auth.py` – Auth routes: signup, login, refresh, logout, profile.
- `app/api/__init__.py`, `app/workers/__init__.py` – Package markers.
- `alembic.ini` – Alembic configuration (script location, logging).
- `migrations/env.py` – Alembic environment hooking settings URL and metadata.
- `migrations/versions/0001_init.py` – Placeholder initial migration (to be filled in Phase 3).
- `Dockerfile` – API/worker image build; installs deps, runs entrypoint then uvicorn.
- `docker-compose.yml` – One-command stack (api, worker, beat, db, redis, minio, init, ollama + mistral pull helper).
- `docker/entrypoint.sh` – Runs Alembic upgrade then execs container CMD.
- `.env.example` – Sample environment for compose/local runs.
- `requirements.txt` – Python dependencies for the project.

## 4. Configuration

Runtime behavior is fully environment-driven:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | JWT signing key |
| `JWT_ALGORITHM` | JWT signing algorithm |
| `JWT_ACCESS_EXPIRES_MIN` | Access token expiry |
| `JWT_REFRESH_EXPIRES_DAYS` | Refresh token expiry |
| `STORAGE_PROVIDER` | `minio` or `local` |
| `STORAGE_BUCKET` | MinIO bucket name |
| `MINIO_ENDPOINT` | MinIO host and port |
| `MINIO_ACCESS_KEY` | MinIO access key |
| `MINIO_SECRET_KEY` | MinIO secret key |
| `LOCAL_STORAGE_PATH` | Local file base directory |
| `LLM_PROVIDER` | `ollama` or `mock` |
| `OLLAMA_BASE_URL` | Ollama API URL |
| `OLLAMA_MODEL` | Model name |
| `REDIS_URL` | Celery broker/result backend |
| `MAX_UPLOAD_MB` | Max file size |
| `ALLOWED_FILE_TYPES` | Allowed mime/types (`pdf`, `txt`) |

## 5. Data Model (ER-aligned)

Core tables:

1. `users`
2. `refresh_tokens`
3. `books`
4. `book_files`
5. `book_ai_summaries`
6. `book_review_consensus`
7. `borrows`
8. `reviews`
9. `tags`
10. `book_tags`
11. `user_tag_preferences`
12. `recommendation_snapshots`
13. `recommendation_items`

Key constraints:

1. One active borrow per book:
   - partial unique index on `borrows(book_id)` where `returned_at IS NULL`.
2. One active borrow per user:
   - partial unique index on `borrows(user_id)` where `returned_at IS NULL`.
3. One review per user-book pair:
   - unique (`user_id`, `book_id`) on `reviews`.
4. One file record per book:
   - unique (`book_id`) on `book_files`.
5. One current AI summary per book:
   - unique (`book_id`) on `book_ai_summaries`.
6. One current review-consensus per book:
   - unique (`book_id`) on `book_review_consensus`.

## 6. File Ingestion Design (PDF and TXT)

Upload flow (`POST /books`):

1. Validate content type and size.
2. Store binary via `StorageProvider`.
3. Save `books` + `book_files` record:
   - `file_type` enum (`pdf`, `txt`)
   - `mime_type`
   - `object_key`
   - `original_filename`
4. Enqueue `summarize_book(book_id)` task.
5. Return 201 immediately.

Idempotency:

1. The summarization task is a no-op if a successful summary already exists for the
   current `prompt_version` and `model_name`.
2. Re-summarization only happens when:
   - the book content changes (file replacement), or
   - the previous job failed and needs retry/backfill.

Text extraction strategy:

1. TXT:
   - decode bytes (utf-8 with fallback strategy).
   - normalize whitespace.
2. PDF:
   - parse pages using a PDF extractor in worker context.
   - concatenate page text.
3. Apply truncation/chunking before LLM call based on token budget.

## 7. API Contract

Required endpoints:

1. `POST /auth/signup`
2. `POST /auth/login`
3. `GET /auth/profile`
4. `POST /auth/logout`
5. `POST /books`
6. `GET /books` (pagination required)
7. `PUT /books/{id}`
8. `DELETE /books/{id}`
9. `POST /books/{id}/borrow`
10. `POST /books/{id}/return`
11. `POST /books/{id}/reviews`
12. `GET /books/{id}/analysis`
13. `GET /recommendations`

Router responsibilities:

1. Input validation (Pydantic models).
2. Auth dependency enforcement.
3. Mapping service exceptions to standardized API errors.

## 8. Authentication and Security

1. Password hashing: `passlib` bcrypt.
2. JWT access and refresh tokens.
3. Refresh token persistence in `refresh_tokens` (hashed token or jti).
4. Logout invalidates refresh token records.
5. Protected endpoints enforced with FastAPI auth dependency.
6. No plaintext secrets or credentials in code.

## 9. Async Processing Model

Celery tasks:

1. `summarize_book(book_id)`:
   - load file from storage
   - extract text (pdf/txt aware)
   - generate summary with `LLMProvider` only if missing (idempotent)
   - store status/result in `book_ai_summaries` (single current row per book)
2. `update_review_consensus(book_id)`:
   - aggregate reviews
   - generate consensus text with `LLMProvider`
   - store in `book_review_consensus` (single current row per book)
3. `recompute_user_preferences(user_id)`:
   - rebuild tag weights from borrow history
4. `recompute_recommendations(user_id)`:
   - score candidates
   - persist ranked snapshot

Operational behaviors:

1. API never waits for LLM response.
2. Tasks are idempotent.
3. Retries use exponential backoff.
4. Task failures are stored with error details for observability.

## 10. Recommendation Strategy

Baseline model: content-based scoring using tags + borrow history.

1. Build user preference vector from historical borrows (`user_tag_preferences`).
2. Score books by tag overlap/weights.
3. Exclude already borrowed books.
4. Persist top N in snapshot tables for deterministic reads.

This meets assignment expectations for non-random, behavior-based recommendations and is easy to evolve later (collaborative or hybrid models).

## 11. Observability and Error Handling

1. Structured JSON logs with request_id and user_id context.
2. Standardized error response schema across routers.
3. Global exception handlers in `app/core/errors.py`.
4. Request validation with clear field-level errors.
5. Metrics hooks for queue depth, task success/failure, and latency.

## 12. Prompt Management

1. Prompts live in the repository filesystem (example: `app/core/prompts/`).
2. Each prompt has a stable version identifier (filename or embedded version string).
3. Workers load prompt templates from disk and record `prompt_version` in DB outputs
   (`book_ai_summaries`, `book_review_consensus`) for auditability.

## 13. Deployment

`docker-compose.yml` should start:

1. `api` (FastAPI)
2. `db` (PostgreSQL)
3. `redis`
4. `worker` (Celery worker)
5. `beat` (Celery scheduler)
6. `ollama` (or mock LLM container)
7. `minio` (or local storage fallback)

Running `docker-compose up --build` must bring up a working end-to-end stack without manual host setup.

## 14. Testing Strategy

1. Unit tests for routers, services, repositories, providers, and workers.
2. Integration tests for:
   - auth lifecycle
   - book upload (pdf/txt)
   - borrow/review constraints
   - async summary and sentiment flow
   - recommendations endpoint
3. Contract tests for provider interchangeability (storage/LLM swap).

## 15. Run/Resume Checklist

1. `cp .env.example .env` (adjust as needed).
2. `docker compose down && docker compose build --no-cache api worker beat && docker compose up -d`.
3. `docker compose exec api alembic upgrade head` (if migrations not already applied).
4. Health: `curl http://localhost:8000/api/health`.
5. Watch workers: `docker compose logs worker -f`.
6. For summaries/consensus issues, check `book_ai_summaries` / `book_review_consensus` status and `error_message`, and worker logs.

## 16. Diagram References
- For step-by-step validation and curls, see `VALIDATION.md`.

## 17. Reliability & Observability Notes
- Celery tasks use autoretry with exponential backoff (max 3 retries) for summaries, consensus, and recomputation.
- Task status/error_message persisted in `book_ai_summaries` and `book_review_consensus` for post-mortem checks.
- Worker queues: `llm`, `recs`, `celery`; ensure worker command includes all.
- Logs: `docker compose logs worker -f` for task outcomes; API logs surface HTTP errors.

ER and high-level block architecture diagrams are maintained in:

`/Users/krishneshkumar/Desktop/LuminaLib/SYSTEM_DIAGRAMS.md`
