from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# ── Database URL Selection ────────────────────────────────────────────────────
# LOCAL  (DEV_MODE=true,  USE_REMOTE_DB_IN_DEV=false): SQLite at ./app.db
# LOCAL  (DEV_MODE=true,  USE_REMOTE_DB_IN_DEV=true):  Railway PostgreSQL via DATABASE_URL
# PROD   (DEV_MODE=false):                              DATABASE_URL (Railway injects it)
#
# To switch local ↔ production: only change DEV_MODE in .env — no code changes needed.
# ─────────────────────────────────────────────────────────────────────────────

if settings.dev_mode and not settings.use_remote_db_in_dev:
    database_url = settings.local_database_url  # sqlite+aiosqlite:///./app.db
else:
    # Outside of local dev (dev_mode=False), never silently fall back to the
    # SQLite default — a missing/misnamed DATABASE_URL env var must fail
    # loudly at startup, not route production traffic to a throwaway local
    # file. `database_url`'s pydantic field default is the sqlite fallback,
    # so we can't distinguish "explicitly set to sqlite" from "never set"
    # via the field alone — require it to come from the environment instead.
    import os

    raw_database_url = os.environ.get("DATABASE_URL")
    if not raw_database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Refusing to start with dev_mode=False "
            "and no DATABASE_URL — this would otherwise silently fall back "
            "to a local SQLite database in production."
        )
    database_url = raw_database_url
    # Normalize Railway's postgres:// to the async driver format
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# FP-D3: without pool_pre_ping, a connection Railway (or any host that
# drops idle connections) has silently closed behind our back surfaces as
# a hard failure on the next request that happens to draw it from the
# pool, rather than being detected and transparently replaced. pool_size/
# max_overflow are Postgres-only (QueuePool) tuning -- SQLite's own pool
# class doesn't accept them, and dev/test only ever use SQLite here.
_pool_kwargs = {"pool_pre_ping": True, "pool_recycle": 1800}
if not database_url.startswith("sqlite"):
    _pool_kwargs.update(pool_size=10, max_overflow=20)

engine = create_async_engine(database_url, echo=settings.dev_mode, **_pool_kwargs)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
