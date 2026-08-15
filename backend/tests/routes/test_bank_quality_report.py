"""Route tests for task 1.26: GET /api/v1/bank/upload/{upload_id}/quality-report.
Uses the `client` fixture (RBAC-bypassed) for shape/found/not-found cases, and
`rbac_client`/`as_user()` (real UserMerchantRole rows, no bypass) for the
access-denied case -- same split test_bank_rbac.py already uses."""

import uuid
from datetime import date

from app.models.auth import User
from app.models.reconciliation_reports import AnalyzerType
from app.models.uploads import Upload, UploadStatus
from app.models.user_merchant_roles import BankRole, UserMerchantRole, Vertical
from tests.conftest import as_user


def _make_user(user_id: int) -> User:
    # premium: this endpoint is gated on platform.data_quality_report
    # (Free/Basic/Premium all FULL) — set explicitly since an unpersisted
    # User() leaves subscription_tier as None, which fails closed.
    return User(
        id=user_id, email=f"user{user_id}@example.com", first_name="Test", last_name="User", is_verified=True,
        subscription_tier="premium",
    )


async def _make_bank_upload(db_session, merchant_id) -> Upload:
    upload = Upload(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        analyzer_type=AnalyzerType.bank,
        data_source="generic_csv",
        status=UploadStatus.ready,
        rows_parsed=5,
        rows_rejected=1,
        date_range_start=date(2026, 1, 1),
        date_range_end=date(2026, 1, 20),
        days_of_history=20,
        warnings=[{"field": "transaction_date/amount", "severity": "medium", "message": "1 row rejected.", "features_disabled": []}],
        analyzer_metadata={
            "months_of_data": 1,
            "balance_integrity": {
                "opening_balance": 1000000.0,
                "closing_balance": 3164500.0,
                "computed_closing_balance": 3164500.0,
                "balance_integrity_passed": True,
                "balance_discrepancy": None,
            },
            "date_gaps": [],
            "rejected_rows": [
                {
                    "row": 2,
                    "field": "transaction_date",
                    "code": "AMBIGUOUS_DATE",
                    "message": "'03/04/2026' is ambiguous.",
                    "raw_value": "03/04/2026",
                    "remediation": "Confirm a date_locale for this mapping and re-upload.",
                }
            ],
        },
    )
    db_session.add(upload)
    await db_session.commit()
    return upload


async def test_get_bank_quality_report_found_matches_spec_shape(client, db_session):
    merchant_id = uuid.uuid4()
    upload = await _make_bank_upload(db_session, merchant_id)

    response = await client.get(f"/api/v1/bank/upload/{upload.id}/quality-report")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["transactions_parsed"] == 5
    assert data["date_range"] == {"start": "2026-01-01", "end": "2026-01-20"}
    assert data["months_of_data"] == 1
    assert data["balance_integrity"]["balance_integrity_passed"] is True
    assert data["date_gaps"] == []
    assert len(data["warnings"]) == 1
    assert data["rejected_rows"][0]["code"] == "AMBIGUOUS_DATE"


async def test_get_bank_quality_report_not_found_for_unknown_upload_id(client):
    response = await client.get(f"/api/v1/bank/upload/{uuid.uuid4()}/quality-report")

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_get_bank_quality_report_invalid_upload_id_returns_400(client):
    response = await client.get("/api/v1/bank/upload/not-a-uuid/quality-report")

    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_get_bank_quality_report_404s_for_non_bank_upload(client, db_session):
    """This route is bank-namespaced -- an ecommerce/sales upload_id must not
    leak through it, even though the row technically exists in the shared
    uploads table."""
    merchant_id = uuid.uuid4()
    upload = Upload(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        analyzer_type=AnalyzerType.ecommerce,
        status=UploadStatus.ready,
        rows_parsed=10,
        rows_rejected=0,
    )
    db_session.add(upload)
    await db_session.commit()

    response = await client.get(f"/api/v1/bank/upload/{upload.id}/quality-report")

    assert response.status_code == 404


