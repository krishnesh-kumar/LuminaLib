from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import BookAISummary, BookReviewConsensus


class BookSummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, book_id: str) -> Optional[BookAISummary]:
        stmt = select(BookAISummary).where(BookAISummary.book_id == book_id)
        return self.db.scalar(stmt)

    def get_consensus(self, book_id: str) -> Optional[BookReviewConsensus]:
        stmt = select(BookReviewConsensus).where(BookReviewConsensus.book_id == book_id)
        return self.db.scalar(stmt)
