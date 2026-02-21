import hashlib
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# Use PBKDF2-SHA256 to avoid bcrypt backend/length issues in slim images
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_refresh_token(token: str) -> str:
    return _hash_refresh_token(token)


def create_access_token(subject: str, extra: Optional[dict[str, Any]] = None) -> str:
    to_encode = {"sub": str(subject), "type": "access"}
    if extra:
        to_encode.update(extra)
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_EXPIRES_MIN)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    now = datetime.utcnow()
    to_encode = {"sub": str(subject), "type": "refresh", "iat": now, "jti": str(uuid4())}
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRES_DAYS)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
