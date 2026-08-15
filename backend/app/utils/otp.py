import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OtpRecord

_OTP_TTL_MINUTES = 10


def generate_otp() -> str:
    # cryptographically random 6-digit code
    return str(secrets.randbelow(900000) + 100000)


async def save_otp(db: AsyncSession, email: str, code: str, purpose: str = "verification") -> None:
    # Remove any existing unexpired OTPs for this email + purpose before inserting
    await db.execute(
        delete(OtpRecord).where(OtpRecord.email == email, OtpRecord.purpose == purpose)
    )
    db.add(
        OtpRecord(
            email=email,
            code=code,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES),
        )
    )
    await db.commit()


async def verify_otp(db: AsyncSession, email: str, code: str, purpose: str = "verification") -> bool:
    result = await db.execute(
        select(OtpRecord)
        .where(OtpRecord.email == email, OtpRecord.purpose == purpose)
        .order_by(OtpRecord.created_at.desc())
    )
    record = result.scalars().first()

    if not record:
        return False

    # Clean up expired record
    if datetime.now(timezone.utc) > record.expires_at.replace(tzinfo=timezone.utc):
        await db.execute(delete(OtpRecord).where(OtpRecord.id == record.id))
        await db.commit()
        return False

    if record.code != code:
        return False

    # Consume the OTP — one-time use
    await db.execute(delete(OtpRecord).where(OtpRecord.id == record.id))
    await db.commit()
    return True
