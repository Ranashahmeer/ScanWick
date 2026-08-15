import pytest

from app.services.encryption import decrypt_field, encrypt_field, hash_value


def test_encrypt_decrypt_round_trip():
    plaintext = "1234567890123456"

    ciphertext = encrypt_field(plaintext)

    assert ciphertext != plaintext
    assert decrypt_field(ciphertext) == plaintext


def test_encrypt_field_is_not_deterministic():
    """Fernet tokens embed a timestamp + random IV, so encrypting the same
    plaintext twice must not produce the same ciphertext (semantic security),
    unlike hash_value which must be deterministic for matching to work."""
    plaintext = "1234567890123456"

    assert encrypt_field(plaintext) != encrypt_field(plaintext)


def test_hash_value_is_deterministic_and_one_way():
    plaintext = "1234567890123456"

    digest = hash_value(plaintext)

    assert digest == hash_value(plaintext)  # deterministic, needed for matching
    assert digest != plaintext
    assert plaintext not in digest

    # a hash is not a Fernet token — there is no way back to the plaintext
    with pytest.raises(ValueError):
        decrypt_field(digest)


def test_decrypt_field_rejects_garbage_token():
    with pytest.raises(ValueError):
        decrypt_field("not-a-valid-fernet-token")
