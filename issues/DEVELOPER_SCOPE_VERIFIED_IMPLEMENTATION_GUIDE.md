# Scanwick Developer Scope — Verified Implementation Guide

**Source:** `Scanwick_Developer_Scope.pdf` (6 pages, measured 27 July 2026)  
**Repository reviewed:** current `scanwick` workspace, 1 August 2026  
**Purpose:** the developer-facing replacement for the PDF. It records the complete required scope, what was verified in the repository, the intended resolution, testable acceptance criteria, and paste-ready prompts for an implementation agent.

> This document is a scope and implementation guide. It does not claim that planned changes have already been implemented. “Verified” means the relevant current code was inspected; “missing” means the required model/flow was not found in the current application models.

## 1. Product decision and delivery order

The bank-statement analyzer is the product. Ecommerce ingestion remains only as evidence for cash-gap verification. The sales analyzer is cancelled.

The PDF measured 41 keeper services (6,124 lines) and 34 services to remove (4,906 lines), or 44% of the service layer. It also calls for deleting 19 sales-specific test files (3,195 lines), leaving 105 test files. Re-count these figures before execution because the repository may have changed after the PDF audit.

Implement in this order:

1. **Correctness and access control:** ABM, calendar windows, score weights, CV boundary, lender brief, fraud false positives, loan-officer access, currency totals, deduplication, date locale, mapping, rejected-row warnings, session-derived merchant context.
2. **Scope removal:** delete sales and non-core ecommerce/bank capability; remove the associated routes, models, migrations, tests, frontend navigation, permissions, and documentation.
3. **Mothball:** move payment/report scheduling code out of the main runtime path and remove routes without destroying reusable code.
4. **New lender product:** identity, business entity, multi-account consolidation, cash-gap reconciliation, consent/retention/audit, assessments/shares/outcomes, real-versus-nominal currency reporting.

## 2. Keep intact

Do not rewrite these working foundations while executing this scope:

| Area | Components | Required treatment |
| --- | --- | --- |
| Provenance | `reconciliation.py`, `reconciliation_reports` | Every analysis must retain source, date range, currency conversions, exclusions/reasons, disabled features, contextual markers, and `analysis_run_id`. This is the attestation layer. |
| Mapping | `column_mapping.py`, `column_mapping_store.py`, `column_mappings` | Keep exact → fuzzy → confirm → unmapped resolution, header-signature persistence, and the prohibition on fuzzy auto-apply for money fields. Correct the `total cost` synonym only. |
| Open banking | `mono_client.py`, `mono_ingestion.py` | Keep Mono behind an adapter so another open-banking/NIBSS provider can be added. |
| Bank core | `bank_ingestion.py`, `bank_pdf_ingestion.py`, `bank_account_integrity.py`, `bank_transaction_classification.py`, `bank_cashflow.py`, `bank_dashboard.py`, `bank_income_stability.py`, `bank_abm.py`, `bank_cashflow_analysis.py`, `bank_fraud_risk.py`, `bank_loan_readiness.py`, `bank_lender_brief.py`, `bank_playbook.py`, `bank_cashflow_forecast.py` | Preserve the core; apply the corrections below. In particular, do not alter the 0.01 account-integrity tolerance or the shared `eligible_transactions` exclusions without explicit regression tests. |
| Ecommerce input | `ecommerce_ingestion.py`, `ecommerce_margins.py`, `ecommerce_revenue.py`, `ecommerce_order_items.py`, `ecommerce_dashboard.py` | Keep only the minimum needed to ingest sales records and compare them with bank inflows. Do not rewrite the margin behavior that returns `null` when COGS is unknown. |
| Platform | encryption, storage, staging, Redis, FX/merchant currency, dataset detection, AI/recommendations, contextual markers, merchant provisioning, team management, privacy, RBAC/entitlements | Keep the mechanisms. Rewrite the role matrix and add missing routes/models. |

## 3. Verified corrections

### 3.1 Loan-readiness calculations

**Files:** `backend/app/services/bank_loan_readiness.py`  
**Status:** resolved on 1 August 2026; regression-tested in `backend/tests/services/test_bank_loan_readiness.py`.

