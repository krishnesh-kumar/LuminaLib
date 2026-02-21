from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.repositories.borrow_repo import BorrowRepository
from app.core.celery_app import celery_app


class BorrowService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BorrowRepository(db)

    def borrow(self, user_id: str, book_id: str):
        if self.repo.get_active_by_book(book_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book already borrowed")
        if self.repo.get_active_by_user(user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has an active borrow")
        borrow = self.repo.create(user_id=user_id, book_id=book_id)
        self._enqueue_recompute(user_id)
        return borrow

    def return_book(self, user_id: str, book_id: str):
        borrow = self.repo.get_active_by_user_and_book(user_id, book_id)
        if not borrow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active borrow not found")
        borrow.returned_at = borrow.returned_at or datetime.utcnow()
        self._enqueue_recompute(user_id)
        return borrow

    def _enqueue_recompute(self, user_id: str):
        celery_app.send_task("app.workers.tasks.recompute_user_preferences", args=[user_id])
        celery_app.send_task("app.workers.tasks.recompute_recommendations", args=[user_id])
