import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.accounts import Account
from app.models.auth import User
from app.models.bank_transactions import BankTransaction
from app.models.reconciliation_reports import AnalyzerType
from app.models.uploads import Upload, UploadStatus
from app.models.user_merchant_roles import BankRole, Vertical
from app.schemas.envelope import error_response, success_response
from app.services.bank_abm import get_abm_response
from app.services.bank_account_integrity import detect_own_account_transfers
from app.services.bank_cashflow import eligible_transactions
from app.services.bank_cashflow_analysis import compute_cashflow_analysis
from app.services.bank_cashflow_forecast import compute_cashflow_forecast
from app.services.bank_dashboard import compute_dashboard_summary
from app.services.bank_fraud_risk import compute_fraud_risk, redact_flags_for_loan_officer
from app.services.bank_income_stability import get_income_stability_response
from app.services.bank_lender_brief import get_lender_brief_response
from app.services.bank_loan_readiness import compute_loan_readiness
from app.services.bank_pdf_ingestion import ingest_bank_pdf
from app.services.upload_staging import delete_staged_upload, mark_upload_failed, stage_upload
from app.services.bank_playbook import get_financial_health_playbook_response
from app.services.entitlements import check_feature_access
from app.services.merchant_dependencies import require_account_role, require_merchant_role
from app.services.mono_client import MonoAPIError
from app.services.mono_ingestion import ingest_mono_account
from app.services.plan_permissions import AccessLevel
from app.services.rbac import check_role
from app.services.reconciliation import record_analysis_run

logger = logging.getLogger(__name__)

# Uploading a statement is a batch write, not a read — tighter than
# READ_ROLES (loan_officer/bank_viewer can view dashboards but shouldn't be
# the ones feeding new statements in).
INGEST_ROLES = {BankRole.bank_owner.value, BankRole.bank_admin.value}
_MAX_PDF_BYTES = 15 * 1024 * 1024  # 15 MB — scanned statements run larger than CSV exports


class MonoIngestRequest(BaseModel):
    merchant_id: str
    mono_account_id: str

# Access table (RBAC — Bank, task 5.3 / 3.4): explicit policy sets for each
# class of endpoint. Loan Officers get brief/aggregate views ONLY — never
# transaction-level diagnostics, payee data, descriptions, raw amounts, or
# account-detail endpoints. Bank Viewer remains in the full-data group for
# backward-compatible dashboard/diagnostic access.
FULL_DATA_ROLES = {
    BankRole.bank_owner.value,
    BankRole.bank_admin.value,
    BankRole.bank_viewer.value,
}
DIAGNOSTIC_ROLES = FULL_DATA_ROLES
# Endpoints that are brief/aggregate BY CONSTRUCTION (fraud-risk redacts its
# flags for non-FULL_DATA roles; loan-readiness never propagates raw flags;
# the lender brief never renders payee/transaction detail) — the one group a
# Loan Officer belongs to. Endpoints that expose payee names or real balance
# figures (dashboard/summary, accounts, quality-report) must NOT use this set
# without their own per-loan-officer redaction — see `_shape_accounts`/
# `_shape_quality_report` below.
BRIEF_ONLY_ROLES = FULL_DATA_ROLES | {BankRole.loan_officer.value}
# Summary/read access for non-transaction-detail Bank endpoints whose
# response is redacted per-role before being returned (accounts,
# quality-report) rather than being blanket-allowed.
READ_ROLES = BRIEF_ONLY_ROLES
# Fraud-risk's `flags` carry transaction_id/amount/description -- narrower
# than FULL_DATA_ROLES (which also covers dashboard/diagnostic access for
# Bank Viewer): only Owner/Admin get the raw flags. Bank Viewer and Loan
# Officer both get `redact_flags_for_loan_officer`'s aggregate-only shape.
FRAUD_FULL_DETAIL_ROLES = {
    BankRole.bank_owner.value,
    BankRole.bank_admin.value,
}

router = APIRouter(prefix="/api/v1/bank", tags=["bank"])


def _shape_fraud_risk(data: dict, access) -> dict:
    """bank.fraud_risk is LIMITED at Basic (statement_integrity only — no
    fraud score/flags) and FULL at Premium. Free never reaches here at all
    (check_feature_access already 403s it)."""
    if access.level != AccessLevel.LIMITED:
        return data
    return {"statement_integrity": data["statement_integrity"]}


