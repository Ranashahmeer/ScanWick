import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.accounts import Account
from app.services import mono_ingestion
from app.services.mono_ingestion import ingest_mono_account_task

ACCOUNT_DETAILS = {
    "accountNumber": "1234567890",
    "currency": "NGN",
    "institution": {"name": "GTBank"},
}
TRANSACTIONS = [
    {"id": "t1", "date": "2026-01-01T00:00:00.000Z", "narration": "Opening Balance", "amount": 100000, "type": "credit", "balance": 100000},
]


@pytest.fixture
async def isolated_db(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/mono_task_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(mono_ingestion, "async_session", test_session)
    yield test_session
    await engine.dispose()


def test_ingest_mono_account_task_called_directly(isolated_db):
    """Sync on purpose — same reasoning as every other ingestion task test:
    the task calls asyncio.run() internally, like a real Celery worker."""
    user_id = str(uuid.uuid4())

    with (
        patch("app.services.mono_ingestion.fetch_account_details", new=AsyncMock(return_value=ACCOUNT_DETAILS)),
        patch("app.services.mono_ingestion.fetch_all_account_transactions", new=AsyncMock(return_value=TRANSACTIONS)),
    ):
        result = ingest_mono_account_task(user_id, "acc_ng_1")

    assert result["transactions_created"] == 1

    async def _check():
        async with isolated_db() as db:
            return (await db.execute(select(Account).where(Account.user_id == uuid.UUID(user_id)))).scalar_one()

    account = asyncio.run(_check())
    assert account.bank_name == "GTBank"
