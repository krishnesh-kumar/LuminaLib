from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class Book(Base):
    __tablename__ = "books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    isbn = Column(String(50), nullable=True, unique=True)
    language = Column(String(50), nullable=True)
    published_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BookFile(Base):
    __tablename__ = "book_files"
    __table_args__ = (UniqueConstraint("book_id", name="uq_book_files_book_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    storage_provider = Column(String(50), nullable=False)
    object_key = Column(String(512), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf | txt
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    original_filename = Column(String(255), nullable=True)


class BookAISummary(Base):
    __tablename__ = "book_ai_summaries"
    __table_args__ = (UniqueConstraint("book_id", name="uq_book_ai_summaries_book_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class BookReviewConsensus(Base):
    __tablename__ = "book_review_consensus"
    __table_args__ = (UniqueConstraint("book_id", name="uq_book_review_consensus_book_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    consensus = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Borrow(Base):
    __tablename__ = "borrows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    borrowed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_at = Column(DateTime, nullable=True)
    returned_at = Column(DateTime, nullable=True)


Index(
    "ix_borrows_book_active",
    Borrow.book_id,
    unique=True,
    postgresql_where=(Borrow.returned_at.is_(None)),
)

Index(
    "ix_borrows_user_active",
    Borrow.user_id,
    unique=True,
    postgresql_where=(Borrow.returned_at.is_(None)),
)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_reviews_user_book"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)


class BookTag(Base):
    __tablename__ = "book_tags"
    __table_args__ = (UniqueConstraint("book_id", "tag_id", name="uq_book_tags_book_tag"),)

    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class UserTagPreference(Base):
    __tablename__ = "user_tag_preferences"
    __table_args__ = (UniqueConstraint("user_id", "tag_id", name="uq_user_tag_pref_user_tag"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    weight = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RecommendationSnapshot(Base):
    __tablename__ = "recommendation_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    provider = Column(String(50), nullable=True)


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"
    __table_args__ = (UniqueConstraint("snapshot_id", "book_id", name="uq_recommendation_items_snapshot_book"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("recommendation_snapshots.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
