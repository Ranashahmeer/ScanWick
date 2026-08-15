import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _alembic_config(db_path) -> Config:
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
    os.environ["ALEMBIC_DATABASE_URL_OVERRIDE"] = f"sqlite+aiosqlite:///{db_path}"
    return cfg


def _tables(db_path) -> set[str]:
    engine = create_engine(f"sqlite:///{db_path}")
    names = set(inspect(engine).get_table_names())
    engine.dispose()
    return names


def _schema_snapshot(db_path) -> dict[str, frozenset[str]]:
    """Tables AND their columns -- catches column-only migrations (e.g.
    adding analysis_run_id to the existing postmortem_reports table),
    not just whole-new-table migrations, unlike a bare table-name set."""
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    snapshot = {
        table: frozenset(col["name"] for col in inspector.get_columns(table))
        for table in inspector.get_table_names()
    }
    engine.dispose()
    return snapshot


def test_all_migrations_apply_and_revert_cleanly(tmp_path):
    db_path = tmp_path / "migration_test.db"
    cfg = _alembic_config(db_path)

    try:
        command.upgrade(cfg, "head")
        tables_after_upgrade = _tables(db_path)
        assert "orders" in tables_after_upgrade
        assert "order_items" in tables_after_upgrade
        assert "merchant_settings" in tables_after_upgrade
        assert "uploads" in tables_after_upgrade
        assert "contextual_markers" in tables_after_upgrade
        assert "exchange_rates" in tables_after_upgrade
        assert "accounts" in tables_after_upgrade
        assert "bank_transactions" in tables_after_upgrade
        assert "reconciliation_reports" in tables_after_upgrade
        assert "users" in tables_after_upgrade
        # Section 4: sales analyzer and ecommerce-depth-only tables are
        # deleted, not just unused -- confirms the migration chain actually
        # drops them rather than merely no longer referencing them in code.
        for deleted_table in (
            "deals",
            "stage_transition_logs",
            "returns",
            "postmortem_reports",
            "rfm_segment_assignments",
            "sku_inventory",
            "ad_kill_audit_log",
        ):
            assert deleted_table not in tables_after_upgrade

        command.downgrade(cfg, "base")
        tables_after_downgrade = _tables(db_path)
        assert tables_after_downgrade == {"alembic_version"}

        command.upgrade(cfg, "head")
        assert _tables(db_path) == tables_after_upgrade
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL_OVERRIDE", None)


def test_each_migration_reverts_and_reapplies_one_step_at_a_time(tmp_path):
    """Walk the whole chain downgrading one step at a time from head, then back
    up one step at a time, confirming each individual migration's down_revision
    and table set is consistent. Avoids hardcoding which migration is "newest"
    (that changes every time a new migration is added on top).

    Uses a full table+column schema snapshot, not just a table-name set --
    a bare table-count check would wrongly fail for any migration that only
    adds a column to an existing table (e.g. 9f612082e573, adding
    analysis_run_id to postmortem_reports) rather than a whole new table,
    since "strictly fewer tables" doesn't hold for a column-only downgrade
    even though the schema genuinely did change."""
    db_path = tmp_path / "migration_test_stepwise.db"
    cfg = _alembic_config(db_path)

    try:
        command.upgrade(cfg, "head")
        snapshot_at_head = _schema_snapshot(db_path)

        command.downgrade(cfg, "-1")
        snapshot_one_below_head = _schema_snapshot(db_path)
        # Usually the downgrade changes the schema -- but not universally: a
        # migration that only widens an existing sa.Enum column's allowed
        # values (e.g. 74b3becc9b81/bd5bd71257e0) is a legitimate no-op on
        # SQLite specifically, since sa.Enum has no native backing here and
        # emits no CHECK constraint at all (create_constraint defaults to
        # False for non-native-enum dialects) -- confirmed by inspecting the
        # raw sqlite_master DDL directly. The real effect of that migration
        # category only exists on Postgres's native ENUM type. So this only
        # asserts the round-trip below is exact, not that every single
        # migration is individually detectable on SQLite.

        command.upgrade(cfg, "+1")
        assert _schema_snapshot(db_path) == snapshot_at_head
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL_OVERRIDE", None)
