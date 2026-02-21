from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken:
        rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(rt)
        self.db.flush()
        return rt

    def revoke(self, token_hash: str) -> int:
        stmt = delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = self.db.execute(stmt)
        return result.rowcount or 0

    def revoke_all_for_user(self, user_id: str) -> int:
        try:
            uid = uuid.UUID(str(user_id))
        except Exception:
            uid = user_id
        stmt = delete(RefreshToken).where(RefreshToken.user_id == uid)
        result = self.db.execute(stmt)
        return result.rowcount or 0

    def find(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.scalar(stmt)