def _shape_accounts(accounts: list[Account], role_row) -> list[dict]:
    """3.4: `/accounts` is the one BRIEF_ONLY_ROLES endpoint a Loan Officer
    must reach (to obtain an account_id for the brief/loan-readiness
    endpoints), but its full shape includes `bank_name` and
    `closing_balance` — account-detail and a real amount, both explicitly
    off-limits for that role. Loan Officer gets only what's needed to
    identify and select an account; every other role keeps the full shape."""
    is_loan_officer = role_row.role == BankRole.loan_officer.value
    result = []
    for account in accounts:
        row = {
            "id": str(account.id),
            "statement_period_start": account.statement_period_start.isoformat()
            if account.statement_period_start
            else None,
            "statement_period_end": account.statement_period_end.isoformat()
            if account.statement_period_end
            else None,
        }
        if not is_loan_officer:
            row["bank_name"] = account.bank_name
            row["base_currency"] = account.base_currency
            row["closing_balance"] = str(account.closing_balance) if account.closing_balance is not None else None
        result.append(row)
    return result


def _shape_quality_report(data: dict, role_row) -> dict:
    """3.4: the quality report's `balance_integrity` carries real
    opening/closing-balance and discrepancy amounts, and its `warnings`
    messages embed the discrepancy figure as free text — both are "amounts"
    a Loan Officer must not receive. Keeps the pass/fail signal (needed to
    judge statement trustworthiness) while dropping the figures themselves.
    3.7's `rejected_rows` is row-level import/diagnostic detail (raw source
    values, per-row references) rather than a brief-level summary, so it is
    dropped entirely for this role -- the aggregate `warnings` entries
    already carry the reject counts."""
    if role_row.role != BankRole.loan_officer.value:
        return data
    integrity = data.get("balance_integrity") or {}
    redacted_integrity = {"balance_integrity_passed": integrity.get("balance_integrity_passed")}
    redacted_warnings = [
        {**w, "message": "Balance integrity check failed for this statement (amount withheld for this role)."}
        if w.get("field") == "balance_integrity"
        else w
        for w in data.get("warnings", [])
    ]
    return {**data, "balance_integrity": redacted_integrity, "warnings": redacted_warnings, "rejected_rows": []}


def _shape_loan_readiness(data: dict, access) -> dict:
    """bank.loan_readiness is the one three-way tiered row in the whole
    matrix: Free sees the letter grade only, Basic sees score+grade+tier
    (no breakdown/plan), Premium sees everything. Distinguished by
    `access.detail` rather than a fourth AccessLevel, since it's still just
    "how much of this LIMITED response do you get.\""""
    if access.level != AccessLevel.LIMITED:
        return data
    if access.detail and access.detail.startswith("Grade only"):
        return {"creditworthiness_tier": data["creditworthiness_tier"]}
    return {
        "loan_readiness_score": data["loan_readiness_score"],
        "creditworthiness_tier": data["creditworthiness_tier"],
        "tier_definition": data["tier_definition"],
    }