async def test_get_bank_quality_report_denied_for_user_without_a_role(db_session, rbac_client):
    merchant_id = uuid.uuid4()
    upload = await _make_bank_upload(db_session, merchant_id)

    outsider = _make_user(999)
    as_user(outsider)

    response = await rbac_client.get(f"/api/v1/bank/upload/{upload.id}/quality-report")

    assert response.status_code == 403
    assert response.json()["success"] is False


async def test_get_bank_quality_report_allowed_for_user_with_bank_viewer_role(db_session, rbac_client):
    merchant_id = uuid.uuid4()
    upload = await _make_bank_upload(db_session, merchant_id)

    viewer = _make_user(42)
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(), user_id=viewer.id, merchant_id=merchant_id, vertical=Vertical.bank, role="bank_viewer"
        )
    )
    await db_session.commit()
    as_user(viewer)

    response = await rbac_client.get(f"/api/v1/bank/upload/{upload.id}/quality-report")

    assert response.status_code == 200
    assert response.json()["data"]["transactions_parsed"] == 5
    assert response.json()["data"]["rejected_rows"][0]["code"] == "AMBIGUOUS_DATE"


async def test_get_bank_quality_report_hides_rejected_rows_detail_for_loan_officer(db_session, rbac_client):
    """3.4/3.7: rejected_rows carries raw source values and row-level
    detail -- import/diagnostic depth beyond a Loan Officer's brief-only
    scope, so it's dropped entirely for that role."""
    merchant_id = uuid.uuid4()
    upload = await _make_bank_upload(db_session, merchant_id)

    officer = _make_user(45)
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(), user_id=officer.id, merchant_id=merchant_id, vertical=Vertical.bank, role=BankRole.loan_officer.value
        )
    )
    await db_session.commit()
    as_user(officer)

    response = await rbac_client.get(f"/api/v1/bank/upload/{upload.id}/quality-report")

    assert response.status_code == 200
    assert response.json()["data"]["rejected_rows"] == []


async def test_get_bank_quality_report_redacts_balance_amounts_for_loan_officer(db_session, rbac_client):
    """3.4: Loan Officer may see the quality report (they need to judge
    statement trustworthiness for the brief-only endpoints), but
    `balance_integrity`'s opening/closing/discrepancy figures and the
    matching warning's embedded discrepancy amount are real amounts and
    must be withheld -- only the pass/fail signal survives."""
    merchant_id = uuid.uuid4()
    upload = Upload(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        analyzer_type=AnalyzerType.bank,
        data_source="generic_csv",
        status=UploadStatus.ready,
        rows_parsed=5,
        rows_rejected=0,
        date_range_start=date(2026, 1, 1),
        date_range_end=date(2026, 1, 20),
        days_of_history=20,
        warnings=[
            {
                "field": "balance_integrity",
                "severity": "high",
                "message": "Opening balance + credits - debits does not reconcile (discrepancy: 4500.00).",
                "features_disabled": [],
            }
        ],
        analyzer_metadata={
            "months_of_data": 1,
            "balance_integrity": {
                "opening_balance": 1000000.0,
                "closing_balance": 3164500.0,
                "computed_closing_balance": 3160000.0,
                "balance_integrity_passed": False,
                "balance_discrepancy": 4500.0,
            },
            "date_gaps": [],
        },
    )
    db_session.add(upload)
    await db_session.commit()

    officer = User(id=44, email="officer2@example.com", first_name="Loan", last_name="Officer", is_verified=True, subscription_tier="premium")
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(), user_id=officer.id, merchant_id=merchant_id, vertical=Vertical.bank, role=BankRole.loan_officer.value
        )
    )
    await db_session.commit()
    as_user(officer)

    response = await rbac_client.get(f"/api/v1/bank/upload/{upload.id}/quality-report")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["balance_integrity"] == {"balance_integrity_passed": False}
    assert "4500" not in data["warnings"][0]["message"]
    assert "1000000" not in str(data)
    assert "3164500" not in str(data)
