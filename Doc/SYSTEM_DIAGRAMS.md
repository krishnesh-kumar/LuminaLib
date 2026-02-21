# LuminaLib Diagrams

## 1) ER Diagram

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : has
    USERS ||--o{ BORROWS : makes
    USERS ||--o{ REVIEWS : writes
    USERS ||--o{ USER_TAG_PREFERENCES : has
    USERS ||--o{ RECOMMENDATION_SNAPSHOTS : owns

    BOOKS ||--|| BOOK_FILES : stores
    BOOKS ||--o{ BORROWS : borrowed_in
    BOOKS ||--o{ REVIEWS : reviewed_in
    BOOKS ||--o{ BOOK_TAGS : tagged_with
    BOOKS ||--o| BOOK_AI_SUMMARIES : summarized_by
    BOOKS ||--o| BOOK_REVIEW_CONSENSUS : analyzed_by
    BOOKS ||--o{ RECOMMENDATION_ITEMS : recommended_as

    TAGS ||--o{ BOOK_TAGS : maps
    TAGS ||--o{ USER_TAG_PREFERENCES : weights

    RECOMMENDATION_SNAPSHOTS ||--o{ RECOMMENDATION_ITEMS : contains

    USERS {
        uuid id PK
        string email UK
        string password_hash
        datetime created_at
        datetime updated_at
    }
    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        string token_hash
        datetime expires_at
        datetime revoked_at
    }
    BOOKS {
        uuid id PK
        string title
        string author
        string isbn
        string language
        int published_year
        datetime created_at
    }
    BOOK_FILES {
        uuid id PK
        uuid book_id FK
        string object_key
        string storage_provider
        string file_type
        string mime_type
        string original_filename
        int size_bytes
    }
    BOOK_AI_SUMMARIES {
        uuid id PK
        uuid book_id FK
        string status
        string model_name
        string prompt_version
        text summary
        text error_message
        datetime updated_at
    }
    BOOK_REVIEW_CONSENSUS {
        uuid id PK
        uuid book_id FK
        string status
        string model_name
        string prompt_version
        text consensus
        text error_message
        datetime updated_at
    }
    BORROWS {
        uuid id PK
        uuid user_id FK
        uuid book_id FK
        datetime borrowed_at
        datetime due_at
        datetime returned_at
    }
    REVIEWS {
        uuid id PK
        uuid user_id FK
        uuid book_id FK
        int rating
        text review_text
        datetime created_at
    }
    TAGS {
        uuid id PK
        string name UK
    }
    BOOK_TAGS {
        uuid book_id FK
        uuid tag_id FK
    }
    USER_TAG_PREFERENCES {
        uuid user_id FK
        uuid tag_id FK
        float weight
        datetime updated_at
    }
    RECOMMENDATION_SNAPSHOTS {
        uuid id PK
        uuid user_id FK
        datetime generated_at
    }
    RECOMMENDATION_ITEMS {
        uuid id PK
        uuid snapshot_id FK
        uuid book_id FK
        float score
        int rank
    }
```

## 2) High-Level Architecture (Block Line Diagram)

```mermaid
flowchart LR
    Client["Client Apps"] --> API["FastAPI API Layer"]

    subgraph Core["Application Core"]
        API --> Services["Service Layer"]
        Services --> Repos["Repository Layer"]
        Services --> Storage["StorageProvider"]
        Services --> LLM["LLMProvider"]
    end

    Repos --> DB["PostgreSQL"]
    Storage --> Minio["MinIO or Local Storage"]

    API --> Queue["Redis Queue"]
    Queue --> Worker["Celery Worker"]
    Worker --> Storage
    Worker --> LLM
    Worker --> Repos
    Beat["Celery Beat"] --> Worker

    LLM --> Ollama["Ollama or Mock LLM"]
```

## 3) Async Event Flow (Reference)

```mermaid
flowchart TD
    A["POST /books (pdf or txt)"] --> B["Store file metadata and object key"]
    B --> C["Enqueue summarize_book"]
    C --> D["Worker extracts text"]
    D --> E["Worker calls LLM provider"]
    E --> F["Persist summary status and content"]

    G["POST /books/{id}/reviews"] --> H["Validate user borrowed book"]
    H --> I["Save review"]
    I --> J["Enqueue update_review_consensus"]
    J --> K["Worker aggregates reviews and calls LLM"]
    K --> L["Persist consensus"]
```

## 4) Endpoint -> Tables Touched

| Endpoint | Reads | Writes/Updates |
|---|---|---|
| `POST /auth/signup` | - | `USERS` |
| `POST /auth/login` | `USERS` | `REFRESH_TOKENS` |
| `GET /auth/profile` | `USERS` | - |
| `POST /auth/logout` | `REFRESH_TOKENS` | `REFRESH_TOKENS` (revoke) |
| `POST /books` | - | `BOOKS`, `BOOK_FILES` |
| `GET /books` | `BOOKS`, `BOOK_FILES` | - |
| `PUT /books/{id}` | `BOOKS`, `BOOK_FILES` | `BOOKS` (metadata), optionally `BOOK_FILES` (file replace) |
| `DELETE /books/{id}` | `BOOKS`, `BOOK_FILES` | `BOOKS` + dependent rows (file/text/ai/tags) |
| `POST /books/{id}/borrow` | `BOOKS`, `BORROWS` | `BORROWS` |
| `POST /books/{id}/return` | `BORROWS` | `BORROWS` (returned_at) |
| `POST /books/{id}/reviews` | `BORROWS` | `REVIEWS` |
| `GET /books/{id}/analysis` | `BOOK_REVIEW_CONSENSUS`, `BOOK_AI_SUMMARIES` | - |
| `GET /recommendations` | `RECOMMENDATION_SNAPSHOTS`, `RECOMMENDATION_ITEMS`, `BOOKS` | - |

Worker tasks (triggered asynchronously):

| Task | Reads | Writes/Updates |
|---|---|---|
| `summarize_book(book_id)` | `BOOK_FILES` + storage bytes | `BOOK_AI_SUMMARIES` |
| `update_review_consensus(book_id)` | `REVIEWS` | `BOOK_REVIEW_CONSENSUS` |
| `recompute_user_preferences(user_id)` | `BORROWS`, `BOOK_TAGS` | `USER_TAG_PREFERENCES` |
| `recompute_recommendations(user_id)` | `USER_TAG_PREFERENCES`, `BOOK_TAGS`, `BORROWS` | `RECOMMENDATION_SNAPSHOTS`, `RECOMMENDATION_ITEMS` |
