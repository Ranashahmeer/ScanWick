"""Smoke test for app/routes/auth.py — locks in the core register -> verify
-> authenticated request happy path so future changes don't silently break it."""

import asyncio

from sqlalchemy import select

from app.models import OtpRecord, PasswordReset, User
from app.utils.security import verify_password


def test_register_verify_and_me_smoke(sync_client, db_session_factory):
    register_response = sync_client.post(
        "/api/auth/register",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert register_response.status_code == 201
    assert "verification code" in register_response.json()["message"].lower()

    otp_code = asyncio.run(_fetch_latest_otp(db_session_factory, "ada@example.com"))
    assert (
        otp_code is not None
    ), "expected an OTP record to have been created on register"

    verify_response = sync_client.post(
        "/api/auth/verify-otp",
        json={"email": "ada@example.com", "otp": otp_code, "purpose": "verification"},
    )
    assert verify_response.status_code == 200
    tokens = verify_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me_response = sync_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["email"] == "ada@example.com"
    assert me_body["first_name"] == "Ada"
    assert me_body["is_verified"] is True
    assert me_body["merchant_id"], "verify-otp should auto-provision a merchant_id"

    # /me is idempotent — a second fetch returns the same merchant_id, not a
    # freshly re-provisioned one.
    second_me_response = sync_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert second_me_response.json()["merchant_id"] == me_body["merchant_id"]


def test_reregistering_unverified_email_does_not_overwrite_password(
    sync_client, db_session_factory
):
    first_response = sync_client.post(
        "/api/auth/register",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "password": "original-correct-horse",
        },
    )
    assert first_response.status_code == 201 

    second_response = sync_client.post(
        "/api/auth/register",
        json={
            "first_name": "Mallory",
            "last_name": "Attacker",
            "email": "ada@example.com",
            "password": "attacker-password",
        },
    )
    assert second_response.status_code == 201

    user_before_verify = asyncio.run(_fetch_user(db_session_factory, "ada@example.com"))
    assert user_before_verify is not None
    assert user_before_verify.first_name == "Ada"
    assert user_before_verify.last_name == "Lovelace"
    assert verify_password("original-correct-horse", user_before_verify.hashed_password)
    assert not verify_password("attacker-password", user_before_verify.hashed_password)

    otp_code = asyncio.run(_fetch_latest_otp(db_session_factory, "ada@example.com"))
    verify_response = sync_client.post(
        "/api/auth/verify-otp",
        json={"email": "ada@example.com", "otp": otp_code, "purpose": "verification"},
    )
    assert verify_response.status_code == 200

    attacker_login_response = sync_client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "attacker-password"},
    )
    assert attacker_login_response.status_code == 401

    original_login_response = sync_client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "original-correct-horse"},
    )
    assert original_login_response.status_code == 200


def test_forgot_password_unknown_email_tells_user_to_register(sync_client):
    """Product decision (reverses the endpoint's prior anti-enumeration
    design on purpose): a non-existent email must get a clear "register
    first" message rather than the generic "if registered..." response."""
    response = sync_client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})

    assert response.status_code == 404
    assert "register" in response.json()["detail"].lower()


def test_forgot_password_unverified_account_tells_user_to_verify(sync_client):
    register_response = sync_client.post(
        "/api/auth/register",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada-unverified@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert register_response.status_code == 201

    response = sync_client.post("/api/auth/forgot-password", json={"email": "ada-unverified@example.com"})

    assert response.status_code == 400
    assert "verif" in response.json()["detail"].lower()


def test_forgot_password_verified_account_sends_a_reset_link(sync_client, db_session_factory):
    register_response = sync_client.post(
        "/api/auth/register",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada-verified@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert register_response.status_code == 201
    otp_code = asyncio.run(_fetch_latest_otp(db_session_factory, "ada-verified@example.com"))
    verify_response = sync_client.post(
        "/api/auth/verify-otp",
        json={"email": "ada-verified@example.com", "otp": otp_code, "purpose": "verification"},
    )
    assert verify_response.status_code == 200

    response = sync_client.post("/api/auth/forgot-password", json={"email": "ada-verified@example.com"})

    assert response.status_code == 200
    assert "sent" in response.json()["message"].lower()

    async def _fetch_reset_token() -> PasswordReset | None:
        async with db_session_factory() as session:
            result = await session.execute(
                select(PasswordReset).where(PasswordReset.email == "ada-verified@example.com")
            )
            return result.scalars().first()

    reset_row = asyncio.run(_fetch_reset_token())
    assert reset_row is not None
    assert reset_row.token


async def _fetch_latest_otp(session_factory, email: str) -> str | None:
    async with session_factory() as session:
        result = await session.execute(
            select(OtpRecord)
            .where(OtpRecord.email == email)
            .order_by(OtpRecord.created_at.desc())
        )
        record = result.scalars().first()
        return record.code if record else None


async def _fetch_user(session_factory, email: str) -> User | None:
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()
