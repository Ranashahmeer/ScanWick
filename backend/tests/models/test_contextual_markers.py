import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import StatementError

from app.models.contextual_markers import ContextualMarker
from app.models.reconciliation_reports import AnalyzerType


def _make_marker(**overrides) -> ContextualMarker:
    defaults = dict(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        analyzer_type=AnalyzerType.bank,
        label="Black Friday promo",
        start_date=date(2026, 11, 27),
        end_date=date(2026, 11, 30),
        created_by=uuid.uuid4(),
    )
    defaults.update(overrides)
    return ContextualMarker(**defaults)


async def test_create_and_read_contextual_marker(db_session):
    marker = _make_marker()
    db_session.add(marker)
    await db_session.commit()

    result = await db_session.execute(select(ContextualMarker).where(ContextualMarker.id == marker.id))
    fetched = result.scalar_one()

    assert fetched.analyzer_type == AnalyzerType.bank
    assert fetched.label == "Black Friday promo"
    assert fetched.start_date == date(2026, 11, 27)
    assert fetched.end_date == date(2026, 11, 30)
    assert fetched.created_at is not None


async def test_update_contextual_marker(db_session):
    marker = _make_marker()
    db_session.add(marker)
    await db_session.commit()

    marker.label = "Black Friday + Cyber Monday promo"
    marker.analyzer_type = AnalyzerType.ecommerce
    await db_session.commit()

    result = await db_session.execute(select(ContextualMarker).where(ContextualMarker.id == marker.id))
    fetched = result.scalar_one()
    assert fetched.label == "Black Friday + Cyber Monday promo"
    assert fetched.analyzer_type == AnalyzerType.ecommerce


async def test_delete_contextual_marker(db_session):
    marker = _make_marker()
    db_session.add(marker)
    await db_session.commit()

    await db_session.delete(marker)
    await db_session.commit()

    result = await db_session.execute(select(ContextualMarker).where(ContextualMarker.id == marker.id))
    assert result.scalar_one_or_none() is None


async def test_each_analyzer_type_enum_value_is_storable(db_session):
    for analyzer_type in AnalyzerType:
        db_session.add(_make_marker(id=uuid.uuid4(), analyzer_type=analyzer_type))
    await db_session.commit()

    result = await db_session.execute(select(ContextualMarker.analyzer_type))
    stored_types = {row[0] for row in result.all()}
    assert stored_types == set(AnalyzerType)


async def test_rejects_invalid_analyzer_type(db_session):
    marker = _make_marker(analyzer_type="not_a_real_type")
    db_session.add(marker)

    with pytest.raises(StatementError):
        await db_session.commit()
