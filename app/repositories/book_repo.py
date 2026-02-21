from typing import Optional, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Book, BookFile, BookAISummary


class BookRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_isbn(self, isbn: str) -> Optional[Book]:
        stmt = select(Book).where(Book.isbn == isbn)
        return self.db.scalar(stmt)

    def create(self, **kwargs) -> Book:
        book = Book(**kwargs)
        self.db.add(book)
        self.db.flush()
        return book

    def list(self, offset: int = 0, limit: int = 20) -> Sequence[Book]:
        stmt = select(Book).offset(offset).limit(limit)
        return list(self.db.scalars(stmt))

    def get(self, book_id: str) -> Optional[Book]:
        return self.db.get(Book, book_id)

    def delete(self, book: Book):
        self.db.delete(book)

    def update(self, book: Book, **kwargs) -> Book:
        for k, v in kwargs.items():
            if v is not None:
                setattr(book, k, v)
        self.db.flush()
        return book


class BookFileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_book(self, book_id: str) -> Optional[BookFile]:
        stmt = select(BookFile).where(BookFile.book_id == book_id)
        return self.db.scalar(stmt)

    def upsert(self, book_id: str, **kwargs) -> BookFile:
        existing = self.db.execute(select(BookFile).where(BookFile.book_id == book_id)).scalar_one_or_none()
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            self.db.flush()
            return existing
        bf = BookFile(book_id=book_id, **kwargs)
        self.db.add(bf)
        self.db.flush()
        return bf


class BookSummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_pending(self, book_id: str, model_name: str, prompt_version: str) -> BookAISummary:
        existing = (
            self.db.execute(select(BookAISummary).where(BookAISummary.book_id == book_id))
            .scalar_one_or_none()
        )
        if existing:
            return existing
        summary = BookAISummary(
            book_id=book_id,
            status="pending",
            model_name=model_name,
            prompt_version=prompt_version,
        )
        self.db.add(summary)
        self.db.flush()
        return summary
