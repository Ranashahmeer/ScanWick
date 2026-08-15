import logging

import httpx

from app.config import settings

logger = logging.getLogger("app.email")

_BASE_STYLE = (
    "font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;"
)
_CODE_STYLE = (
    "display: inline-block; font-size: 28px; font-weight: bold; letter-spacing: 6px;"
    " padding: 12px 24px; background: #f4f4f5; border-radius: 8px; margin: 16px 0;"
)
_FOOTER = (
    "<p style='font-size:12px;color:#999;margin-top:32px;'>"
    "If you did not request this, you can safely ignore this email."
    "</p>"
)


async def _send(to: str, subject: str, html: str) -> None:
    if not settings.resend_api_key or not settings.resend_from_email:
        print(f"[email] Resend not configured — dev OTP to {to}: {subject}")
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={"from": settings.resend_from_email, "to": to, "subject": subject, "html": html},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"[email] Resend error {exc.response.status_code}: {exc.response.text}")
            if settings.dev_mode:
                return
            raise


async def send_otp_email(email: str, first_name: str, otp: str) -> None:
    if settings.dev_mode:
        print(f"[email] Verification OTP for {email}: {otp}")
    else:
        logger.info("OTP email dispatched to %s", email)
    html = f"""
    <div style="{_BASE_STYLE}">
      <h2 style="color:#1a1a1a;">Verify your email</h2>
      <p>Hi {first_name},</p>
      <p>Use the code below to verify your Scanwick account. It expires in 10 minutes.</p>
      <div style="{_CODE_STYLE}">{otp}</div>
      {_FOOTER}
    </div>
    """
    await _send(email, "Your Scanwick verification code", html)


async def send_login_otp_email(email: str, first_name: str, otp: str) -> None:
    if settings.dev_mode:
        print(f"[email] Login OTP for {email}: {otp}")
    else:
        logger.info("Login OTP email dispatched to %s", email)
    html = f"""
    <div style="{_BASE_STYLE}">
      <h2 style="color:#1a1a1a;">Your login code</h2>
      <p>Hi {first_name},</p>
      <p>Use the code below to complete your sign-in. It expires in 10 minutes.</p>
      <div style="{_CODE_STYLE}">{otp}</div>
      <p>If you didn't try to sign in, your password may be compromised — change it immediately.</p>
      {_FOOTER}
    </div>
    """
    await _send(email, "Your Scanwick login code", html)


async def send_password_reset_email(email: str, first_name: str, reset_link: str) -> None:
    if settings.dev_mode:
        print(f"[email] Password reset link for {email}: {reset_link}")
    else:
        logger.info("Password reset email dispatched to %s", email)
    html = f"""
    <div style="{_BASE_STYLE}">
      <h2 style="color:#1a1a1a;">Reset your password</h2>
      <p>Hi {first_name},</p>
      <p>Click the button below to reset your password. The link expires in 1 hour.</p>
      <a href="{reset_link}"
         style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
                text-decoration:none;border-radius:8px;font-weight:bold;margin:16px 0;">
        Reset password
      </a>
      <p style="font-size:13px;color:#666;">Or copy this link:<br>{reset_link}</p>
      {_FOOTER}
    </div>
    """
    await _send(email, "Reset your Scanwick password", html)


async def send_postmortem_email(email: str, period_type: str, period_start, period_end, pdf_url: str) -> None:
    print(f"[email] {period_type.title()} post-mortem ready for {email}: {period_start}–{period_end}")
    html = f"""
    <div style="{_BASE_STYLE}">
      <h2 style="color:#1a1a1a;">Your {period_type} post-mortem is ready</h2>
      <p>Covering {period_start.isoformat()} to {period_end.isoformat()}.</p>
      <a href="{pdf_url}"
         style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
                text-decoration:none;border-radius:8px;font-weight:bold;margin:16px 0;">
        Download report
      </a>
      {_FOOTER}
    </div>
    """
    await _send(email, f"Your Scanwick {period_type} post-mortem is ready", html)


async def send_team_invite_email(email: str, inviter_name: str, accept_link: str) -> None:
    print(f"[email] Team invite for {email} from {inviter_name}: {accept_link}")
    html = f"""
    <div style="{_BASE_STYLE}">
      <h2 style="color:#1a1a1a;">You've been invited to Scanwick</h2>
      <p>{inviter_name} has invited you to join their team on Scanwick. Click below to accept
      — the link expires in 7 days.</p>
      <a href="{accept_link}"
         style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
                text-decoration:none;border-radius:8px;font-weight:bold;margin:16px 0;">
        Accept invite
      </a>
      <p style="font-size:13px;color:#666;">Or copy this link:<br>{accept_link}</p>
      {_FOOTER}
    </div>
    """
    await _send(email, f"{inviter_name} invited you to join their team on Scanwick", html)
