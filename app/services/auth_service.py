from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.user_repo import UserRepository
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.core import security


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    def signup(self, email: str, password: str):
        if self.users.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        password_hash = security.hash_password(password)
        user = self.users.create(email=email, password_hash=password_hash)
        self.db.refresh(user)
        return user

    def login(self, email: str, password: str):
        user = self.users.get_by_email(email)
        if not user or not security.verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        tokens = self._issue_tokens(user.id)
        self.db.commit()
        return user, tokens

    def refresh(self, refresh_token: str):
        payload = security.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        token_hash = security.hash_refresh_token(refresh_token)
        deleted = self.refresh_tokens.revoke(token_hash)
        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        # ensure single-active: clear any other refresh tokens for this user
        self.refresh_tokens.revoke_all_for_user(user_id)
        tokens = self._issue_tokens(user_id)
        self.db.commit()
        return tokens

    def logout(self, refresh_token: str):
        payload = security.decode_token(refresh_token)
        user_id = payload.get("sub")
        # revoke all refresh tokens for this user
        self.refresh_tokens.revoke_all_for_user(user_id)
        self.db.commit()

    def _issue_tokens(self, user_id: str):
        access = security.create_access_token(user_id)
        refresh = security.create_refresh_token(user_id)
        expires_at = datetime.utcnow() + timedelta(days=security.settings.JWT_REFRESH_EXPIRES_DAYS)
        token_hash = security.hash_refresh_token(refresh)
        self.refresh_tokens.add(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