@router.get("/accounts")
async def list_accounts(
    merchant_ctx=Depends(require_merchant_role(Vertical.bank, BRIEF_ONLY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Every other endpoint in this file takes an account_id, but nothing
    anywhere lets a caller discover one — Account.id is only ever surfaced
    once, synchronously, from the Mono ingestion response; the PDF/CSV
    ingestion paths are 202-Accepted + Celery, and neither the immediate
    response nor the quality-report endpoint ever exposes the account_id
    the task ends up creating. Added so the frontend has any way at all to
    list — and let a user pick between — the accounts already ingested for
    their merchant, regardless of which ingestion path created them.

    3.9: RBAC (`require_merchant_role`) resolves and validates merchant_id
    as a dependency, before this body runs at all — see
    `merchant_dependencies.py`."""
    error, merchant_uuid, role_row = merchant_ctx
    if error is not None:
        return error

    accounts = (
        (await db.execute(select(Account).where(Account.user_id == merchant_uuid))).scalars().all()
    )
    return success_response(_shape_accounts(accounts, role_row))


# Task 5.4 / audit #21: `detect_own_account_transfers` (bank_account_integrity.py)
# was fully built and tested but never called from any real request path —
# `is_own_account_transfer` was always False in production, so every
# dashboard/cashflow/fraud/loan-readiness/lender-brief figure double-counted
# genuine same-merchant transfers between their own accounts as both an
# inflow and an outflow. Process-local memoization cache: keyed by user_id,
# storing the transaction count across that user's accounts as of the last
# scan. A mismatch (new statement ingested since) forces a rescan; an
# unchanged count skips the O(n^2) scan + commit entirely. Worst case in a
# multi-replica deployment is an extra rescan on a cache miss on a different
# replica -- never a *missed* scan, so this can only cost a bit of redundant
# work, never correctness, matching the "idempotent, not just fast" bar
# `detect_own_account_transfers` itself already meets by construction
# (already-flagged rows are excluded from its matching pool).
_transfer_scan_cache: dict[UUID, int] = {}


async def _ensure_own_account_transfers_detected(db: AsyncSession, user_id) -> None:
    """Runs the own-account-transfer scan across every account this user
    owns, before that user's transactions are loaded for any analysis --
    the whole point being that `is_own_account_transfer` is correct by the
    time `eligible_transactions()` filters on it downstream. A no-op (fast,
    single COUNT query) once a user's transaction count hasn't changed since
    the last scan; `detect_own_account_transfers` itself already no-ops
    for single-account users."""
    total = (
        await db.execute(
            select(func.count())
            .select_from(BankTransaction)
            .join(Account, Account.id == BankTransaction.account_id)
            .where(Account.user_id == user_id)
        )
    ).scalar_one()

    if _transfer_scan_cache.get(user_id) == total:
        return

    await detect_own_account_transfers(db, user_id)
    _transfer_scan_cache[user_id] = total


async def _load_transactions(db: AsyncSession, account: Account) -> list[BankTransaction]:
    """Shared by every account-scoped bank endpoint, called AFTER the
    caller is already known to be authorized for this account's owning
    merchant (3.9: see `require_account_role` in `merchant_dependencies.py`,
    which resolves/validates the account + role as a route dependency
    before any handler body runs). Runs the own-account-transfer scan for
    this account's owner (see `_ensure_own_account_transfers_detected` --
    this is the integration point for audit #21) — a WRITE, so it must
    never run before authorization — and loads this account's transactions
    excluding is_anomalous=TRUE (Part 1's "filter out before training"
    principle, extended to predictive models the same way 1.18 extended it
    to sales' data-quality-cost). Transactions are ordered by
    (transaction_date, id) -- a deterministic tiebreaker for same-day rows,
    since the DB gives no other guarantee of same-day ordering and
    `_statement_integrity`'s sequential-ordering check (bank_fraud_risk.py)
    depends on a stable order (audit #25)."""
    await _ensure_own_account_transfers_detected(db, account.user_id)

    transactions = (
        (
            await db.execute(
                select(BankTransaction)
                .where(BankTransaction.account_id == account.id, BankTransaction.is_anomalous.is_(False))
                .order_by(BankTransaction.transaction_date, BankTransaction.id)
            )
        )
        .scalars()
        .all()
    )
    return transactions


async def _record_bank_analysis_run(
    db: AsyncSession, account: Account, transactions: list[BankTransaction], disabled_features: list | None = None
) -> str:
    """Task 5.5: Bank never wrote reconciliation reports anywhere (the one
    real gap a cross-vertical audit found — Ecommerce/Sales mostly already
    did). Added at the route layer rather than inside each compute_X
    function, since most of those are synchronous and take no `db` —
    restructuring 9+ already-tested service functions just to thread
    db/async through them wasn't worth it when every route already has
    `account`/`transactions` in hand. `records_excluded` is the count
    filtered out by `eligible_transactions()` (is_anomalous already
    excluded at the DB query level in `_load_transactions`, so
    every exclusion counted here is specifically an is_own_account_transfer
    row -- hence the single-reason `exclusion_detail` below, audit #57)."""
    eligible = eligible_transactions(transactions)
    records_excluded = len(transactions) - len(eligible)
    exclusion_detail = (
        [{"reason": "own_account_transfer", "count": records_excluded}] if records_excluded else []
    )
    report = await record_analysis_run(
        db,
        account.user_id,
        AnalyzerType.bank,
        records_analyzed=len(eligible),
        records_excluded=records_excluded,
        exclusion_detail=exclusion_detail,
        disabled_features=disabled_features,
    )
    return str(report.id)


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    # 3.4: dashboard/summary carries top_payees_by_outflow/top_income_sources
    # (real payee names) and opening/closing balances (real amounts) — both
    # explicitly off-limits for Loan Officer, so this uses DIAGNOSTIC_ROLES
    # (full-data roles only), not the brief-only set. 3.9: RBAC is resolved
    # as a dependency (`require_account_role`), before this body runs.
    account_ctx=Depends(require_account_role(Vertical.bank, DIAGNOSTIC_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "bank.dashboard_summary")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data = compute_dashboard_summary(account, transactions)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions)
    return success_response(data, analysis_run_id=analysis_run_id)


@router.get("/diagnostic/income-stability")
async def get_income_stability(
    account_ctx=Depends(require_account_role(Vertical.bank, DIAGNOSTIC_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "bank.income_stability")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data, disabled_features = get_income_stability_response(transactions)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions, disabled_features)
    return success_response(data, disabled_features=disabled_features, analysis_run_id=analysis_run_id)


@router.get("/diagnostic/abm")
async def get_abm(
    account_ctx=Depends(require_account_role(Vertical.bank, DIAGNOSTIC_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "bank.abm")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data, disabled_features = get_abm_response(transactions)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions, disabled_features)
    return success_response(data, disabled_features=disabled_features, analysis_run_id=analysis_run_id)


@router.get("/diagnostic/cashflow-analysis")
async def get_cashflow_analysis(
    account_ctx=Depends(require_account_role(Vertical.bank, DIAGNOSTIC_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "bank.cashflow_analysis")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data = compute_cashflow_analysis(account, transactions)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions)
    return success_response(data, analysis_run_id=analysis_run_id)


@router.get("/predictive/fraud-risk")
async def get_fraud_risk(
    account_ctx=Depends(require_account_role(Vertical.bank, BRIEF_ONLY_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The task's explicit concern: a Loan Officer (and Bank Viewer) must
    never receive transaction-level detail (transaction_id, amount,
    description) from `flags` — redacted via `redact_flags_for_loan_officer`,
    keeping only flag_type/severity/aggregate fields. Owner/Admin get the
    full, unredacted flags."""
    error, account, role_row = account_ctx
    if error is not None:
        return error
    error, access = await check_feature_access(current_user, "bank.fraud_risk")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data = compute_fraud_risk(account, transactions)
    if role_row.role not in FRAUD_FULL_DETAIL_ROLES:
        data = {**data, "flags": redact_flags_for_loan_officer(data["flags"])}
    data = _shape_fraud_risk(data, access)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions)
    return success_response(data, analysis_run_id=analysis_run_id, plan_access=access)


@router.get("/predictive/loan-readiness")
async def get_loan_readiness(
    account_ctx=Depends(require_account_role(Vertical.bank, BRIEF_ONLY_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """No redaction needed here -- compute_loan_readiness only ever
    extracts fraud_risk_score from compute_fraud_risk internally, never
    propagating the raw `flags` array into its own response."""
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, access = await check_feature_access(current_user, "bank.loan_readiness")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data = compute_loan_readiness(account, transactions)
    data = _shape_loan_readiness(data, access)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions)
    return success_response(data, analysis_run_id=analysis_run_id, plan_access=access)


@router.get("/predictive/cashflow-forecast")
async def get_cashflow_forecast(
    account_ctx=Depends(require_account_role(Vertical.bank, DIAGNOSTIC_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "bank.cashflow_forecast")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data, disabled_features = compute_cashflow_forecast(transactions, account)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions, disabled_features)
    return success_response(data, disabled_features=disabled_features, analysis_run_id=analysis_run_id)


@router.get("/ai/lender-brief")
async def get_lender_brief(
    account_ctx=Depends(require_account_role(Vertical.bank, BRIEF_ONLY_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """No redaction needed -- the lender brief's `risk_flags` section only
    ever includes `flag_count` (an integer), never the raw `flags` array
    itself, so transaction-level detail was never in this response or its
    rendered PDF to begin with."""
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "bank.lender_brief")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data = await get_lender_brief_response(account, transactions)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions)
    return success_response(data, analysis_run_id=analysis_run_id)


@router.get("/ai/financial-health-playbook")
async def get_financial_health_playbook(
    account_ctx=Depends(require_account_role(Vertical.bank, DIAGNOSTIC_ROLES)),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error, account, _role_row = account_ctx
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "bank.financial_health_playbook")
    if error is not None:
        return error

    transactions = await _load_transactions(db, account)
    data, disabled_features = await get_financial_health_playbook_response(account, transactions)
    analysis_run_id = await _record_bank_analysis_run(db, account, transactions, disabled_features)
    return success_response(data, disabled_features=disabled_features, analysis_run_id=analysis_run_id)


@router.get("/upload/{upload_id}/quality-report")
async def get_bank_quality_report(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Task 1.26: bank-namespaced quality report, distinct from the shared,
    analyzer-agnostic `GET /api/v1/upload/{upload_id}/quality-report`
    (task 1.11, built for Ecommerce). 404s both for an unknown upload_id and
    for one that belongs to a non-bank analyzer run -- this route only
    serves Bank uploads."""
    try:
        upload_uuid = UUID(upload_id)
    except ValueError:
        return JSONResponse(
            status_code=400, content=error_response("INVALID_UPLOAD_ID", f"'{upload_id}' is not a valid UUID.")
        )

    upload = (await db.execute(select(Upload).where(Upload.id == upload_uuid))).scalar_one_or_none()
    if upload is None or upload.analyzer_type != AnalyzerType.bank:
        return JSONResponse(
            status_code=404,
            content=error_response("UPLOAD_NOT_FOUND", f"No bank upload found for upload_id {upload_id}."),
        )

    error, role_row = await check_role(db, current_user, upload.merchant_id, Vertical.bank, READ_ROLES)
    if error is not None:
        return error
    error, _ = await check_feature_access(current_user, "platform.data_quality_report")
    if error is not None:
        return error

    metadata = upload.analyzer_metadata or {}
    data = {
        "transactions_parsed": upload.rows_parsed,
        "date_range": {
            "start": upload.date_range_start.isoformat() if upload.date_range_start else None,
            "end": upload.date_range_end.isoformat() if upload.date_range_end else None,
        },
        "months_of_data": metadata.get("months_of_data"),
        # Audit #58 (frontend): already computed and stored at ingestion
        # time (`bank_ingestion.py`), but never returned here -- the
        # frontend had to approximate elapsed days from
        # months_of_data * 30 (badly wrong for short/boundary-crossing
        # statements) since there was nowhere to read the real value from.
        "days_of_history": upload.days_of_history,
        "balance_integrity": metadata.get("balance_integrity"),
        "date_gaps": metadata.get("date_gaps", []),
        "warnings": upload.warnings or [],
        # 3.7: named, row-referenced rejection detail (row/field/code/
        # raw_value/remediation) -- see bank_ingestion.py's
        # compute_bank_quality_report.
        "rejected_rows": metadata.get("rejected_rows", []),
        "mapping_applied": metadata.get("mapping_applied"),
    }
    data = _shape_quality_report(data, role_row)
    return success_response(data)


@router.post("/upload/pdf", status_code=status.HTTP_202_ACCEPTED)
async def upload_bank_pdf(
    file: UploadFile = File(..., description="Text-based bank statement PDF (scanned/image-only PDFs are not supported)"),
    merchant_id: str = Form(...),
    bank_name: str | None = Form(None, description="e.g. 'GTBank'"),
    password: str | None = Form(None, description="PDF password when the statement is encrypted — used once in memory, never stored"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reads the PDF's embedded text layer directly (no OCR, no image
    rendering) — a scanned/image-only PDF is rejected with a clear error
    rather than silently producing no transactions. Still staged and
    dispatched via the existing `ingest_bank_pdf` Celery task rather than
    processed inline, for consistency with the CSV upload path (same
    staging + poll-the-quality-report pattern as POST /api/v1/upload/csv).

    Password-protected PDFs are unlocked in this request handler before
    staging so the password never reaches Redis/Celery or disk."""
    from app.services.bank_pdf_ingestion import (
        PasswordRequiredError,
        WrongPasswordError,
        unlock_pdf_bytes,
    )

    try:
        merchant_uuid = UUID(merchant_id)
    except ValueError:
        return JSONResponse(
            status_code=400, content=error_response("INVALID_MERCHANT_ID", f"'{merchant_id}' is not a valid UUID.")
        )

    error, _ = await check_role(db, current_user, merchant_uuid, Vertical.bank, INGEST_ROLES)
    if error is not None:
        return error

    if file.content_type != "application/pdf" and not (file.filename and file.filename.lower().endswith(".pdf")):
        return JSONResponse(
            status_code=415, content=error_response("UNSUPPORTED_FILE_TYPE", "Only PDF files are supported.")
        )

    raw = await file.read()
    if len(raw) > _MAX_PDF_BYTES:
        return JSONResponse(
            status_code=413, content=error_response("FILE_TOO_LARGE", "File exceeds the 15 MB limit.")
        )
    if not raw:
        return JSONResponse(status_code=422, content=error_response("EMPTY_FILE", "The uploaded file is empty."))

    try:
        raw = await run_in_threadpool(unlock_pdf_bytes, raw, password)
    except PasswordRequiredError as exc:
        return JSONResponse(
            status_code=422, content=error_response("PASSWORD_REQUIRED", str(exc))
        )
    except WrongPasswordError as exc:
        return JSONResponse(
            status_code=422, content=error_response("WRONG_PASSWORD", str(exc))
        )
    except Exception:
        logger.exception("Failed to open uploaded PDF")
        return JSONResponse(
            status_code=422,
            content=error_response(
                "PDF_UNREADABLE",
                "We could not open this PDF. Re-download a text statement from your bank app and try again.",
            ),
        )

    upload_id = uuid4()

    try:
        await run_in_threadpool(stage_upload, str(upload_id), raw, "pdf")
    except Exception:
        logger.exception("Failed to stage uploaded PDF for upload_id %s", upload_id)
        return JSONResponse(
            status_code=500, content=error_response("STAGING_FAILED", "Could not accept the file. Please try again.")
        )

    db.add(Upload(id=upload_id, merchant_id=merchant_uuid, analyzer_type=AnalyzerType.bank, status=UploadStatus.processing))
    await db.commit()

    # Same dispatch-failure handling as POST /api/v1/upload/csv (audit #15)
    # — extended here for consistency now that this exact line also needs
    # the run_in_threadpool wrap (see that route's comment): in local dev
    # with CELERY_TASK_ALWAYS_EAGER on, `.delay()` runs the task inline,
    # and that task calls asyncio.run() internally (safe in a separate
    # worker process, not safe inside this already-running event loop
    # without a threadpool thread of its own).
    try:
        await run_in_threadpool(ingest_bank_pdf.delay, str(upload_id), str(merchant_uuid), bank_name)
    except Exception as exc:
        logger.exception("Failed to dispatch PDF ingestion task for upload_id %s", upload_id)
        await mark_upload_failed(db, str(upload_id), merchant_uuid, AnalyzerType.bank, exc)
        delete_staged_upload(str(upload_id))
        # Eager-mode parse/validation failures raise here — surface the real
        # reason so the UI can show a calm Tier-D rejection instead of a
        # generic dispatch error.
        message = str(exc).strip() or "Could not start processing the file. Please try again."
        if isinstance(exc, (ValueError, NotImplementedError)):
            return JSONResponse(
                status_code=422,
                content=error_response("PARSE_FAILED", message),
            )
        return JSONResponse(
            status_code=502,
            content=error_response("DISPATCH_FAILED", "Could not start processing the file. Please try again."),
        )

    return success_response({"upload_id": str(upload_id), "status": UploadStatus.processing.value})


@router.post("/upload/mono")
async def upload_bank_mono(
    body: MonoIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mono (open banking, NG/GH/KE) is a live API call, not a file — fast
    enough to run synchronously and return the full result, unlike the
    PDF/CSV paths. Note this doesn't create a durable `Upload` row (the
    underlying `ingest_mono_account` has no real UUID to key one on), so
    there's no quality-report to poll afterwards — the response here is
    the complete result."""
    try:
        merchant_uuid = UUID(body.merchant_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=error_response("INVALID_MERCHANT_ID", f"'{body.merchant_id}' is not a valid UUID."),
        )

    error, _ = await check_role(db, current_user, merchant_uuid, Vertical.bank, INGEST_ROLES)
    if error is not None:
        return error

    if not settings.mono_secret_key:
        return JSONResponse(
            status_code=503, content=error_response("MONO_NOT_CONFIGURED", "Mono is not configured.")
        )

    try:
        result = await ingest_mono_account(db, merchant_uuid, body.mono_account_id)
    except MonoAPIError as exc:
        logger.warning("Mono API error ingesting account %s: %s", body.mono_account_id, exc)
        return JSONResponse(
            status_code=502, content=error_response("MONO_API_ERROR", "Mono was unable to fulfil this request.")
        )

    return success_response(result)