| Defect | Evidence in current code | Required resolution | Acceptance criteria |
| --- | --- | --- | --- |
| Average monthly balance (ABM) omits quiet days | `compute_daily_closing_balances` emits only transaction dates; `_average_for_window` averages only those dates. | Build a calendar-day series from the opening/first known balance through the reference date. Carry the prior closing balance over each zero-activity day before averaging. Define and test the no-opening-balance behavior. | A fixture with sparse transactions includes every day in the denominator and matches a hand-calculated result. |
| Month windows use `months * 30` | `_average_for_window` subtracts `timedelta(days=months * 30)`. | Use a calendar-aware offset (for example `dateutil.relativedelta`) and document inclusive boundary behavior. | 3/6/12-month windows start on true calendar dates across February and leap years. |
| CV of exactly 40 is volatile | Current condition is `< 40` for moderate. | Use `<= 40` for moderate; volatile is `> 40`. | Tests cover 19.9, 20, 40, and 40.1. |
| Missing components silently receive redistributed weight | Current code normalizes each available component by total available weight. | Keep fixed 30/25/25/20 weights. An unavailable component is unearned; expose `max_achievable_score` and disabled reasons. Do not claim a component has a different specified weight. | Response weight percentages stay 30/25/25/20, calculated score never benefits from unavailable data, and max achievable is returned. |

Implementation notes:

- Decide the balance seed explicitly. Prefer a verified statement opening balance; if unavailable, begin at the first transaction’s `balance_after`, mark pre-seed days unavailable, and describe the limitation in provenance.
- Use `Decimal` through balance arithmetic. Do not turn money into floats merely to fill dates.
- Ensure lender brief and ABM diagnostic share the corrected function, so scores cannot disagree.

**Agent prompt**

> In `backend/app/services/bank_loan_readiness.py`, repair loan-readiness correctness without changing the fixed 30/25/25/20 specification. Expand daily balances across every calendar day by carrying forward the last known closing balance, use calendar-aware 3/6/12-month windows, classify CV=40 as moderate, and never renormalize missing components. Return each fixed weight, disabled reasons, and `max_achievable_score`. Add focused regression tests for sparse balances, February/leap-year boundaries, CV boundaries, and missing components. Run the relevant test module.

**Implementation record (1 August 2026):** completed in `backend/app/services/bank_loan_readiness.py`. The daily series now carries balances through quiet days, month windows use `relativedelta`, CV=40 is moderate, and unavailable components remain unearned at their fixed weights. The focused test module passed (17 tests).

### 3.2 Lender brief output

**File:** `backend/app/services/bank_lender_brief.py`  
**Status:** resolved on 1 August 2026; regression-tested in `backend/tests/services/test_bank_lender_brief.py`.

Current `SECTION_NAMES` use `income_stability`, `cash_flow_analysis`, `loan_readiness_assessment`, and `risk_flags`, rather than the required lender narrative structure. `_build_sections_and_key_metrics` builds dictionaries/lists, and `_render_lender_brief_pdf` inserts `str(section)` as one clipped 110-character line. This produces raw dictionaries and unreadable/truncated output.

Required structure:

1. Business overview
2. Income summary
3. Expense summary
4. Risk assessment
5. Creditworthiness assessment
6. Recommendation paragraph

Resolution:

- Create deterministic narrative builders for every required section from structured metrics.
- Optionally let AI improve wording, but validate its result and always retain deterministic fallback text. A failed AI call or one failed section must not fail the whole brief.
- Render wrapped paragraphs with headings, page breaks, margins, and a footnote stating source, date range, exclusions, and integrity result.
- Preserve structured metrics separately for API consumers; never render Python dict/list representations.
- The longer-term product replacement is a verifiable assessment link, not an editable PDF. Maintain the PDF only while that link is being delivered.

Acceptance criteria: no `{...}`/`[...]` raw structures in output; all six sections exist in readable prose; text wraps/paginates; forced AI failure returns usable deterministic output.

**Agent prompt**

