# Bank Test Prompt 3 — Dashboard Endpoint Testing (Consolidated)

**Date:** 2026-07-10
**Mode:** non-isolated — run against the project's real, current dev DB (`backend/app.db`), populated by Bank Prompt 2, no new ingestion, no reset.
**Prerequisite:** Bank Test Prompt 2 — PASS WITH ISSUES (confirmed, see `tests/results/bank/02_ingestion.md`).

## Pre-execution verification

Confirmed before any endpoint call:

| Table | Row count |
|---|---|
| `accounts` | 5 |
| `bank_transactions` | 11,223 |
| `uploads` | 4 |
| `contextual_markers` | 1 |
| `user_merchant_roles` | 3 (+1 added, see below) |

Data from Prompt 2 was fully intact. One evolution since Prompt 2's last snapshot: `is_anomalous=True` count moved from 208 to **223**, because Prompt 2's intentional duplicate-ingestion run (the 5th account) happened *after* the contextual marker was created, so its own transactions in the marker's date range were flagged at insert time — an expected, explainable change, not data loss or corruption.

**One additive DB action was required to run this prompt at all:** the endpoint requires an authenticated user with a `bank` role for the test merchant. A `user_merchant_roles` row already existed for this exact (user, merchant, vertical), but its `merchant_id` was stored as a 36-character dashed UUID string (leftover from an earlier ad-hoc script using raw SQL), while `accounts.user_id` is stored via the ORM's normal 32-character hex form — the two never string-match, so the RBAC check always 403'd. Inserted one additional row through the real ORM (`UserMerchantRole` model), which is now stored in the same form the application itself would produce. The original malformed row was left untouched. No Bank data tables were modified.

## Endpoint discovery

