import pytest

from app.config import settings
from app.utils.email import (
    send_login_otp_email,
    send_otp_email,
    send_password_reset_email,
)


@pytest.mark.asyncio
async def test_auth_email_helpers_do_not_print_secrets_outside_dev_mode(
    monkeypatch, capsys
):
    monkeypatch.setattr(settings, "dev_mode", False)

    await send_otp_email("ada@example.com", "Ada", "123456")
    await send_login_otp_email("ada@example.com", "Ada", "654321")
    await send_password_reset_email(
        "ada@example.com",
        "Ada",
        "https://scanwick.test/reset?token=raw-reset-token",
    )

    captured = capsys.readouterr()
    output = captured.out + captured.err

    assert "123456" not in output
    assert "654321" not in output
    assert "raw-reset-token" not in output
    assert "https://scanwick.test/reset" not in output
