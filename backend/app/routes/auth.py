import base64
import io
import re
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode, urlparse
from uuid import uuid4

import httpx
import pyotp
import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import LoginEvent, LoginEventResult, PasswordReset, RefreshToken, User, UserMerchantRole
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginEventOut,
    LoginPendingResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendOtpRequest,
    ResetPasswordRequest,
    RoleOut,
    SessionOut,
    TokenResponse,
    TwoFactorCodeRequest,
    TwoFactorDisableRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyLoginRequest,
    UpdateProfileRequest,
    UserOut,
    VerifyOtpRequest,
)
from app.services.encryption import decrypt_field, encrypt_field
from app.services.merchant_provisioning import ensure_merchant_provisioned
from app.services.redis_client import redis_client
from app.services.storage import upload_file
from app.utils.email import (
    send_login_otp_email,
    send_otp_email,
    send_password_reset_email,
)
from app.utils.otp import generate_otp, save_otp, verify_otp
from app.utils.security import (
    create_access_token,
    create_refresh_token_str,
    hash_password,
    refresh_token_expiry,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_GOOGLE_STATE_TTL_SECONDS = 600  # 10 minutes
_RESET_TOKEN_TTL = timedelta(hours=1)

# Per-account OTP brute-force lockout (in addition to main.py's per-IP rate
# limiter, which doesn't stop an attacker spreading guesses across IPs).
_OTP_MAX_ATTEMPTS = 10
_OTP_LOCKOUT_WINDOW_SECONDS = 15 * 60


# ── Helpers ───────────────────────────────────────────────────────────────────

def _otp_attempts_key(email: str, purpose: str) -> str:
    return f"otp-attempts:{purpose}:{email.lower()}"


def _require_google_oauth_config() -> None:
    if settings.google_client_id and settings.google_client_secret:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Google OAuth is not configured.",
    )


def _is_allowed_frontend_origin(origin: str) -> bool:
    """Same allowlist as main.py's CORS config (kept separate since
    CORSMiddleware and this need different shapes — a static list vs. a
    predicate — but must stay in sync): production domains always, plus,
    only in dev_mode, localhost and any cloudflared quick-tunnel host."""
    if origin in {"https://scanwick.com", "https://www.scanwick.com"}:
        return True
    if settings.dev_mode:
        if origin in {
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        }:
            return True
        if re.fullmatch(r"https://[a-z0-9-]+\.trycloudflare\.com", origin):
            return True
    return False


def _derive_frontend_origin(request: Request) -> str:
    """Captures which frontend to send the browser back to after Google
    login, mirroring _derive_redirect_uri's per-request approach but from
    the Referer header instead of Host: the browser reaches /google via a
    full-page navigation from the frontend (GoogleButton does
    window.location.href), so Referer is the frontend's own origin at the
    moment this runs. By the time /google/callback runs, the request's
    Host is the backend's own origin (a different tunnel host than the
    frontend's, when testing through cloudflared), so it can't be read
    there — the caller must thread this value through instead (see the
    oauth-state Redis entry).

    Validated against _is_allowed_frontend_origin before use: this value
    ends up in a redirect carrying access/refresh tokens in the URL
    fragment, so trusting an arbitrary Referer would be an open redirect
    that leaks tokens to whatever origin the browser reports.
    """
    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if _is_allowed_frontend_origin(origin):
            return origin
    return settings.frontend_url


def _build_frontend_redirect(frontend_origin: str, access_token: str, refresh_token: str) -> str:
    fragment = urlencode(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "provider": "google",
        }
    )
    return f"{frontend_origin}/#{fragment}"


