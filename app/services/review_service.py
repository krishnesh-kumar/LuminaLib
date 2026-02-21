from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.review_repo import ReviewRepository
from app.repositories.borrow_repo import BorrowRepository
from app.core.celery_app import celery_app


class ReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.reviews = ReviewRepository(db)
        self.borrows = BorrowRepository(db)

    def add_review(self, user_id: str, book_id: str, rating: int, review_text: str | None):
        # Ensure user has borrowed this book (any historical borrow)
        borrow = self.borrows.get_by_user_and_book_any(user_id, book_id)
        if not borrow:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrow required before review")
        if self.reviews.get_by_user_book(user_id, book_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review already exists")

        review = self.reviews.create(user_id=user_id, book_id=book_id, rating=rating, review_text=review_text)
        self._enqueue_consensus(book_id)
        return review

    def list_reviews(self, book_id: str):
        return self.reviews.list_for_book(book_id)

    def _enqueue_consensus(self, book_id: str):
        celery_app.send_task("app.workers.tasks.update_review_consensus", args=[book_id])
