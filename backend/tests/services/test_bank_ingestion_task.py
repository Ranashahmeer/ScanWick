import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.concurrency import run_in_threadpool

from app.celery_app import celery_app
from app.models import Base
from app.models.accounts import Account
from app.models.uploads import Upload, UploadStatus
from app.services import bank_ingestion
from app.services.bank_ingestion import ingest_bank_csv
from app.services.upload_staging import delete_staged_upload, read_staged_csv, stage_upload

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def staged_bank_upload(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/bank_task_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(bank_ingestion, "async_session", test_session)

    upload_id = str(uuid.uuid4())
    stage_upload(upload_id, (FIXTURES_DIR / "generic_bank_sample.csv").read_bytes(), "csv")

    yield upload_id, test_session

    delete_staged_upload(upload_id)
    await engine.dispose()


def test_ingest_bank_csv_task_called_directly(staged_bank_upload):
    """Sync on purpose — same reasoning as the e-commerce/sales task tests:
    the task calls asyncio.run() internally, like a real Celery worker."""
    upload_id, test_session = staged_bank_upload
    user_id = str(uuid.uuid4())

    result = ingest_bank_csv(upload_id, user_id, bank_name="GTBank")

    assert result["transactions_created"] == 5
    assert result["rows_rejected"] == 0

    import asyncio

    async def _check():
        async with test_session() as db:
            return (await db.execute(select(Account).where(Account.user_id == uuid.UUID(user_id)))).scalar_one()

    account = asyncio.run(_check())
    assert account.bank_name == "GTBank"


async def test_delay_under_eager_mode_works_from_inside_a_running_event_loop(staged_bank_upload):
    """Regression test for a real footgun introduced by adding local-dev
    Celery eager mode (CELERY_TASK_ALWAYS_EAGER): with task_always_eager on,
    `.delay()` runs this task inline instead of publishing to Redis — and
    the task itself calls asyncio.run(...), which is only safe in a
    separate worker process/thread with no event loop of its own. Calling
    `.delay()` directly from an async route handler (which is already
    running inside uvicorn's event loop) would crash with "asyncio.run()
    cannot be called from a running event loop". The routes dispatch
    through `run_in_threadpool` specifically to avoid this — this test
    proves that actually works, using the real (unmocked) `.delay()` path,
    not the monkeypatched-away version every route test uses."""
    upload_id, test_session = staged_bank_upload
    user_id = str(uuid.uuid4())

    assert celery_app.conf.task_always_eager, "expected eager mode on for this test (dev_mode + default setting)"

    # This `await` is what proves it: the test itself is already running
    # inside pytest-asyncio's event loop, mirroring a real async route
    # handler. Without run_in_threadpool, this would raise.
    result = await run_in_threadpool(ingest_bank_csv.delay, upload_id, user_id, "GTBank")

    assert result.get()["transactions_created"] == 5

    async def _check():
        async with test_session() as db:
            return (await db.execute(select(Account).where(Account.user_id == uuid.UUID(user_id)))).scalar_one()

    account = await _check()
    assert account.bank_name == "GTBank"


def test_ingest_bank_csv_task_deletes_the_staged_file_on_success(staged_bank_upload):
    """Audit #16 regression: staged files were never cleaned up."""
    upload_id, _ = staged_bank_upload
    user_id = str(uuid.uuid4())

    ingest_bank_csv(upload_id, user_id, bank_name="GTBank")

    with pytest.raises(Exception):
        read_staged_csv(upload_id)


def test_ingest_bank_csv_task_marks_upload_failed_and_still_cleans_up_on_a_corrupt_file(
    staged_bank_upload, monkeypatch
):
    """Audit #13/#16 regression: an exception during ingestion must mark the
    Upload row `failed` with a real error message (never leave it stuck at
    `processing` forever) and still delete the staged file, not just on the
    success path."""
    upload_id, test_session = staged_bank_upload
    user_id = str(uuid.uuid4())

    def _boom(_df, *_args, **_kwargs):
        raise ValueError("simulated parse failure")

    monkeypatch.setattr(bank_ingestion, "extract_canonical_bank_rows", _boom)

    with pytest.raises(ValueError, match="simulated parse failure"):
        ingest_bank_csv(upload_id, user_id, bank_name="GTBank")

    with pytest.raises(Exception):
        read_staged_csv(upload_id)

    import asyncio

    async def _check():
        async with test_session() as db:
            return (await db.execute(select(Upload).where(Upload.id == uuid.UUID(upload_id)))).scalar_one()

    upload = asyncio.run(_check())
    assert upload.status == UploadStatus.failed
    assert "simulated parse failure" in upload.error_message
