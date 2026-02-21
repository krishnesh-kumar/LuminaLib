from typing import List, Sequence
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, desc
from app.models import RecommendationSnapshot, RecommendationItem, UserTagPreference, Borrow, Book, Tag, Review


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def latest_snapshot(self, user_id: str) -> RecommendationSnapshot | None:
        stmt = select(RecommendationSnapshot).where(RecommendationSnapshot.user_id == user_id).order_by(
            desc(RecommendationSnapshot.generated_at)
        )
        return self.db.scalars(stmt).first()

    def create_snapshot(self, user_id: str, provider: str | None = None) -> RecommendationSnapshot:
        snap = RecommendationSnapshot(user_id=user_id, provider=provider)
        self.db.add(snap)
        self.db.flush()
        return snap

    def replace_items(self, snapshot_id: str, items: List[tuple[str, float]]):
        self.db.execute(delete(RecommendationItem).where(RecommendationItem.snapshot_id == snapshot_id))
        ranked = sorted(items, key=lambda x: x[1], reverse=True)
        for rank, (book_id, score) in enumerate(ranked, start=1):
            self.db.add(
                RecommendationItem(
                    snapshot_id=snapshot_id,
                    book_id=book_id,
                    score=score,
                    rank=rank,
                )
            )
        self.db.flush()

    def user_preferences(self, user_id: str) -> Sequence[UserTagPreference]:
        stmt = select(UserTagPreference).where(UserTagPreference.user_id == user_id)
        return list(self.db.scalars(stmt))

    def user_preferences_with_names(self, user_id: str) -> dict[str, float]:
        stmt = (
            select(Tag.name, UserTagPreference.weight)
            .join(Tag, Tag.id == UserTagPreference.tag_id)
            .where(UserTagPreference.user_id == user_id)
        )
        return {name: weight for name, weight in self.db.execute(stmt)}

    def user_borrowed_book_ids(self, user_id: str) -> set[str]:
        try:
            u = uuid.UUID(str(user_id))
        except Exception:
            u = user_id
        stmt = select(Borrow.book_id).where(Borrow.user_id == u)
        return {str(row[0]) for row in self.db.execute(stmt)}

    # --- ML prep helpers ---
    def interactions(self) -> list[tuple[str, str, float]]:
        rows: list[tuple[str, str, float]] = []
        # borrows as implicit positives
        for user_id, book_id in self.db.execute(select(Borrow.user_id, Borrow.book_id)):
            rows.append((str(user_id), str(book_id), 1.0))
        # reviews add rating/5 capped at +1
        for user_id, book_id, rating in self.db.execute(select(Review.user_id, Review.book_id, Review.rating)):
            bonus = min(1.0, (rating or 0) / 5.0)
            rows.append((str(user_id), str(book_id), bonus))
        return rows

    def index_mappings(self, interactions: list[tuple[str, str, float]]):
        user_ids = sorted({u for u, _, _ in interactions})
        book_ids = sorted({b for _, b, _ in interactions})
        user_to_idx = {u: i for i, u in enumerate(user_ids)}
        book_to_idx = {b: i for i, b in enumerate(book_ids)}
        return user_to_idx, book_to_idx, user_ids, book_ids

    def list_books(self) -> Sequence[Book]:
        stmt = select(Book)
        return list(self.db.scalars(stmt))

    def items_for_snapshot(self, snapshot_id: str) -> Sequence[RecommendationItem]:
        stmt = select(RecommendationItem).where(RecommendationItem.snapshot_id == snapshot_id).order_by(RecommendationItem.rank)
        return list(self.db.scalars(stmt))
