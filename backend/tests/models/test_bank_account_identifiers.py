from sqlalchemy import select

from app.models.bank_account_identifiers import BankAccountIdentifier


def _make_identifier(**overrides) -> BankAccountIdentifier:
    defaults = dict(
        user_id=1,
        account_number_hash="a" * 64,
        account_number_encrypted="gAAAAA-fake-fernet-token",
    )
    defaults.update(overrides)
    return BankAccountIdentifier(**defaults)


async def test_create_and_read_bank_account_identifier(db_session):
    identifier = _make_identifier()
    db_session.add(identifier)
    await db_session.commit()

    result = await db_session.execute(
        select(BankAccountIdentifier).where(BankAccountIdentifier.id == identifier.id)
    )
    fetched = result.scalar_one()

    assert fetched.user_id == 1
    assert fetched.account_number_hash == "a" * 64
    assert fetched.account_number_encrypted == "gAAAAA-fake-fernet-token"
    assert fetched.created_at is not None


async def test_update_bank_account_identifier(db_session):
    identifier = _make_identifier()
    db_session.add(identifier)
    await db_session.commit()

    identifier.account_number_encrypted = "gAAAAA-rotated-token"
    await db_session.commit()

    result = await db_session.execute(
        select(BankAccountIdentifier).where(BankAccountIdentifier.id == identifier.id)
    )
    assert result.scalar_one().account_number_encrypted == "gAAAAA-rotated-token"


async def test_delete_bank_account_identifier(db_session):
    identifier = _make_identifier()
    db_session.add(identifier)
    await db_session.commit()

    await db_session.delete(identifier)
    await db_session.commit()

    result = await db_session.execute(
        select(BankAccountIdentifier).where(BankAccountIdentifier.id == identifier.id)
    )
    assert result.scalar_one_or_none() is None


async def test_unique_constraint_on_user_and_hash(db_session):
    db_session.add(_make_identifier())
    await db_session.commit()

    db_session.add(_make_identifier())
    try:
        await db_session.commit()
        assert False, "expected a uniqueness violation on (user_id, account_number_hash)"
    except Exception:
        await db_session.rollback()
