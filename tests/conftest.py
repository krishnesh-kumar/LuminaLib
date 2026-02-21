import pytest
from sqlalchemy import text
from app.core.database import SessionLocal


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure each test runs with a clean database state."""
    with SessionLocal() as db:
        # order matters because of FKs
        db.execute(text("TRUNCATE recommendation_items RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE recommendation_snapshots RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE user_tag_preferences RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE book_tags RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE tags RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE reviews RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE borrows RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE book_ai_summaries RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE book_review_consensus RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE book_files RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE books RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE refresh_tokens RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
        db.commit()
    yield
