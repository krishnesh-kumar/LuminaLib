from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Review


class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, book_id: str, rating: int, review_text: str | None):
        review = Review(user_id=user_id, book_id=book_id, rating=rating, review_text=review_text)
        self.db.add(review)
        self.db.flush()
        return review

    def get_by_user_book(self, user_id: str, book_id: str) -> Optional[Review]:
        stmt = select(Review).where(Review.user_id == user_id, Review.book_id == book_id)
        return self.db.scalar(stmt)

    def list_for_book(self, book_id: str):
        stmt = select(Review).where(Review.book_id == book_id)
        return list(self.db.scalars(stmt))