> Rebuild `bank_lender_brief.py` into a lender-facing narrative. Keep metric assembly structured, then generate six deterministic prose sections: business overview, income summary, expense summary, risk assessment, creditworthiness assessment, and recommendation. AI wording is optional and must have per-section deterministic fallback. Replace 110-character single-line PDF insertion with wrapped, paginated rendering, and include provenance/integrity footnotes. Add tests proving there are no raw dict/list strings and that an AI failure still yields a complete brief.

**Implementation record (1 August 2026):** completed in `backend/app/services/bank_lender_brief.py`. The API now returns six lender-facing prose sections, the AI recommendation has a deterministic fallback, and PDFs wrap text and create additional pages when needed. The focused test module passed (4 tests).

### 3.3 Fraud: contributory savings are not fraud

**File:** `backend/app/services/bank_fraud_risk.py`  
**Status:** resolved on 1 August 2026; regression-tested in `backend/tests/services/test_bank_fraud_risk.py`.

The z-score threshold and round-number structuring logic can flag legitimate ajo, esusu, and adashe patterns. Add a transparent positive-signal classifier using recurring participants, cadence, approximately consistent contributions, and expected payout cycles. It must reduce/suppress only the affected false-positive flags—not blanket-suppress high-risk activity. Return the detected pattern and why it was treated as legitimate.

Acceptance criteria: labelled contributory-savings fixtures no longer produce inappropriate fraud flags; true structuring fixtures remain flagged; explanation is available to authorized users and safely summarized for loan officers.

**Implementation record (1 August 2026):** completed in `backend/app/services/bank_fraud_risk.py`. Named ajo/esusu/adashe payments qualify only when there are at least three separate, similarly sized, regularly recurring contributions. Qualifying transactions are excluded from z-score and structuring detection and returned as an aggregate positive signal; irregular named payments and unrelated round-number transactions remain subject to fraud checks. The focused suite passed (20 fraud tests; 39 related tests total).

### 3.4 Loan-officer scope

**File:** `backend/app/routes/bank.py`  
**Status:** verified open defect.

`READ_ROLES` currently contains `loan_officer` and is used across dashboard and diagnostic endpoints. Fraud flags are partly redacted, but this is not sufficient: loan officers must be brief/summary-only and must not access transaction-level diagnostics, payee data, descriptions, amounts, or account-detail endpoints.

Resolution:

- Define endpoint policy sets, for example `FULL_DATA_ROLES`, `SUMMARY_ROLES`, and `BRIEF_ONLY_ROLES`; apply them at route dependencies, not as scattered handler conditions.
- Explicitly list which summarized endpoints a loan officer may use. Default-deny all new bank endpoints until classified.
- Return a consistent 403 for forbidden paths and test it for every restricted route class.

