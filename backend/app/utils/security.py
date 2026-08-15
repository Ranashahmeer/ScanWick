import hashlib
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

# bcrypt rounds are driven by BCRYPT_ROUNDS in .env (default 12)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)


def hash_password(password: str) -> str:
    # SHA-256 pre-hash ensures bcrypt's 72-byte input limit never truncates long passwords
    digest = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(digest)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    digest = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(digest, hashed_password)


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": email, "user_id": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token_str() -> str:
    return token_urlsafe(32)


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