Searched the entire `app/` tree (`main.py`'s registered routers, every `@router.get/post` decorator in every `routes/*.py` file) — confirmed `routes/bank.py` is the only file with Bank-prefixed routes, and no alternate/refactored/versioned Bank router exists anywhere else. Of the 12 endpoints registered under `/api/v1/bank`, exactly **one** is a literal `/dashboard/` endpoint:

| Endpoint | Route | Method | Handler | Scope |
|---|---|---|---|---|
| Bank Dashboard Summary | `/api/v1/bank/dashboard/summary` | GET | `get_dashboard_summary` (`app/routes/bank.py:112`) | **Tested this prompt** |
| (11 others: income-stability, ABM, cashflow-analysis, customer-segmentation, revenue-patterns, fraud-risk, loan-readiness, cashflow-forecast, lender-brief, financial-health-playbook, upload quality-report) | various | GET | various | Diagnostic/predictive/AI/upload endpoints — belong to Prompt 4 and later, not "dashboard" testing; not in scope here |

## Endpoint verification: `GET /api/v1/bank/dashboard/summary`

Called via the real FastAPI app (in-process ASGI, `httpx.AsyncClient`), `get_current_user` overridden to a stub (never-persisted) user object matching the corrected RBAC role above; `get_db` left completely unoverridden so every request hit the real `app.db`. Tested against all 5 accounts currently in the DB.

### 1. Response envelope
Confirmed exact match to `app/schemas/envelope.py::success_response` in all 5 responses: `{success: true, data: {...}, meta: {missing_fields: [], disabled_features: [], analysis_run_id: "<uuid>"}}`. No deviation observed.

### 2. Dashboard calculations — recomputed independently via raw SQL against `bank_transactions`

| Account | Metric | Recomputed | Endpoint Returned | Match? |
|---|---|---|---|---|
| `a8b7128c...` (primary, fresh) | inflows | 29,955,327.79 | 29,955,327.79 | ✅ |
| `a8b7128c...` | outflows | 37,248,435.63 | 37,248,435.63 | ✅ |
| `a8b7128c...` | credit/debit count | 209 / 217 | 209 / 217 | ✅ |
| `49cfae02...` (savings) | inflows | 892,774.81 | 892,774.81 | ✅ |
| `49cfae02...` | outflows | **0** | **0** | ✅ (matches, but see Critical Finding below) |
| `49cfae02...` | credit/debit count | 486 / 0 | 486 / 0 | ✅ |
| `b70312cb...` (wallet) | inflows | 61,433,215.47 | 61,433,215.47 | ✅ |
| `b70312cb...` | outflows | 63,127,382.94 | 63,127,382.94 | ✅ |
| `889e6553...` (2nd duplicate) | inflows | 33,555,327.79 | 33,555,327.79 | ✅ |
| `889e6553...` | outflows | 40,848,435.63 | 40,848,435.63 | ✅ |

**Every single recomputed value matches the endpoint's returned value exactly, in all 5 accounts.** `compute_dashboard_summary`'s arithmetic is verified correct.

### 3. `is_own_account_transfer` logic
Implementation: `detect_own_account_transfers` (`app/services/bank_account_integrity.py:88`), exclusion applied via `eligible_transactions` (`app/services/bank_cashflow.py:16`), called inside `compute_dashboard_summary` (`app/services/bank_dashboard.py:57`).

**Confirmed the dashboard correctly excludes rows flagged `is_own_account_transfer=True`** — this is not in question. **What is in question is the correctness of the flags themselves**, and this is the central finding of this prompt:

- Savings account (`49cfae02...`): **933 of 933 debits (100%)** are flagged `is_own_account_transfer=True` — confirmed via direct SQL. Without this exclusion, real outflows would be 3,794,287.92 across 905 transactions, not 0.
- Wallet account (`b70312cb...`): 240 of 5,662 debits (~4.2%) flagged.
- Primary file, two of its three copies: 24 rows each flagged (12 debit + 12 credit), corresponding to a real recurring "Transfer to/from Own Account" pattern in the source file (12 × 300,000). The third copy of the same file (ingested after the one manual detection pass already ran) has **zero** of these flagged, so it reports 3,600,000 more in both inflows and outflows than the other two copies of the identical source data.

Root cause: Prompt 2's non-isolation combined with the greedy, unscoped, same-day/same-amount-tolerance matching algorithm in `detect_own_account_transfers` produces false-positive-heavy results when multiple large real accounts (with common round-number transaction amounts) are matched against each other simultaneously. This is a genuine architectural risk, not just a test-environment artifact — the same false-positive pattern could occur in production wherever a business's several accounts share similar transaction amounts/timing by coincidence.

### 4. `is_anomalous` logic
Confirmed excluded correctly at the `_load_account_and_transactions` query level (`app/routes/bank.py:76`, `is_anomalous.is_(False)` in the WHERE clause itself — excluded before the data even reaches `compute_dashboard_summary`). Consistent with Prompt 2's finding that this flagging mechanism (`is_within_marker_ranges`/contextual markers) is precise (0 false positives observed in Prompt 2). No new issues found here in Prompt 3.

### 5. Disabled features
**Not Implemented.** `dashboard/summary`'s route handler never passes a `disabled_features` argument to `success_response`, so it always defaults to `[]` regardless of data volume — there is no minimum-months/minimum-transaction-count/minimum-account-count gate for this specific endpoint (unlike `diagnostic/income-stability`, which does have a 3-month minimum, per Prompt 2's earlier code reading). This was confirmed empirically: `meta.disabled_features` was `[]` in all 5 responses, including the wallet account with 37 months of data and the savings account which failed balance integrity — no data condition triggers a disabled state on this endpoint. This is a factual description of the current code, not a defect by itself, but worth knowing before assuming any dashboard metric silently degrades when data is thin.

### 6. `account_number_hash`
Not re-verified in this prompt (already confirmed hashed in Prompt 2); not returned anywhere in the dashboard response, so not directly relevant to dashboard output.

## Prompt 2 follow-ups, assessed against dashboard behavior

| Prompt 2 finding | Affects dashboard output? |
|---|---|
| Duplicate ingestion (no dedup) | **Yes, directly** — three copies of the primary file now produce two *different* sets of dashboard numbers (see above), not just three redundant identical rows. |
| `is_own_account_transfer` not auto-wired | **Yes, directly and severely** — see Critical Finding. |
| `account_number_hash` fallback (upload-id-derived) | No direct dashboard impact — not surfaced in this endpoint's response. |
| Balance integrity failures (savings: 32.76 discrepancy; wallet: 800,624.14 discrepancy) | **Partially** — `dashboard/summary` reads `opening_balance`/`closing_balance` directly from the `accounts` row (as originally derived at ingestion) and returns them as-is; it does not re-surface the integrity-check failure itself anywhere in this response. A user would see a `balance` block with numbers but no indication those numbers failed reconciliation. |

## Overall verdict

**PASS WITH ISSUES for the wallet and primary-file accounts; FAIL for the savings account specifically**, due to the transfer-flag contamination reducing its reported outflows to zero. The dashboard endpoint's own code — calculations, envelope, exclusion logic, RBAC — is correct and verified in every case tested. The critical, must-fix-before-trusting-this-feature issue is entirely upstream, in `is_own_account_transfer` flag correctness at multi-account volume.