**Solution (4 August 2026):** `backend/app/routes/bank.py` already had `FULL_DATA_ROLES`/`DIAGNOSTIC_ROLES` policy sets excluding `loan_officer` from every transaction-level diagnostic route, but `loan_officer` was still in the group used by `/dashboard/summary` (real payee names via `top_payees_by_outflow`/`top_income_sources`, real opening/closing balances), `/accounts` (real `bank_name`/`closing_balance`), and the quality-report endpoint (real balance-integrity amounts embedded in both the JSON fields and a warning's free-text message). Fixed by: (1) adding a `BRIEF_ONLY_ROLES` set for endpoints that are aggregate-only by construction (fraud-risk, loan-readiness, lender-brief) and moving `/dashboard/summary` to `DIAGNOSTIC_ROLES` (denies loan_officer entirely); (2) adding `_shape_accounts()` so loan_officer gets only `id`/statement-period dates from `/accounts`, never `bank_name`/`closing_balance`; (3) adding `_shape_quality_report()` so loan_officer gets only the `balance_integrity_passed` boolean, with the discrepancy amount scrubbed from both the `balance_integrity` object and the matching warning message. Also fixed two unrelated pre-existing bugs surfaced while verifying this: `bank_viewer` was in the same set used to decide fraud-risk flag redaction as owner/admin, so it received unredacted transaction-level fraud flags despite the route's own docstring saying it shouldn't (added a narrower `FRAUD_FULL_DETAIL_ROLES` = owner/admin only for that one check); and `tests/routes/test_bank.py::test_get_lender_brief_returns_all_sections` still asserted the pre-3.2 dict-shaped section names, which no longer exist post-3.2's prose rebuild. Regression tests added/updated in `test_bank_rbac.py`, `test_bank_accounts_list.py`, and `test_bank_quality_report.py`; full `-k bank` suite passes (205 tests).

### 3.5 Ecommerce currency aggregation

**File:** `backend/app/services/ecommerce_revenue.py`  
**Status:** verified open defect.

`aggregate_order_list` sums original-currency `gross_revenue` and labels the total using the first order’s `original_currency`. It must aggregate `base_currency_amount` in the merchant base currency. Missing converted amounts cannot be silently mixed into a total: surface them in `meta.missing_fields`/quality output and define whether the order is excluded from the converted total.

**Solution (4 August 2026):** verified already resolved in the current codebase, no code change needed. `aggregate_order_list` (`backend/app/services/ecommerce_revenue.py`) already sums `base_currency_amount` (falling back to a 1.0 rate only when the order's own currency already equals the base currency), reports the total under the merchant's real base currency (not the first order's `original_currency`), and excludes orders with a missing conversion from the converted total while surfacing `excluded_orders_due_to_missing_conversion`/`included_orders`; `compute_dashboard_revenue` maps that into `missing_fields` on the API response. This entry in the guide predates that fix landing.

### 3.6 Ecommerce deduplication

**Files:** `backend/app/services/ecommerce_ingestion.py`, `backend/app/models/orders.py`, migration layer  
**Status:** verified open defect.

The current ingestion preloads non-null `external_order_id` values, then skips duplicates only when an ID exists. Rows without order IDs remain repeatable. The `orders` model has no visible composite uniqueness constraint.

Resolution:

- Generate a deterministic surrogate external ID for missing IDs from merchant ID, source/header signature, normalized date, SKU, quantity, gross revenue, and stable row position/line-item identity. Make the collision policy explicit.
- Normalize IDs before comparison.
- Add an actual database unique constraint/index appropriate to the data model (normally merchant plus source plus canonical external/surrogate ID), handle `IntegrityError`, and make retries idempotent.

**Solution (4 August 2026):** completed. `_generate_surrogate_external_id()` (`backend/app/services/ecommerce_ingestion.py`) builds a deterministic ID from merchant_id, source, the row's own position in the file, order_date, SKU, quantity, and gross_revenue whenever a row has no real `external_order_id` — stable across an unmodified re-upload of the same file, so those rows are now caught by the existing dedup check instead of bypassing it. Collision policy is explicit and documented inline: two different rows sharing all six inputs hash identically and the second is treated as a duplicate. Also fixed a related bug found while verifying this: the old `str(raw.get(col))` turned a genuinely-missing cell into the literal string `"nan"` (pandas leaves numeric-looking ID columns as float64), which was "present" to the old check and silently collided every such row together — `_normalize_external_id()` now treats NaN/blank as truly missing. IDs are normalized case-insensitively for comparison only (`_dedup_key()`, casefold) without changing what's stored/displayed. Added `uq_orders_merchant_source_external_id` (unique on `merchant_id`, `data_source`, `external_order_id`) via migration `a3f7b6c9e1d2` (SQLite-safe via `batch_alter_table`) as the DB-level backstop; `_commit_pending_orders()` commits the batch in one round trip in the common case and, only on an `IntegrityError` (a genuine concurrent-ingest race), rolls back and retries row-by-row in savepoints so a race drops just the colliding row(s), not the whole batch — making a retried request idempotent. The quality report now includes `rejected_reasons` (missing_gross_revenue/missing_order_date counts) and a named `duplicates_skipped` warning. Regression tests added in `test_ecommerce_ingestion.py` (missing-ID dedup, NaN-string bug, case-insensitive dedup, DB constraint enforcement, race-recovery), `test_ecommerce_ingestion_task.py` (end-to-end quality-report surfacing); full backend suite passes (789 tests).
- Include duplicate/rejected counts and reasons in the quality report.

### 3.7 Locale-aware dates and rejection warnings

**Files:** `bank_ingestion.py`, `ecommerce_ingestion.py`, mapping-store/value-rule path, quality-report routes  
**Status:** required change; ecommerce’s rejection branch currently increments `rows_rejected` and continues without producing a named warning.

Resolution:

- Read `date_locale` from persisted mapping `value_rules`; adopt documented day-first default only when the mapping locale is absent.
- Detect ambiguous values such as `03/04/2026`; do not silently guess. Reject or require mapping confirmation and emit a stable warning code.
- Every rejected row must produce a named warning with row reference, canonical field, reason/code, raw value only when safe, and remediation. Aggregate warnings without exposing sensitive data in lender-facing outputs.

**Solution (4 August 2026):** completed. Added `app/utils/locale_dates.py`'s `parse_locale_date()`: reads `date_locale` from the mapping's persisted `value_rules`, falling back to the documented day-first default only when absent; a numeric D/M/Y value where both components are ≤12 (e.g. `03/04/2026`) and no locale was ever confirmed is rejected with a stable `AMBIGUOUS_DATE` code rather than guessed, and resolves normally once a locale is confirmed for that mapping (`day_first` or `month_first`). A day>12 value (`25/12/2026`) is unambiguous either way and always parses. Year-first ISO values (`2026-01-05`) are detected separately and always parsed with `dayfirst=False`, working around a genuine pandas/dateutil bug found while testing this: `pd.to_datetime("2026-01-05", dayfirst=True)` silently returns `2026-05-01`, swapping the trailing month/day pair even though the leading 4-digit year already fixes the field order. Wired into both `bank_ingestion.py`'s `extract_canonical_bank_rows` (transaction_date) and `ecommerce_ingestion.py`'s `extract_canonical_rows` (order_date), each now taking `value_rules` (bank's didn't before). `compute_bank_quality_report`/`compute_ecommerce_quality_report` now return a `rejected_rows` list: every rejected row gets a named entry (row position, canonical field, stable code, raw value, remediation) — either the AMBIGUOUS_DATE/INVALID_DATE detail from parsing, or a synthesized `MISSING_REQUIRED_FIELD` entry for a plain missing amount/date. Surfaced via both the bank-namespaced and shared quality-report routes; redacted to `[]` for Loan Officer (3.4) since it's row-level import detail with raw source values, not brief-level summary. Also fixed a related bug found while wiring this through: `routes/uploads.py`'s auto-apply fast path resolved a saved mapping's `value_rules` (including any previously-confirmed `date_locale`) but never actually forwarded it to `_dispatch_ingestion` — every zero-touch re-upload reusing a saved mapping silently reverted to the unconfirmed default locale. Regression tests added in `tests/utils/test_locale_dates.py`, `test_bank_ingestion.py`, `test_ecommerce_ingestion.py`, `test_bank_quality_report.py`, and `test_mapping_routes.py`; full backend suite passes (805 tests; one unrelated pre-existing flaky timing test in `test_sales_deals.py` passes on rerun).

### 3.8 Mapping synonym: `total cost`

**File:** `backend/app/services/column_mapping.py`  
**Status:** verified open defect.

`CANONICAL_SYNONYMS[AnalyzerType.ecommerce]["unit_cogs"]` includes `total cost`. A line total must not be mapped to a per-unit COGS field. Remove this exact synonym from automatic `unit_cogs` resolution. If a line-total cost field is supported, map it to a distinct canonical `line_cogs` field with explicit conversion; otherwise require confirmation/unmapped status.

**Solution (4 August 2026):** completed, using the "otherwise require confirmation/unmapped status" branch — no distinct `line_cogs` field exists downstream (no ingestion path or `OrderItem` column reads one), so building one would be new, unrequested scope rather than a bug fix. Removed `"total cost"` from `CANONICAL_SYNONYMS[AnalyzerType.ecommerce]["unit_cogs"]`'s exact-match variant list. This mattered specifically because tier-1 (exact) matching is the one tier `MONEY_FIELDS`' fuzzy-auto-apply block does NOT cover — an exact `"total cost"` header used to resolve straight to `unit_cogs` with zero confirmation, silently corrupting unit-margin/profit-leak figures by whatever the average quantity-per-order happened to be. A `"total cost"` header now falls through to tier-2 fuzzy scoring, where `unit_cogs`'s `MONEY_FIELDS` membership correctly forces `needs_confirmation` (verified: score 0.57, well below the fuzzy auto-apply threshold) instead of vanishing to unmapped or auto-applying. Regression test added in `test_column_mapping.py`; full mapping/ecommerce suite passes (202 tests).

### 3.9 Merchant identity and RBAC boundary

**Files:** `rbac.py`, all routes accepting merchant IDs (including bank PDF/Mono paths)  
**Status:** verified open defect in bank routes.

The bank upload/PDF/Mono paths accept a client-supplied `merchant_id`; current RBAC checks access after parsing it. The scope requires merchant context to be derived from authenticated session/route dependency and enforced before handler business logic. Design an explicit active-business/session context for users who legitimately belong to multiple businesses; a public/computable user-derived merchant ID is not an authorization boundary.

Acceptance criteria: a client cannot select another merchant by changing query/form/body data; owner/member/multi-business cases are tested; every read/write route uses the shared dependency.

**Solution (4 August 2026):** completed for the routes that survive Section 4's scope removal (bank.py in full; ecommerce.py's two surviving routes — see scope note below); `sales.py` intentionally left untouched since it's already scheduled for full deletion in Section 4 and fixing it now would be discarded work.

Audit first: every merchant_id-accepting route in `bank.py`/`ecommerce.py`/`sales.py` already ran `check_role` and correctly denied a caller with no `UserMerchantRole` row for the target merchant — a client genuinely cannot "select another merchant" today by changing form data, because `check_role` fails closed. `ecommerce.py`'s and `sales.py`'s merchant_id params were literally annotated `"Placeholder until real auth/RBAC derives this from the session"` by the original authors, confirming this was already a known, flagged gap in architecture (not a live open access hole) across all three verticals. `team.py`/`privacy.py`/`auth.py` already derive merchant_id correctly from the authenticated user (`ensure_merchant_provisioned(db, current_user.id)`), never from client input — the pattern to build on. No live case of a "computable merchant_id" bypass was found: `merchant_provisioning._auto_merchant_id_for_user` (a deterministic `uuid5` of a fixed namespace + user_id) is only ever called server-side from `current_user.id`, never accepted as client input.

The one concrete, exploitable defect found: `bank.py`'s `_load_account_and_transactions` loaded the `Account` row, ran a WRITE side-effect (the own-account-transfer scan, `detect_own_account_transfers`), and loaded every transaction — all BEFORE `check_role` was ever called back in the route body. An authenticated user with no role at all for an account's owning merchant could trigger that write just by guessing a valid `account_id`.

Fix: added `backend/app/services/merchant_dependencies.py` with two FastAPI dependency factories — `require_merchant_role(vertical, allowed_roles)` for routes where merchant_id is itself the query param, and `require_account_role(vertical, allowed_roles)` for bank.py's `account_id`-scoped routes (which need a minimal, side-effect-free `Account` lookup first to resolve the owning merchant). Both resolve and validate BEFORE the route handler body runs at all — a structural guarantee from FastAPI's dependency-resolution order, not a call-ordering convention. `bank.py`'s `_load_account_and_transactions` was split: the dependency does only the minimal authorization-safe lookup; a new `_load_transactions()` (transfer scan + transaction query) is called by the handler body only after authorization succeeds. All 9 account-scoped bank routes plus `/accounts` were converted; `ecommerce.py`'s `/dashboard/summary` and `/dashboard/revenue` (the two routes Section 4 keeps) were converted the same way. Upload/PDF/Mono routes and `uploads.py`'s `POST /csv` were verified already correctly ordered (check_role runs before any file read/write) and left as-is. Added `GET /api/v1/team/my-businesses` — the "explicit active-business/session context" the scope asks for: lists every business (merchant_id, vertical, role, `is_own_business`) the caller belongs to, so a frontend can discover/switch between businesses instead of the caller needing to already know which merchant_id to pass.

Regression tests added in `test_bank_rbac.py` (proving the transfer-scan write does NOT run for an unauthorized account_id, and still does for an authorized one — both directions), `test_team_routes.py` (solo-owner and multi-business discovery cases). Full backend suite passes (811 tests).

## 4. Delete from the active product

Delete code, registrations, imports, route exposure, permissions, models/tables/migrations, tests, fixtures, frontend pages/navigation, and documentation together. Do not leave dormant runtime code.

### Sales analyzer

Delete services: `sales_deals`, `sales_forecast`, `sales_ingestion`, `sales_notifications`, `sales_pipeline`, `sales_playbook`, `sales_postmortem`, `sales_quality`, `sales_rbac_scoping`, `sales_rep_leaderboard`, `sales_rep_trajectory`, `sales_slippage`, `sales_stage_timing`, `sales_stage_velocity`, `sales_stagnation`, `sales_win_dna`, `sales_win_probability`.

Delete: all `/api/v1/sales` routes, `deals`, `stage_transition_logs`, sales-specific tests (the PDF identifies 19 files), related UI and role/entitlement entries.

### Ecommerce depth features

Delete: `ecommerce_rfm`, `ecommerce_rfm_endpoint`, `ecommerce_churn`, `ecommerce_holt_winters`, `ecommerce_inventory_forecast`, `ecommerce_sku_matrix`, `ecommerce_diagnostics`, `ecommerce_returns`, `ecommerce_ad_kill_switch`, `ecommerce_playbook`, `ecommerce_olist_adapter`; plus `rfm_segment_assignments`, `sku_inventory`, `ad_kill_audit_log`.

Keep ecommerce API only for upload, quality report, and a minimal revenue endpoint used by cash-gap reconciliation.

### Bank features outside the credit decision

Delete for now: `bank_customer_segmentation` and `bank_revenue_patterns`, their endpoints/tests/UI/permissions. The first also risks exposing confidential payee data; the second requires history most users do not have.

## 5. Mothball rather than delete

Move reusable payment/report scheduling code to a clearly documented inactive branch/package and remove it from the running application/router. Do not execute irreversible schema drops until a migration and rollback plan are approved.

Mothball: `payments.py`, `paystack_client.py`, `flutterwave_client.py`, `payment_provider.py`, payment routes, `subscriptions`, `payment_transactions`, `generated_reports`, `report_schedules`, and notification scheduling. Remove live endpoints and background scheduling registrations; ensure no secrets, workers, or UI links remain active.

## 6. Build: lender-ready product capabilities

These were not found as application data models in the reviewed repository and should be designed/migrated before implementation.

| Capability | Minimum delivery |
| --- | --- |
| Identity | BVN capture/verification and a `business_entities` model distinct from user accounts; include legal name, CAC number, owner linkage, verification status, and several accounts per entity. Treat BVN as sensitive: encrypt, minimize retention, never log raw values. |
| Multi-account consolidation | A business-level assessment combines commercial bank, fintech wallet, and cooperative accounts. Specify cross-account transfer netting and provenance per account. |
| Cash-gap reconciliation | Compare eligible bank inflows to uploaded sales records over matching dates; output verified unbanked cash revenue, confidence, exclusions, currency basis, and source links. Example from PDF: NGN 5,200,000 inflows vs NGN 8,633,800 sales = NGN 3,433,800 (40%) unbanked cash. Do not treat it as a footnote. |
| Consent, retention, audit | `consent_records` (subject, scope, granted/revoked timestamps, source), retention by data class, delete-my-data workflow, and `data_access_log` (actor, assessment, timestamp, context/source). Implement authorization, immutable audit semantics, and deletion exceptions where legally required. |
| Assessment and verifiable share | `assessments` as the institution-facing unit of value/billing; `assessment_shares` with recipient, expiry, revocation, and view history. Link shows source, ingestion date, integrity result, and reconciliation-backed record. |
| Outcome tracking | `assessment_outcomes` records approval/decline, amount, repayment status, and outcome dates. Add data-quality/consent rules before collecting outcome data. |
| Currency reality | Report nominal and real trends using a documented inflation series, base period, and data provenance. Never call nominal devaluation-driven growth an improving trajectory. |

New endpoints: contextual-marker CRUD; BVN/business entity; consent and delete-my-data; assessment creation/read; share create/revoke/view; institution-facing assessment API. Keep auth/team/privacy routes.

## 7. Data and API migration plan

### Tables retained

`accounts`, `bank_transactions`, `bank_account_identifiers`, `orders`, `order_items`, `uploads`, `column_mappings`, `contextual_markers`, `reconciliation_reports`, `merchant_settings`, `exchange_rates`, `user_merchant_roles`, users/auth tables, `login_events`, `team_invites`, `notification_preferences`.

### Tables deleted

`deals`, `stage_transition_logs`, `rfm_segment_assignments`, `sku_inventory`, `ad_kill_audit_log`, `postmortem_reports`, `returns`.

### Tables mothballed

`subscriptions`, `payment_transactions`, `generated_reports`, `report_schedules`.

### New tables

`business_entities`, `consent_records`, `data_access_log`, `assessments`, `assessment_shares`, `assessment_outcomes`.

Replace generic `owner/admin/manager/viewer` semantics with explicit scopes: Account Owner/CFO, Accountant, Loan Officer, and Analyst read-only. Model capabilities, not just names, so “loan officer can see an assessment brief but not transactions” is enforceable.

The core surviving API includes `POST /api/v1/bank/upload`, bank quality/summary/diagnostic/predictive/lender-brief/playbook endpoints, reconciliation, generic CSV upload, mapping detect/confirm, and auth/team/privacy. Consolidate the currently split bank PDF/Mono upload paths behind `POST /api/v1/bank/upload` with a validated `source_type`, while preserving asynchronous staging and quality-report polling.

## 8. Execution safety and definition of done

Before destructive scope cleanup, create a migration inventory, production backup/rollback plan, and an endpoint/frontend dependency list. Delete in a feature branch with migration tests. “Mothball” means inactive in the main runtime, not untracked code.

The work is done only when:

- all Section 3 defects have regression tests and pass;
- loan officers are denied all transaction-detail paths and can use only explicitly approved assessment/summary paths;
- lender output is readable, provenance-backed, and robust to AI failure;
- date ambiguity/rejections and missing conversion values are visible in quality reports;
- duplicate uploads are idempotent at both application and database levels;
- sales/non-core ecommerce/non-credit bank surfaces are absent from runtime and tests/navigation;
- payment/report scheduling is inactive without data loss;
- identity, consent, audit, assessment/share/outcome schemas and flows are implemented with migrations;
- cash-gap and multi-account results are provenance-linked;
- the single new PRD is versioned, has a change log, includes security (passwords, tokens, rate limits, file validation, encryption, consent, retention, audit, RBAC), defines the four-rung data maturity ladder (Mono, statement, statement+sales, multi-account), and uses measurable accuracy targets.

## 9. Master implementation prompt

> Use `docs/DEVELOPER_SCOPE_VERIFIED_IMPLEMENTATION_GUIDE.md` as the source of truth. First implement and test the verified correctness/security fixes: loan-readiness ABM/calendar/CV/weights, lender-brief prose rendering, contributory-savings fraud handling, endpoint-level loan-officer restrictions, base-currency revenue aggregation, idempotent ecommerce ingestion, locale-aware date parsing, named rejection warnings, `total cost` mapping correction, and session-derived merchant context. Next remove the explicitly cancelled sales/non-core ecommerce/non-credit bank product surfaces and mothball payments/reports safely. Then implement the business entity, consent/audit, assessment/share/outcome, multi-account, cash-gap, and real-currency capabilities. Preserve reconciliation provenance, mapping protections, Mono abstraction, and bank integrity/cashflow behavior. Add migrations and regression tests for every change; do not silently change financial semantics or expose transaction data to loan officers.
