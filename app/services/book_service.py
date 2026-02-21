import os
from typing import Optional, Tuple
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.repositories.book_repo import BookRepository, BookFileRepository, BookSummaryRepository
from app.repositories.tag_repo import TagRepository
from app.providers.storage import get_storage_provider
from app.core.config import settings
from app.core.celery_app import celery_app


class BookService:
    def __init__(self, db: Session):
        self.db = db
        self.books = BookRepository(db)
        self.book_files = BookFileRepository(db)
        self.book_summaries = BookSummaryRepository(db)
        self.storage = get_storage_provider()
        self.tags = TagRepository(db)

    def create_book(
        self,
        file: UploadFile,
        title: str,
        author: str,
        isbn: Optional[str],
        language: Optional[str],
        published_year: Optional[int],
        tags: Optional[str],
    ):
        file_type = (file.content_type or "").split("/")[-1]
        if file_type == "plain":
            file_type = "txt"
        if file_type not in {"pdf", "txt"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
        size = self._file_size(file)
        if size is not None and size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

        if isbn:
            existing = self.books.get_by_isbn(isbn)
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN already exists")

        book = self.books.create(
            title=title,
            author=author,
            isbn=isbn,
            language=language,
            published_year=published_year,
        )
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            if tag_list:
                self.tags.set_book_tags(str(book.id), tag_list)

        object_key = f"{book.id}/{file.filename or 'upload'}"
        stored_key = self.storage.put(file.file, object_key)
        self.book_files.upsert(
            book_id=str(book.id),
            storage_provider=settings.STORAGE_PROVIDER,
            object_key=stored_key,
            file_type=file_type,
            mime_type=file.content_type,
            original_filename=file.filename,
            size_bytes=self._file_size(file),
        )

        self.book_summaries.ensure_pending(book_id=str(book.id), model_name=settings.OLLAMA_MODEL, prompt_version="v1")
        self._enqueue_summary(book_id=str(book.id))
        self._flush_or_raise_conflict()
        self.db.refresh(book)
        return self._hydrate(book)

    def list_books(self, offset: int = 0, limit: int = 20):
        books = self.books.list(offset=offset, limit=limit)
        return [self._hydrate(b) for b in books]

    def update_book(
        self,
        book_id: str,
        title: Optional[str],
        author: Optional[str],
        isbn: Optional[str],
        language: Optional[str],
        published_year: Optional[int],
        file: Optional[UploadFile],
        tags: Optional[str],
    ):
        book = self.books.get(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        if isbn and isbn != book.isbn:
            conflict = self.books.get_by_isbn(isbn)
            if conflict:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN already exists")
        self.books.update(
            book,
            title=title,
            author=author,
            isbn=isbn,
            language=language,
            published_year=published_year,
        )
        if file:
            file_type = (file.content_type or "").split("/")[-1]
            if file_type == "plain":
                file_type = "txt"
            if file_type not in {"pdf", "txt"}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
            size = self._file_size(file)
            if size is not None and size > settings.MAX_UPLOAD_MB * 1024 * 1024:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
            object_key = f"{book.id}/{file.filename or 'upload'}"
            stored_key = self.storage.put(file.file, object_key)
            self.book_files.upsert(
                book_id=str(book.id),
                storage_provider=settings.STORAGE_PROVIDER,
                object_key=stored_key,
                file_type=file_type,
                mime_type=file.content_type,
                original_filename=file.filename,
                size_bytes=self._file_size(file),
            )
            # re-run summary on content change
            self.book_summaries.ensure_pending(book_id=str(book.id), model_name=settings.OLLAMA_MODEL, prompt_version="v1")
            self._enqueue_summary(book_id=str(book.id))
        if tags is not None:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            self.tags.set_book_tags(str(book.id), tag_list)
        self._flush_or_raise_conflict()
        self.db.refresh(book)
        return self._hydrate(book)

    def delete_book(self, book_id: str):
        book = self.books.get(book_id)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        # Best-effort delete file
        # Note: we don't hard fail if storage delete fails
        # Could be enhanced with file lookup and delete
        self.books.delete(book)
        return

    def _enqueue_summary(self, book_id: str):
        celery_app.send_task("app.workers.tasks.summarize_book", args=[book_id])

    @staticmethod
    def _file_size(upload: UploadFile) -> Optional[int]:
        try:
            pos = upload.file.tell()
            upload.file.seek(0, os.SEEK_END)
            size = upload.file.tell()
            upload.file.seek(pos)
            return size
        except Exception:
            return None

    def _flush_or_raise_conflict(self):
        try:
            self.db.flush()
        except IntegrityError as e:
            self.db.rollback()
            # Handle ISBN uniqueness conflict gracefully
            if "ix_books_isbn" in str(e.orig) or "isbn" in str(e.orig):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ISBN already exists",
                )
            raise

    def _hydrate(self, book):
        # attach file and tags for response models
        bf = self.book_files.get_by_book(str(book.id))
        if bf:
            setattr(book, "file", bf)
        tag_objs = self.tags.get_tags_for_book(str(book.id))
        setattr(book, "tags", [t.name for t in tag_objs])
        return book
