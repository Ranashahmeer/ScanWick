"""Task 5.4: every role with read access — across both verticals,
including the spec's undefined "Analyst" (treated as any granted role,
since none of this build's roles are write-only) — can read a
reconciliation report. Real `UserMerchantRole` rows, no bypass."""

import uuid

from app.models.auth import User
from app.models.reconciliation_reports import AnalyzerType, ReconciliationReport
from app.models.user_merchant_roles import BankRole, EcommerceRole, UserMerchantRole, Vertical
from tests.conftest import as_user


def _make_user(user_id: int) -> User:
    return User(id=user_id, email=f"user{user_id}@example.com", first_name="Test", last_name="User", is_verified=True)


async def _grant_role(db_session, user_id: int, merchant_id, vertical: Vertical, role: str) -> None:
    db_session.add(
        UserMerchantRole(id=uuid.uuid4(), user_id=user_id, merchant_id=merchant_id, vertical=vertical, role=role)
    )
    await db_session.commit()


async def _create_report(db_session, merchant_id, analyzer_type: AnalyzerType) -> ReconciliationReport:
    report = ReconciliationReport(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        analyzer_type=analyzer_type,
        base_currency="NGN",
        records_analyzed=100,
        records_excluded=3,
    )
    db_session.add(report)
    await db_session.commit()
    return report


async def _assert_role_can_read(rbac_client, db_session, user_id, vertical, analyzer_type, role):
    merchant_id = uuid.uuid4()
    report = await _create_report(db_session, merchant_id, analyzer_type)
    user = _make_user(user_id)
    await _grant_role(db_session, user.id, merchant_id, vertical, role)
    as_user(user)

    response = await rbac_client.get(f"/api/v1/reconciliation/{report.id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(report.id)


# ── Ecommerce: all 4 roles ──


async def test_ecommerce_owner_can_read_reconciliation(rbac_client, db_session):
    await _assert_role_can_read(
        rbac_client, db_session, 401, Vertical.ecommerce, AnalyzerType.ecommerce, EcommerceRole.owner.value
    )


async def test_ecommerce_admin_can_read_reconciliation(rbac_client, db_session):
    await _assert_role_can_read(
        rbac_client, db_session, 402, Vertical.ecommerce, AnalyzerType.ecommerce, EcommerceRole.admin.value
    )


async def test_ecommerce_manager_can_read_reconciliation(rbac_client, db_session):
    await _assert_role_can_read(
        rbac_client, db_session, 403, Vertical.ecommerce, AnalyzerType.ecommerce, EcommerceRole.manager.value
    )


async def test_ecommerce_viewer_can_read_reconciliation(rbac_client, db_session):
    """The "Analyst" role the task names — this build's equivalent is the
    lowest-privilege read-only role per vertical (Viewer here)."""
    await _assert_role_can_read(
        rbac_client, db_session, 404, Vertical.ecommerce, AnalyzerType.ecommerce, EcommerceRole.viewer.value
    )


# ── Bank: all 4 roles ──


async def test_bank_owner_can_read_reconciliation(rbac_client, db_session):
    await _assert_role_can_read(
        rbac_client, db_session, 409, Vertical.bank, AnalyzerType.bank, BankRole.bank_owner.value
    )


async def test_bank_admin_can_read_reconciliation(rbac_client, db_session):
    await _assert_role_can_read(
        rbac_client, db_session, 410, Vertical.bank, AnalyzerType.bank, BankRole.bank_admin.value
    )


async def test_loan_officer_can_read_reconciliation(rbac_client, db_session):
    """Even though Loan Officer gets redacted fraud-risk detail (5.3),
    reconciliation reports carry no transaction-level detail at all — full
    read access here is unaffected by that restriction."""
    await _assert_role_can_read(
        rbac_client, db_session, 411, Vertical.bank, AnalyzerType.bank, BankRole.loan_officer.value
    )


async def test_bank_viewer_can_read_reconciliation(rbac_client, db_session):
    await _assert_role_can_read(
        rbac_client, db_session, 412, Vertical.bank, AnalyzerType.bank, BankRole.bank_viewer.value
    )


# ── Denial case: no role at all for this report's merchant/vertical ──


async def test_user_with_no_role_cannot_read_reconciliation(rbac_client, db_session):
    merchant_id = uuid.uuid4()
    report = await _create_report(db_session, merchant_id, AnalyzerType.ecommerce)
    user = _make_user(413)
    as_user(user)  # no UserMerchantRole row granted at all

    response = await rbac_client.get(f"/api/v1/reconciliation/{report.id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
