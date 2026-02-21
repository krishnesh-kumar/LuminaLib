# API & Service Design (LuminaLib)

This doc gives endpoint-by-endpoint intent, data flow, and visuals so we can resume quickly.

## Legend for Diagrams
- Rectangles = components, Cylinders = DB, Parallelograms = storage, Hexagon = Celery worker, Cloud = Ollama.

---

## Auth
**Endpoints**  
- `POST /api/auth/signup` – create user, returns 201/400.  
- `POST /api/auth/login` – form login, returns access+refresh tokens.  
- `POST /api/auth/refresh` – rotates refresh (revokes old, issues new).  
- `POST /api/auth/logout` – revokes all refresh tokens for the user.  
- `GET /api/auth/profile` – returns current user (access token required).

**Flow (login/refresh/logout)**  
```mermaid
flowchart LR
  subgraph API
    A[login] --> B[AuthService]
    C[refresh] --> B
    D[logout] --> B
  end
  B -->|verify pwd / decode| U[(users)]
  B -->|store hash| R[(refresh_tokens)]
  B -->|issue JWTs| T[client]
  D -->|delete all refresh| R
```

---

## Books (Upload + Download)
**Endpoints**  
- `POST /api/books` (multipart) – create book, store file, enqueue summary.  
- `GET /api/books` – list (with file meta & tags).  
- `PUT /api/books/{id}` – update fields, optional file replace (re-summary).  
- `DELETE /api/books/{id}` – delete book.  
- `GET /api/books/{id}/file` – download stored file (auth, 404 if missing).

**Validation**  
- MIME allowlist: pdf|txt.  
- Size cap: `MAX_UPLOAD_MB` → 413 if exceeded.  
- Duplicate ISBN → 400.

**Flow (upload & summary enqueue)**  
```mermaid
flowchart LR
  U[User] -->|multipart| API[Books API]
  API -->|put file| STO[(Storage)]
  API -->|insert book + file| DB[(Postgres)]
  API -->|enqueue summary| CEL[[Celery]]
  CEL -->|fetch file| STO
  CEL -->|LLM prompt| OLL[[Ollama]]
  CEL -->|write summary| DB
```

**Flow (download)**  
```mermaid
flowchart LR
  U[User] -->|GET /books/:id/file| API[Books API]
  API -->|lookup file row| DB[(Postgres)]
  API -->|stream object| STO[(Storage)]
  API --> U
```

---

## Borrow / Return
**Endpoints**  
- `POST /api/books/{id}/borrow` – one active borrow per user & per book.  
- `POST /api/books/{id}/return` – sets `returned_at`, 404 if not active.

**Flow**  
```mermaid
flowchart LR
  U --> API
  API -->|constraints| DB[(borrows partial unique idx)]
  API -->|send recompute prefs/recs| CEL[Celery]
  CEL --> DB
```

---

## Reviews & Analysis
**Endpoints**  
- `POST /api/books/{id}/reviews` – only borrowers can review; 1/user/book.  
- `GET /api/books/{id}/reviews` – list.  
- `GET /api/books/{id}/analysis` – returns summary + review consensus (if ready), 404 if neither exists.

**Flow (review -> consensus)**  
```mermaid
flowchart LR
  U --> API
  API --> DB[(reviews)]
  API -->|send_task update_review_consensus| CEL[Celery]
  CEL --> DB
  CEL -->|LLM prompt| OLL[Ollama]
```

---

## Recommendations (Content-Based)
**Endpoint**  
- `GET /api/recommendations`

**Scoring Logic**  
- Tags on books (comma-separated).  
- User preference weight per tag = count of borrows of books with that tag.  
- Score(book) = sum of user tag weights across that book’s tags.  
- Exclude already-borrowed books.  
- If no tags/borrows → empty list + hint.

**Flow**  
```mermaid
flowchart LR
  U[User] -->|GET /recommendations| API[Recs API]
  API -->|compute prefs| DB[(prefs, borrows, book_tags)]
  API -->|rank books| PROVIDER[ContentBased]
  PROVIDER --> API
  API -->|snapshot items| DB
  API --> U
```

---

## Metrics & Logging
- Endpoint: `GET /metrics` (Prometheus).  
- Counters: Celery task success/failure/retry.  
- Logging: JSON (python-json-logger) in API & worker.

---

## Testing Guide (summary)
- Stack running: `docker compose exec api pytest -q`  
- Host: `pytest -q` (needs DB/Redis env).  
- Coverage: auth rotation/logout, upload validation, download, borrow/return, recommendations “no signal”, health. See `tests/test_features.py`.

---

## Storage Providers
- MinIO (default) or local (dev/tests). Both support streaming `get_stream` used by download endpoint.
