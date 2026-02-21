from typing import Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Borrow


class BorrowRepository:
    def __init__(self, db: Session):
        self.db = db

    def _uuid(self, val):
        if isinstance(val, uuid.UUID):
            return val
        return uuid.UUID(str(val))

    def create(self, user_id: str, book_id: str):
        borrow = Borrow(user_id=self._uuid(user_id), book_id=self._uuid(book_id))
        self.db.add(borrow)
        self.db.flush()
        return borrow

    def get_active_by_book(self, book_id: str) -> Optional[Borrow]:
        stmt = select(Borrow).where(Borrow.book_id == self._uuid(book_id), Borrow.returned_at.is_(None))
        return self.db.scalar(stmt)

    def get_active_by_user(self, user_id: str) -> Optional[Borrow]:
        stmt = select(Borrow).where(Borrow.user_id == self._uuid(user_id), Borrow.returned_at.is_(None))
        return self.db.scalar(stmt)

    def get_by_user_and_book(self, user_id: str, book_id: str) -> Optional[Borrow]:
        stmt = select(Borrow).where(
            Borrow.user_id == self._uuid(user_id),
            Borrow.book_id == self._uuid(book_id),
            Borrow.returned_at.is_(None),
        )
        return self.db.scalar(stmt)

    def get_by_user_and_book_any(self, user_id: str, book_id: str) -> Optional[Borrow]:
        stmt = select(Borrow).where(Borrow.user_id == self._uuid(user_id), Borrow.book_id == self._uuid(book_id))
        return self.db.scalar(stmt)

    def get_active_by_user_and_book(self, user_id: str, book_id: str) -> Optional[Borrow]:
        stmt = select(Borrow).where(
            Borrow.user_id == self._uuid(user_id),
            Borrow.book_id == self._uuid(book_id),
            Borrow.returned_at.is_(None),
        )
        return self.db.scalar(stmt)
