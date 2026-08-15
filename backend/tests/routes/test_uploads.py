import datetime
import uuid

import pytest
from sqlalchemy import select

from app.models.auth import User
from app.models.reconciliation_reports import AnalyzerType
from app.models.uploads import Upload, UploadStatus
from app.models.user_merchant_roles import EcommerceRole, UserMerchantRole, Vertical
from app.services.upload_staging import read_staged_csv
from tests.conftest import as_user


async def _create_upload(db_session, **overrides) -> Upload:
    defaults = dict(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        analyzer_type=AnalyzerType.ecommerce,
        data_source="shopify_csv",
        status=UploadStatus.ready,
        rows_parsed=1847,
        rows_rejected=12,
        date_range_start=datetime.date(2026, 1, 1),
        date_range_end=datetime.date(2026, 5, 31),
        days_of_history=151,
        warnings=[
            {
                "field": "cogs",
                "severity": "high",
                "message": "COGS is missing for 420 of 1847 line items (22.7%).",
                "features_disabled": ["unit_margin", "profit_leak_detector"],
            }
        ],
    )
    defaults.update(overrides)
    upload = Upload(**defaults)
    db_session.add(upload)
    await db_session.commit()
    return upload


async def test_get_quality_report_found(client, db_session):
    upload = await _create_upload(db_session)

    response = await client.get(f"/api/v1/upload/{upload.id}/quality-report")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ready"
    assert body["data"]["rows_parsed"] == 1847
    assert body["data"]["rows_rejected"] == 12
    assert body["data"]["date_range"] == {"start": "2026-01-01", "end": "2026-05-31"}
    assert body["data"]["days_of_history"] == 151
    assert len(body["data"]["warnings"]) == 1
    assert body["data"]["warnings"][0]["field"] == "cogs"


async def test_get_quality_report_with_no_warnings(client, db_session):
    upload = await _create_upload(db_session, warnings=[])

    response = await client.get(f"/api/v1/upload/{upload.id}/quality-report")

    assert response.status_code == 200
    assert response.json()["data"]["warnings"] == []


async def test_get_quality_report_not_found(client, db_session):
    missing_id = uuid.uuid4()

    response = await client.get(f"/api/v1/upload/{missing_id}/quality-report")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UPLOAD_NOT_FOUND"


async def test_get_quality_report_invalid_id_format(client, db_session):
    response = await client.get("/api/v1/upload/not-a-uuid/quality-report")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_UPLOAD_ID"


async def test_get_quality_report_denied_for_user_without_a_role(db_session, rbac_client):
    """This route previously had no auth at all — locking that down is the
    point of this test, not just the found/not-found shape above."""
    upload = await _create_upload(db_session)

    outsider = User(id=999, email="outsider@example.com", first_name="Out", last_name="Sider", is_verified=True)
    as_user(outsider)

    response = await rbac_client.get(f"/api/v1/upload/{upload.id}/quality-report")

    assert response.status_code == 403


async def test_get_quality_report_allowed_for_user_with_a_role(db_session, rbac_client):
    upload = await _create_upload(db_session)

    viewer = User(id=42, email="viewer@example.com", first_name="View", last_name="Er", is_verified=True)
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(),
            user_id=viewer.id,
            merchant_id=upload.merchant_id,
            vertical=Vertical.ecommerce,
            role=EcommerceRole.viewer.value,
        )
    )
    await db_session.commit()
    as_user(viewer)

    response = await rbac_client.get(f"/api/v1/upload/{upload.id}/quality-report")

    assert response.status_code == 200
    assert response.json()["data"]["rows_parsed"] == 1847


async def _grant_ecommerce_ingest_role(db_session, user: User, merchant_id) -> None:
    db_session.add(
        UserMerchantRole(
            id=uuid.uuid4(),
            user_id=user.id,
            merchant_id=merchant_id,
            vertical=Vertical.ecommerce,
            role=EcommerceRole.owner.value,
        )
    )
    await db_session.commit()


async def test_upload_csv_rejects_a_non_csv_file_even_with_a_generic_content_type(db_session, rbac_client):
    """Audit #17 regression: content_type alone used to be sufficient —
    'application/octet-stream' was in the allowed set, so a non-CSV file
    mislabeled with that content-type sailed straight through regardless of
    its actual filename/extension."""
    merchant_id = uuid.uuid4()
    owner = User(id=501, email="owner@example.com", first_name="Owner", last_name="User", is_verified=True)
    await _grant_ecommerce_ingest_role(db_session, owner, merchant_id)
    as_user(owner)

    response = await rbac_client.post(
        "/api/v1/upload/csv",
        data={"analyzer_type": "ecommerce", "merchant_id": str(merchant_id), "source": "shopify_csv"},
        files={"file": ("payload.exe", b"not really a csv", "application/octet-stream")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_upload_csv_marks_upload_failed_and_cleans_up_when_dispatch_raises(
    db_session, rbac_client, monkeypatch
):
    """Audit #15 regression: if the Celery broker is unreachable at the
    exact moment `.delay()` is called, the Upload row and staged file used
    to already be committed/written — orphaned in `processing` forever
    with a bare 500 to the caller. Must now mark the row `failed` and clean
    up the staged file, not just crash."""
    import app.routes.uploads as uploads_module

    def _raise(*_args, **_kwargs):
        raise RuntimeError("broker unreachable")

    monkeypatch.setattr(uploads_module.ingest_ecommerce_csv, "delay", _raise)

    merchant_id = uuid.uuid4()
    owner = User(id=502, email="owner2@example.com", first_name="Owner", last_name="User", is_verified=True)
    await _grant_ecommerce_ingest_role(db_session, owner, merchant_id)
    as_user(owner)

    response = await rbac_client.post(
        "/api/v1/upload/csv",
        data={"analyzer_type": "ecommerce", "merchant_id": str(merchant_id), "source": "shopify_csv"},
        files={"file": ("orders.csv", b"order_id,gross_revenue\n1,100\n", "text/csv")},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DISPATCH_FAILED"

    uploads = (
        (await db_session.execute(select(Upload).where(Upload.merchant_id == merchant_id))).scalars().all()
    )
    assert len(uploads) == 1
    assert uploads[0].status == UploadStatus.failed
    assert "broker unreachable" in uploads[0].error_message

    with pytest.raises(Exception):
        read_staged_csv(str(uploads[0].id))
