"""Postgres counterpart to test_migrations_apply_cleanly.py (task 0.2: "run
alembic upgrade head against a clean SQLite and Postgres test DB"). The
SQLite tests in that file can't exercise Postgres-only migration paths (e.g.
`ALTER TYPE ... ADD VALUE`, used by 74b3becc9b81/bd5bd71257e0) at all --
SQLite has no native enum type, so those migrations are legitimate no-ops
there. This file is the real verification for that category.

Skips cleanly (not a failure) when no Postgres is reachable, since most dev/
CI environments won't have one configured -- this project's default/dev DB is
SQLite (app/config.py: sqlite+aiosqlite:///./app.db). Point
`POSTGRES_TEST_DATABASE_URL` at a disposable Postgres database to run this for
real, e.g.:
    postgresql+psycopg://postgres@localhost:5432/scanwick_migration_test
The target database must already exist and is freely dropped/recreated by
this test -- never point it at a database with real data.

Verified manually against a real local Postgres 18 instance while writing
this test: full upgrade head -> downgrade base -> upgrade head round trip,
including confirming 'generic_csv' actually lands in the `orderdatasource`
native Postgres ENUM type.
"""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

POSTGRES_TEST_DATABASE_URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")


def _sync_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)


def _postgres_available() -> bool:
    if not POSTGRES_TEST_DATABASE_URL:
        return False
    try:
        engine = create_engine(_sync_url(POSTGRES_TEST_DATABASE_URL))
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="POSTGRES_TEST_DATABASE_URL not set or not reachable -- set it to a disposable Postgres DB to run this",
)


def _alembic_config() -> Config:
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
    os.environ["ALEMBIC_DATABASE_URL_OVERRIDE"] = _sync_url(POSTGRES_TEST_DATABASE_URL)
    return cfg


def _reset_to_empty():
    """Drops every table so each test starts from a genuinely clean DB,
    without needing CREATE DATABASE/DROP DATABASE privileges (a plain schema
    reset is enough and works for any user with rights on the target DB)."""
    engine = create_engine(_sync_url(POSTGRES_TEST_DATABASE_URL))
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def _tables() -> set[str]:
    engine = create_engine(_sync_url(POSTGRES_TEST_DATABASE_URL))
    names = set(inspect(engine).get_table_names())
    engine.dispose()
    return names


def _enum_values(enum_name: str) -> list[str]:
    engine = create_engine(_sync_url(POSTGRES_TEST_DATABASE_URL))
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = CAST(:name AS regtype) ORDER BY enumsortorder"),
            {"name": enum_name},
        ).fetchall()
    engine.dispose()
    return [r[0] for r in rows]


def test_migrations_apply_and_revert_cleanly_on_real_postgres():
    _reset_to_empty()
    cfg = _alembic_config()

    try:
        command.upgrade(cfg, "head")
        tables_after_upgrade = _tables()
        assert "orders" in tables_after_upgrade
        assert "bank_transactions" in tables_after_upgrade
        assert "reconciliation_reports" in tables_after_upgrade
        assert "deals" not in tables_after_upgrade

        command.downgrade(cfg, "base")
        assert _tables() == {"alembic_version"}

        command.upgrade(cfg, "head")
        assert _tables() == tables_after_upgrade
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL_OVERRIDE", None)


def test_generic_csv_enum_value_lands_in_native_postgres_enum_types():
    """The one thing SQLite structurally cannot verify (task: Postgres
    migration verification requirement) -- confirms 74b3becc9b81 actually
    widens the real native ENUM type, not just a Python-side check."""
    _reset_to_empty()
    cfg = _alembic_config()

    try:
        command.upgrade(cfg, "head")
        assert "generic_csv" in _enum_values("orderdatasource")
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL_OVERRIDE", None)
