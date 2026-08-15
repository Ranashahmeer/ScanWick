"""Field-level cryptography helpers.

Two distinct modes for sensitive fields, chosen per-field by whether the
plaintext ever needs to be read back:
  - encrypt_field / decrypt_field: reversible (Fernet, symmetric). Use only
    when the application has a real need to recover the original value.
  - hash_value: one-way (SHA-256). Use for matching/dedup where the original
    value never needs to be recovered — this is what should back any lookup
    or uniqueness check, since it never exposes the plaintext even in memory
    after hashing.
"""
from __future__ import annotations

import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import DEFAULT_FERNET_KEY, settings

logger = logging.getLogger("app.encryption")

if settings.fernet_key == DEFAULT_FERNET_KEY:
    # The hard failure for dev_mode=False lives in app/main.py's startup
    # check (it needs to run once, loudly, at boot — not on every import of
    # this module). Here we only add a warning so the dev-mode case is
    # still visible in logs.
    if settings.dev_mode:
        logger.warning(
            "FERNET_KEY is not set — using the public dev-only default key. "
            "Encrypted fields are NOT actually confidential in this configuration. "
            "Set FERNET_KEY before storing any real sensitive data."
        )

_fernet = Fernet(settings.fernet_key.encode())


def encrypt_field(plaintext: str) -> str:
    """Encrypt `plaintext`, returning a Fernet token (URL-safe base64 string)."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a Fernet token produced by encrypt_field. Raises ValueError on
    an invalid token or wrong key, rather than letting the cryptography
    library's exception type leak as an implementation detail."""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt field: invalid token or wrong key") from exc


def hash_value(plaintext: str) -> str:
    """One-way SHA-256 hex digest, for matching/dedup without ever storing
    or being able to recover the original value."""
    return hashlib.sha256(plaintext.encode()).hexdigest()