async def _issue_tokens(user: User, db: AsyncSession, request: Request) -> TokenResponse:
    access_token = create_access_token(user.id, user.email)
    raw_refresh = create_refresh_token_str()
    db.add(
        RefreshToken(
            user_id=user.id,
            token=raw_refresh,
            expires_at=refresh_token_expiry(),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            last_used_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


async def _log_login_event(
    db: AsyncSession, user_id: int, result: LoginEventResult, reason: str | None, request: Request
) -> None:
    """Backs the Login & Security tab's "Login history" — only called once a
    user row was actually found (never for an unknown email), same
    anti-enumeration reasoning as resend_otp_route above."""
    db.add(
        LoginEvent(
            user_id=user_id,
            result=result,
            reason=reason,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    await db.commit()


async def _build_user_out(db: AsyncSession, user: User) -> UserOut:
    # Idempotent — also backfills merchant_id for any account that predates
    # this provisioning step (e.g. verified before this was added).
    merchant_id = await ensure_merchant_provisioned(db, user.id)
    user_out = UserOut.model_validate(user, from_attributes=True)
    user_out.merchant_id = str(merchant_id)

    role_rows = (
        (
            await db.execute(
                select(UserMerchantRole).where(
                    UserMerchantRole.user_id == user.id, UserMerchantRole.merchant_id == merchant_id
                )
            )
        )
        .scalars()
        .all()
    )
    user_out.roles = [
        RoleOut(vertical=row.vertical.value, role=row.role, rep_id=str(row.rep_id) if row.rep_id else None)
        for row in role_rows
    ]
    return user_out


# ── Registration ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalars().first()

    if existing and existing.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    if not existing:
        db.add(
            User(
                first_name=body.first_name,
                last_name=body.last_name,
                email=body.email,
                hashed_password=hash_password(body.password),
                is_verified=False,
            )
        )

    await db.commit()

    code = generate_otp()
    await save_otp(db, body.email, code, purpose="verification")
    await send_otp_email(body.email, (existing.first_name if existing else body.first_name) or "there", code)

    return RegisterResponse(
        message="Registration successful. Please check your email for the verification code."
    )


# ── OTP Verification (registration + login 2FA) ───────────────────────────────

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_route(body: VerifyOtpRequest, request: Request, db: AsyncSession = Depends(get_db)):
    attempts_key = _otp_attempts_key(body.email, body.purpose)
    if redis_client.get_counter(attempts_key) >= _OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Please request a new code and try again later.",
        )

    valid = await verify_otp(db, body.email, body.otp, purpose=body.purpose)
    if not valid:
        redis_client.incr_with_ttl(attempts_key, _OTP_LOCKOUT_WINDOW_SECONDS)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # A correct OTP alone must never be sufficient for purpose="login" — that
    # would let anyone who can read a "login OTP" email in, with no password
    # at all. Require the password too, same check as the real /login route.
    if body.purpose == "login":
        if not body.password or not user.hashed_password or not verify_password(
            body.password, user.hashed_password
        ):
            redis_client.incr_with_ttl(attempts_key, _OTP_LOCKOUT_WINDOW_SECONDS)
            await _log_login_event(db, user.id, LoginEventResult.blocked, "invalid_password", request)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

    redis_client.delete_value(attempts_key)

    if body.purpose == "verification":
        user.is_verified = True
        await db.commit()
        await db.refresh(user)
        await ensure_merchant_provisioned(db, user.id)
    else:
        await _log_login_event(db, user.id, LoginEventResult.success, None, request)

    return await _issue_tokens(user, db, request)


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp_route(body: ResendOtpRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalars().first()

    # Always return the same message to avoid user enumeration
    if not user:
        return MessageResponse(message="If that email is registered, a new code has been sent.")

    if body.purpose == "verification" and user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account already verified.")

    if body.purpose == "login" and not user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is not verified.")

    code = generate_otp()
    await save_otp(db, body.email, code, purpose=body.purpose)

    if body.purpose == "login":
        await send_login_otp_email(body.email, user.first_name or "there", code)
    else:
        await send_otp_email(body.email, user.first_name or "there", code)

    # Same literal text as the unknown-email branch above — a differently
    # worded success message would itself reveal whether the email is
    # registered, defeating the anti-enumeration intent.
    return MessageResponse(message="If that email is registered, a new code has been sent.")


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse | LoginPendingResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalars().first()

    # Same error for wrong email or wrong password — prevents user enumeration
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        if user:
            await _log_login_event(db, user.id, LoginEventResult.blocked, "invalid_password", request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_verified:
        await _log_login_event(db, user.id, LoginEventResult.blocked, "unverified", request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    # Password alone is confirmed correct at this point — but with TOTP 2FA
    # enabled, tokens must not be issued yet. The frontend follows up with
    # POST /2fa/verify-login (which re-checks the password too) once the
    # user supplies their code.
    if user.totp_enabled:
        return LoginPendingResponse(message="Enter your two-factor authentication code.", email=user.email)

    await _log_login_event(db, user.id, LoginEventResult.success, None, request)
    return await _issue_tokens(user, db, request)


@router.post("/2fa/verify-login", response_model=TokenResponse)
async def verify_2fa_login(body: TwoFactorVerifyLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalars().first()

    # A correct TOTP code alone must never be sufficient — same reasoning as
    # verify_otp_route's purpose="login" branch — so the password is
    # re-checked here even though /login already checked it once.
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        if user:
            await _log_login_event(db, user.id, LoginEventResult.blocked, "invalid_password", request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled for this account.",
        )

    secret = decrypt_field(user.totp_secret)
    if not pyotp.TOTP(secret).verify(body.code, valid_window=1):
        await _log_login_event(db, user.id, LoginEventResult.blocked, "invalid_2fa_code", request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid two-factor code.")

    await _log_login_event(db, user.id, LoginEventResult.success, None, request)
    return await _issue_tokens(user, db, request)


# ── Token Refresh & Logout ────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == body.refresh_token))
    stored = result.scalars().first()

    if not stored or stored.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired.",
        )

    result = await db.execute(select(User).where(User.id == stored.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    await db.execute(delete(RefreshToken).where(RefreshToken.id == stored.id))
    await db.commit()

    return await _issue_tokens(user, db, request)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(RefreshToken).where(RefreshToken.token == body.refresh_token))
    await db.commit()
    return MessageResponse(message="Logged out successfully.")


# ── Current User ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _build_user_out(db, current_user)


# ── Profile (Account tab) ─────────────────────────────────────────────────────

@router.patch("/me", response_model=UserOut)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return await _build_user_out(db, current_user)


_MAX_AVATAR_BYTES = 5 * 1024 * 1024
_AVATAR_CONTENT_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    extension = _AVATAR_CONTENT_TYPES.get(file.content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG, JPEG, or WEBP images are supported.",
        )
    data = await file.read()
    if len(data) > _MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image must be smaller than 5 MB.")

    key = f"avatars/{current_user.id}/{uuid4()}.{extension}"
    current_user.avatar_url = upload_file(key, data)
    await db.commit()
    await db.refresh(current_user)
    return await _build_user_out(db, current_user)


# ── Password change (Login & Security tab) ────────────────────────────────────

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account signs in with Google and has no password to change.",
        )
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")

    current_user.hashed_password = hash_password(body.new_password)
    # Invalidate all existing refresh tokens on password change — same as
    # reset-password's existing behavior.
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == current_user.id))
    await db.commit()
    return MessageResponse(message="Password updated successfully. Please log in again.")


# ── Two-factor authentication (Login & Security tab) ──────────────────────────

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Generates a fresh secret every call — safe to call repeatedly (e.g. the
    # user re-opens the QR step) since `totp_enabled` (untouched here) is the
    # only thing that ever gates login; an abandoned setup can't lock anyone
    # out or leave a stale secret active.
    secret = pyotp.random_base32()
    current_user.totp_secret = encrypt_field(secret)
    current_user.totp_enabled = False
    await db.commit()

    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name="Scanwick")
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return TwoFactorSetupResponse(secret=secret, qr_code_base64=f"data:image/png;base64,{qr_base64}")


@router.post("/2fa/enable", response_model=MessageResponse)
async def enable_2fa(
    body: TwoFactorCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start two-factor setup first.")

    secret = decrypt_field(current_user.totp_secret)
    if not pyotp.TOTP(secret).verify(body.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code. Please try again.")

    current_user.totp_enabled = True
    await db.commit()
    return MessageResponse(message="Two-factor authentication is now enabled.")


@router.post("/2fa/disable", response_model=MessageResponse)
async def disable_2fa(
    body: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Requires the current password rather than a TOTP code — a lost
    # authenticator device must never permanently lock someone out of
    # disabling 2FA on their own account.
    if not current_user.hashed_password or not verify_password(
        body.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()
    return MessageResponse(message="Two-factor authentication has been disabled.")


# ── Sessions & login history (Login & Security tab) ───────────────────────────

@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.user_id == current_user.id)
        .order_by(RefreshToken.last_used_at.desc(), RefreshToken.created_at.desc())
    )
    tokens = result.scalars().all()
    return [
        SessionOut(
            id=token.id,
            device=token.user_agent,
            ip_address=token.ip_address,
            last_used_at=token.last_used_at,
            created_at=token.created_at,
            is_current=(index == 0),
        )
        for index, token in enumerate(tokens)
    ]


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(RefreshToken).where(RefreshToken.id == session_id, RefreshToken.user_id == current_user.id)
    )
    await db.commit()
    return MessageResponse(message="Session revoked.")


@router.get("/login-history", response_model=list[LoginEventOut])
async def login_history(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LoginEvent)
        .where(LoginEvent.user_id == current_user.id)
        .order_by(LoginEvent.created_at.desc())
        .limit(20)
    )
    events = result.scalars().all()
    return [
        LoginEventOut(
            id=str(event.id),
            when=event.created_at,
            device=event.user_agent,
            ip_address=event.ip_address,
            result=event.result.value,
            reason=event.reason,
        )
        for event in events
    ]


# ── Account deletion (Privacy & Data tab) ─────────────────────────────────────

@router.post("/delete-account", response_model=MessageResponse)
async def request_account_deletion(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    current_user.deletion_requested_at = datetime.now(timezone.utc)
    # Forces re-login everywhere — deliberately does NOT block future login
    # (see plan notes): blocking login would make cancelling impossible
    # without a separate unauthenticated flow.
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == current_user.id))
    await db.commit()
    return MessageResponse(
        message="Your account is scheduled for deletion. You can cancel this any time before it's finalized."
    )


@router.post("/delete-account/cancel", response_model=MessageResponse)
async def cancel_account_deletion(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    current_user.deletion_requested_at = None
    await db.commit()
    return MessageResponse(message="Account deletion has been cancelled.")


# ── Password Reset ────────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Deliberately discloses account existence (product decision) —
    reverses the anti-enumeration design this endpoint used to have (every
    outcome returned the identical "if registered..." message specifically
    to prevent a caller from learning which emails are registered). Traded
    off in favor of telling the user plainly what's wrong so they're not
    stuck guessing. Be aware this does let a caller enumerate registered
    emails via this endpoint."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email. Please register first.",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account hasn't been verified yet. Please check your email for the verification code.",
        )

    # Delete any existing reset tokens for this email
    await db.execute(delete(PasswordReset).where(PasswordReset.email == body.email))

    raw_token = token_urlsafe(32)
    db.add(
        PasswordReset(
            email=body.email,
            token=raw_token,
            expires_at=datetime.now(timezone.utc) + _RESET_TOKEN_TTL,
        )
    )
    await db.commit()

    reset_link = f"{settings.frontend_url}/reset?token={raw_token}"
    await send_password_reset_email(body.email, user.first_name or "there", reset_link)

    return MessageResponse(message="A password reset link has been sent to your email.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PasswordReset).where(PasswordReset.token == body.token))
    record = result.scalars().first()

    if not record or record.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has expired.",
        )

    result = await db.execute(select(User).where(User.email == record.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.hashed_password = hash_password(body.new_password)
    await db.execute(delete(PasswordReset).where(PasswordReset.email == record.email))
    # Invalidate all existing refresh tokens on password change
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    await db.commit()

    return MessageResponse(message="Password updated successfully. Please log in again.")


# ── Google OAuth ──────────────────────────────────────────────────────────────

def _derive_redirect_uri(request: Request) -> str:
    """Builds the OAuth redirect_uri from the incoming request's own Host
    header instead of a single fixed settings value, so Google sign-in
    works both hit directly (http://localhost:8000/...) and through a
    reverse proxy/tunnel (e.g. a cloudflared quick tunnel used for
    temporary client testing, https://<random>.trycloudflare.com/...) with
    no config change or restart between the two. /google and /google/
    callback both call this, so a single sign-in attempt always computes
    the same value on both ends (Google requires the token-exchange
    redirect_uri to match the authorization request's exactly) as long as
    the client stays on the same host for the whole flow, which it always
    does within one attempt.

    Whatever this resolves to must also be registered as an Authorized
    redirect URI in Google Cloud Console — this doesn't bypass that
    requirement, it just means multiple hosts (localhost + a tunnel) can
    each be registered once and both work without touching .env.
    Falls back to settings.google_redirect_uri if the Host header is
    somehow absent (shouldn't happen over HTTP/1.1+)."""
    host = request.headers.get("host")
    if not host:
        return settings.google_redirect_uri
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{scheme}://{host}/api/auth/google/callback"


@router.get("/google")
async def google_login(request: Request):
    _require_google_oauth_config()

    state = token_urlsafe(32)
    # Stored in Redis (not an in-process dict) so /google and /google/callback
    # still work correctly when they land on different worker processes or
    # replicas — a plain in-memory dict would intermittently 400 real logins
    # under any multi-process/multi-replica deployment. The value itself is
    # the frontend origin to redirect back to (see _derive_frontend_origin) —
    # riding along on the same key /google/callback already looks up by
    # state, rather than a second Redis round trip.
    redis_client.set_value(
        f"oauth-state:{state}", _derive_frontend_origin(request), ttl_seconds=_GOOGLE_STATE_TTL_SECONDS
    )

    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": _derive_redirect_uri(request),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url=auth_url)
    return JSONResponse({"authorization_url": auth_url})


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    _require_google_oauth_config()

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Google OAuth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state.")

    # Atomic get-and-delete — a state token is single-use either way. The
    # value is the frontend origin /google stashed for us (see
    # _derive_frontend_origin) since this request's own Host is the
    # backend's origin, not the frontend's.
    frontend_origin = redis_client.pop_value(f"oauth-state:{state}")
    if frontend_origin is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": _derive_redirect_uri(request),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != status.HTTP_200_OK:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to exchange Google code.")

        userinfo_resp = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token_resp.json()['access_token']}"},
        )
        if userinfo_resp.status_code != status.HTTP_200_OK:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch Google profile.")

    google_user = userinfo_resp.json()
    email = (google_user.get("email") or "").strip().lower()
    google_id = google_user.get("sub")

    if not email or not google_id or not google_user.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account has no verified email.")

    from sqlalchemy import or_
    result = await db.execute(select(User).where(or_(User.email == email, User.google_id == google_id)))
    user = result.scalars().first()

    given_name = google_user.get("given_name") or (google_user.get("name", "") or "").split(" ")[0] or None
    family_name = google_user.get("family_name") or None
    picture = google_user.get("picture")

    if user:
        user.email = email
        user.google_id = google_id
        user.avatar_url = picture
        user.is_verified = True
        if given_name and not user.first_name:
            user.first_name = given_name
        if family_name and not user.last_name:
            user.last_name = family_name
    else:
        user = User(
            first_name=given_name,
            last_name=family_name,
            email=email,
            google_id=google_id,
            avatar_url=picture,
            is_verified=True,
        )
        db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        # The Google-reported email now collides with a different existing
        # user's `users.email` (unique-indexed) — a real but rare scenario
        # (e.g. two accounts, one later linked to a Google identity sharing
        # the other's address). Fail cleanly instead of a bare 500.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Google account's email is already associated with a different account.",
        )
    await db.refresh(user)
    await ensure_merchant_provisioned(db, user.id)

    await _log_login_event(db, user.id, LoginEventResult.success, None, request)
    tokens = await _issue_tokens(user, db, request)
    return RedirectResponse(
        url=_build_frontend_redirect(frontend_origin, tokens.access_token, tokens.refresh_token)
    )
