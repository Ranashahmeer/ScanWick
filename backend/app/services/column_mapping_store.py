"""DB-touching persistence for ColumnMapping -- kept separate from
column_mapping.py so that module stays a pure, easily-unit-tested function
library with no database dependency."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.column_mappings import ColumnMapping
from app.models.reconciliation_reports import AnalyzerType


async def get_saved_mapping(
    db: AsyncSession, merchant_id: uuid.UUID, analyzer_type: AnalyzerType, source_signature: str
) -> Optional[ColumnMapping]:
    """Zero-touch reuse: a merchant's previously-confirmed (or previously
    auto-applied) mapping for this exact header shape."""
    return (
        await db.execute(
            select(ColumnMapping).where(
                ColumnMapping.merchant_id == merchant_id,
                ColumnMapping.analyzer_type == analyzer_type,
                ColumnMapping.source_signature == source_signature,
            )
        )
    ).scalar_one_or_none()


async def upsert_mapping(
    db: AsyncSession,
    *,
    merchant_id: uuid.UUID,
    analyzer_type: AnalyzerType,
    source_signature: str,
    mapping: dict,
    unmapped_headers: list,
    value_rules: dict,
    confirmed_by: Optional[int],
    confidence_summary: dict,
) -> ColumnMapping:
    """Upsert on the (merchant_id, analyzer_type, source_signature) unique
    constraint -- not check-then-insert, to avoid a race between two
    near-simultaneous uploads of the same header shape creating ambiguous
    duplicate rows. Postgres-specific (this app's only production backend;
    SQLite/dev falls back to check-then-insert, acceptable there since dev
    is single-process)."""
    if db.bind.dialect.name == "postgresql":
        stmt = pg_insert(ColumnMapping).values(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            analyzer_type=analyzer_type,
            source_signature=source_signature,
            mapping=mapping,
            unmapped_headers=unmapped_headers,
            value_rules=value_rules,
            confirmed_by=confirmed_by,
            confidence_summary=confidence_summary,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_column_mapping_signature",
            set_={
                "mapping": mapping,
                "unmapped_headers": unmapped_headers,
                "value_rules": value_rules,
                "confirmed_by": confirmed_by,
                "confidence_summary": confidence_summary,
            },
        ).returning(ColumnMapping.id)
        result = await db.execute(stmt)
        await db.commit()
        mapping_id = result.scalar_one()
        return await db.get(ColumnMapping, mapping_id)

    existing = await get_saved_mapping(db, merchant_id, analyzer_type, source_signature)
    if existing is not None:
        existing.mapping = mapping
        existing.unmapped_headers = unmapped_headers
        existing.value_rules = value_rules
        existing.confirmed_by = confirmed_by
        existing.confidence_summary = confidence_summary
    else:
        existing = ColumnMapping(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            analyzer_type=analyzer_type,
            source_signature=source_signature,
            mapping=mapping,
            unmapped_headers=unmapped_headers,
            value_rules=value_rules,
            confirmed_by=confirmed_by,
            confidence_summary=confidence_summary,
        )
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing
