import uuid

from app.models.reconciliation_reports import AnalyzerType, ReconciliationReport


async def _create_report(db_session, **overrides) -> ReconciliationReport:
    defaults = dict(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        analyzer_type=AnalyzerType.ecommerce,
        base_currency="NGN",
        records_analyzed=100,
        records_excluded=3,
        exclusion_detail=[{"record_id": "rec_1", "reason": "is_anomalous", "field": "order_date"}],
        disabled_features=[{"feature_name": "unit_margin", "reason": "COGS missing", "data_needed": "cogs"}],
        contextual_markers_applied=["marker_1"],
    )
    defaults.update(overrides)
    report = ReconciliationReport(**defaults)
    db_session.add(report)
    await db_session.commit()
    return report


async def test_get_reconciliation_report_found(client, db_session):
    report = await _create_report(db_session)

    response = await client.get(f"/api/v1/reconciliation/{report.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == str(report.id)
    assert body["data"]["analyzer_type"] == "ecommerce"
    assert body["data"]["records_analyzed"] == 100
    assert body["data"]["disabled_features"] == [
        {"feature_name": "unit_margin", "reason": "COGS missing", "data_needed": "cogs"}
    ]
    assert body["meta"]["analysis_run_id"] == str(report.id)


async def test_get_reconciliation_report_not_found(client, db_session):
    missing_id = uuid.uuid4()

    response = await client.get(f"/api/v1/reconciliation/{missing_id}")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RECONCILIATION_NOT_FOUND"


async def test_get_reconciliation_report_invalid_id_format(client, db_session):
    response = await client.get("/api/v1/reconciliation/not-a-uuid")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_ANALYSIS_RUN_ID"
