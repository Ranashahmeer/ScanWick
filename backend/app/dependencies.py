from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import User

security = HTTPBearer()
_optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: Optional[HTTPAuthorizationCredentials] = Depends(_optional_security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Same JWT decoding as `get_current_user`, but returns `None` instead
    of raising on a missing or invalid token — for routes that behave
    correctly either way (e.g. `POST /api/v1/team/invite/{token}/accept`,
    where an anonymous caller is creating a brand-new account and an
    already-logged-in caller is just confirming they own the invited
    email)."""
    if token is None:
        return None
    try:
        payload = jwt.decode(token.credentials, settings.secret_key, algorithms=[settings.algorithm])
        email = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()