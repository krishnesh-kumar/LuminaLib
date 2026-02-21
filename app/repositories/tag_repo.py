from typing import List, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models import Tag, BookTag


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, name: str) -> Tag:
        tag = self.db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if tag:
            return tag
        tag = Tag(name=name)
        self.db.add(tag)
        self.db.flush()
        return tag

    def set_book_tags(self, book_id: str, tag_names: List[str]):
        # clear existing
        self.db.execute(delete(BookTag).where(BookTag.book_id == book_id))
        for name in tag_names:
            tag = self.get_or_create(name.strip())
            bt = BookTag(book_id=book_id, tag_id=tag.id)
            self.db.merge(bt)
        self.db.flush()

    def get_tags_for_book(self, book_id: str) -> Sequence[Tag]:
        stmt = select(Tag).join(BookTag, Tag.id == BookTag.tag_id).where(BookTag.book_id == book_id)
        return list(self.db.scalars(stmt))

    def get_tags_for_books(self) -> dict[str, list[str]]:
        stmt = select(BookTag.book_id, Tag.name).join(Tag, Tag.id == BookTag.tag_id)
        mapping: dict[str, list[str]] = {}
        for book_id, name in self.db.execute(stmt):
            mapping.setdefault(str(book_id), []).append(name)
        return mapping
