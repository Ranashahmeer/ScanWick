import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.accounts import Account
from app.services import bank_pdf_ingestion
from app.services.bank_pdf_ingestion import ingest_bank_pdf
from app.services.upload_staging import delete_staged_upload, stage_upload

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def staged_bank_pdf_upload(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/bank_pdf_task_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(bank_pdf_ingestion, "async_session", test_session)

    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, (FIXTURES_DIR / "generic_bank_statement.pdf").read_bytes(), "pdf")

    yield upload_id, test_session

    delete_staged_upload(upload_id)
    await engine.dispose()


def test_ingest_bank_pdf_task_called_directly(staged_bank_pdf_upload):
    upload_id, test_session = staged_bank_pdf_upload
    user_id = str(uuid.uuid4())

    result = ingest_bank_pdf(upload_id, user_id, bank_name="Access Bank")

    assert result["transactions_created"] == 5
    assert result["rows_rejected"] == 0

    import asyncio

    async def _check():
        async with test_session() as db:
            return (await db.execute(select(Account).where(Account.user_id == uuid.UUID(user_id)))).scalar_one()

    account = asyncio.run(_check())
    assert account.bank_name == "Access Bank"
