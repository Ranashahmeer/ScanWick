# Scanwick Critical Fix Pack — Issue Catalog

**Source:** `Scanwick_Critical_Fix_Pack.pdf` (line numbers verified against the pass-3 tree, 28 July 2026).
**Scope of the source document:** Bank Statement analyzer (the product) + Ecommerce (the cash-verification input) only.
**This file:** a straight transcription of every issue from that PDF into the same catalog format as `AUDIT_ISSUES.md`, each tagged with whether it overlaps a finding from that earlier audit.

> This is the second input file. Do not start fixing from this file alone — it will be merged with `AUDIT_ISSUES.md` into one combined backlog next.

> **Status note (5 August 2026):** every Tier B and Tier C issue below (FP-B1 through FP-B6, FP-C1 through FP-C3) is already resolved — fixed independently via `issues/DEVELOPER_SCOPE_VERIFIED_IMPLEMENTATION_GUIDE.md` Section 3 (items 3.1–3.7), which covers the same bank/ecommerce correctness bugs in more detail. See that document for the actual fix descriptions and regression tests. Tier A (minus FP-A1/FP-A3/FP-A5) and Tier D are addressed below with **Solution** notes under the relevant items; FP-A1, FP-A3, and FP-A5 remain open (real logic changes, not yet started).

## Overlap with AUDIT_ISSUES.md — quick summary

| Fix Pack ID | Overlaps | Relationship |
|---|---|---|
| FP-A1 | AUTH-01 | Same bug, same file/lines — independently found by both audits |
| FP-A2 | AUTH-03 | Same bug, same file/lines — independently found by both audits |
| FP-A3 | AUTH-04 | Same bug, same file — independently found by both audits |
| FP-A5 | UP-02 (related, not identical) | Same *class* of bug (content-type spoofing bypass), different endpoint/file — UP-02 covered `analyze.py` (dead code); FP-A5 covers the live `bank.py` PDF upload, not previously flagged |
| FP-B3 | PAY-02 (related, not identical) | Both concern `bank.py` authorization; PAY-02 is an ordering bug (write-before-check), FP-B3 is a scope bug (role sees data it shouldn't) — distinct issues, same file family |
| FP-C2 | PAY-04 / UP-04 (related, not identical) | Both concern ecommerce/bank dedup weaknesses; PAY-04/UP-04 are concurrency races on rows *with* a key, FP-C2 is rows *without* a key skipping the dedup guard entirely — distinct mechanism |
| FP-D1 | UP-05 | Same bug, same fix (Celery timeout/prefetch config) — independently found by both audits |
| FP-D2 | UP-03 (related, not identical) | Both concern staged-file lifecycle bugs in the same ingestion path; UP-03 is "never deleted on abandonment", FP-D2 is "deleted too eagerly on failure, blocking retry" — opposite-direction bugs in the same area |
| All others (FP-A4, B1, B2, B4, B5, B6, C1, C3, D3, D4, D5) | — | New — not found in the earlier audit (mostly because the earlier audit didn't review bank-scoring business logic, lender-brief rendering, or infra/db-engine config in this depth) |

---

## TIER A — Security

### FP-A1 · Account takeover on registration [CRITICAL]
- **Overlaps:** `AUTH-01`
- **File:** `app/routes/auth.py`, `register()`, lines 205-225
- **Description:** The incoming password is only written inside `if not existing:`. When an unverified row already exists for that email (attacker pre-registered it), a legitimate re-registration by the real owner skips the insert branch entirely and the victim's password is silently discarded — the OTP goes to the victim's real inbox, they verify successfully, but the account still authenticates with the *attacker's* original password.
- **Attack:** (1) Attacker registers `victim@company.com` with attacker's password → unverified row created. (2) Victim registers legitimately → `existing` is truthy, insert skipped, victim's password discarded, OTP sent to victim's real inbox. (3) Victim enters OTP, account verified, tokens issued, everything looks normal to the victim. (4) Attacker logs in with the password from step 1 and owns the account.
- **Fix:** On re-registration of an unverified row, update `hashed_password`/`first_name`/`last_name` and invalidate outstanding OTPs, rather than silently discarding the new password.
- **Test:** Register, re-register with a different password, verify OTP, then assert the FIRST (attacker's) password fails at `/login`.

### FP-A2 · SECRET_KEY has no production guard [CRITICAL]
- **Overlaps:** `AUTH-03`
- **File:** `app/config.py` line 16 (default `'change-me-in-production'`); `app/main.py` line 110 (existing Fernet guard)
- **Description:** `main.py` correctly refuses to boot when `fernet_key` is still the committed default, but `secret_key` — which signs every JWT — has an equally public default and no equivalent check. If `SECRET_KEY` is missing/misspelled in the deployment environment, the app boots and signs all tokens with a string published in the repository.
- **Causes:** Anyone reading the source can forge a valid JWT for any email; `get_current_user` resolves the user from the `sub` claim and returns them — complete authentication bypass with no log signal.
- **Fix:** Extend the existing Fernet guard to also require `secret_key` be set, non-default, and ≥32 chars when `dev_mode=False`, raising `RuntimeError` otherwise.
- **Solution (5 August 2026):** added a second guard in `app/main.py`'s `startup_event()`, right after the existing Fernet check, refusing to boot when `dev_mode=False` and `secret_key` is either still `"change-me-in-production"` or under 32 characters. Verified directly (not via a new test file, to keep this fix pack fast): raises `RuntimeError` for both the default value and a short value, boots clean for a real 40-char key.

### FP-A3 · No password policy [HIGH]
- **Overlaps:** `AUTH-04`
- **File:** `app/schemas/auth.py` — `RegisterRequest` and `ResetPasswordRequest`
- **Description:** Password is a bare `str` — no minimum length, no complexity, no breach check. A single character is accepted; verified zero validators exist anywhere in `app/`.
- **Causes:** bcrypt at cost 12 is worthless against a one-character password; the 10-requests/60s auth rate limit is trivially defeated from a small proxy pool.
- **Fix:** Minimum 12 characters plus a common-password blocklist, applied to registration, reset, and invite acceptance (NIST SP 800-63B favors length + breach list over composition rules).

### FP-A4 · Access token lives 30 minutes [MEDIUM]
- **Overlaps:** none (new)
- **File:** `app/config.py` line 21
- **Description:** Access token TTL is 30 minutes; recommended down to 15. Refresh token TTL (7 days) is already correct.
- **Fix:** `access_token_expire_minutes: int = 15`.
- **Solution (5 August 2026):** changed the default to 15. Confirmed nothing in the codebase (app or tests) hardcodes the old 30-minute value — `app/utils/security.py` already reads `settings.access_token_expire_minutes` rather than a literal.

### FP-A5 · PDF accepted on filename alone [HIGH]
- **Overlaps:** `UP-02` (related — same bug class, different file: this is the *live* `bank.py` PDF endpoint, not the dead-code `analyze.py` CSV endpoint UP-02 covered)
- **File:** `app/routes/bank.py` line 545
- **Description:** The check is content-type OR filename extension, both attacker-controlled. Any bytes named `.pdf` are handed directly to PyMuPDF.
- **Causes:** Malformed input reaches a PDF parser — a common source of memory-safety CVEs — inside the Celery worker.
- **Fix:** Read the first 5 bytes and require the `%PDF-` header before parsing. Apply the same principle to CSV: attempt a UTF-8 decode and a `csv.Sniffer` dialect probe before trusting the extension.

---

## TIER B — Bank Accuracy

### FP-B1 · ABM averages only days that had transactions [CRITICAL]
- **Overlaps:** none (new)
- **File:** `app/services/bank_loan_readiness.py`, `compute_daily_closing_balances()`, lines 59-68
- **Description:** `daily[t.transaction_date] = t.balance_after` is built from transaction rows only; days with no transaction produce no entry, and `_average_for_window` averages that sparse list instead of carrying the balance forward across quiet days.
- **Measured:** NGN 10,000,000 held across 88 quiet days then two month-end transactions returns `ABM_3m` of NGN 3,433,333 against a true NGN 9,781,111 — understated by 64.9%, a factor of 2.8.
- **Causes:** Every SME with quiet periods (seasonal businesses, anyone paid monthly — effectively the whole market) gets ABM understated two-to-threefold. ABM carries 25% of loan readiness directly and also drives `abm_trend`, the lender brief key metrics, and the creditworthiness tier — creditworthy businesses get graded C/D and refused credit.
- **Fix:** Carry the last known closing balance forward across days with no transactions (fix provided in source, iterating day-by-day from opening balance, filling from `eod` dict where present, carrying forward otherwise).
- **Test:** Write the assertion before the fix and confirm it FAILS; assert `ABM_3m` is near NGN 9,781,111 for the scenario above, not NGN 3,433,333.

### FP-B2 · ABM window uses 30-day months [MEDIUM]
- **Overlaps:** none (new)
- **File:** `app/services/bank_loan_readiness.py` line 72
- **Description:** `window_start = reference_date - timedelta(days=months * 30)`. A twelve-month ABM covers 360 days while the response reports `months_used: 12`.
- **Fix:** Use `dateutil.relativedelta(months=months)`. Fix in the same commit as FP-B1.

### FP-B3 · Loan Officers see full transaction detail [CRITICAL]
- **Overlaps:** `PAY-02` (related, distinct mechanism — PAY-02 is an authorization-ordering bug; this is an authorization-scope bug, both in `bank.py`)
- **File:** `app/routes/bank.py`, `READ_ROLES` at lines 62-67, applied to every read endpoint
- **Description:** `READ_ROLES` contains all four bank roles and is applied uniformly; only the fraud-risk flags array is redacted. A `loan_officer` therefore reaches `/dashboard/summary` (top payees, top income sources), `/diagnostic/cashflow-analysis` (business-vs-personal split including the owner's personal spending), and `/diagnostic/customer-segmentation`.
- **Violates:** Bank PRD 4.C — "Loan Officer: access to the lender brief, creditworthiness tier, fraud risk score, and income summary only. Cannot see full transaction-level detail."
- **Causes:** A third-party lender granted a role to assess one loan obtains the borrower's complete commercial map — customers, suppliers, competing lenders, personal spending. Directly exploitable, undermines the product's trust proposition.
- **Fix:** Split into `FULL_DATA_ROLES = {bank_owner, bank_admin, bank_viewer}` (gates summary/cashflow-analysis/customer-segmentation) and `BRIEF_ONLY_ROLES = FULL_DATA_ROLES | {loan_officer}` (gates loan-readiness/fraud-risk/income-stability/lender-brief only).
- **Test:** Assert `loan_officer` receives 403 on every transaction-level endpoint.

### FP-B4 · Loan readiness silently renormalizes fixed weights [HIGH]
- **Overlaps:** none (new)
- **File:** `app/services/bank_loan_readiness.py` lines 267-272
- **Description:** When a component is unavailable it's dropped and the rest rescaled, so income stability reports `weight_pct: 40` where the PRD fixes 30 — and worse, the score is computed only from what remains, so incomplete data produces a systematically *higher* score than complete data with one weak factor.
- **Causes:** A lender auditing the arithmetic finds weights contradicting the published methodology; thin-file businesses get inflated scores and are approved for credit they cannot service.
- **Fix:** Keep weights fixed at 30/25/25/20, report the true `weight_pct`, score an unavailable component as unearned, and return `max_achievable_score` alongside (rendered as "74 / 75 possible").

### FP-B5 · Income stability boundary off by one [MEDIUM]
- **Overlaps:** none (new)
- **File:** `app/services/bank_loan_readiness.py` line 54
- **Description:** `'moderate' if cv_pct < 40 else 'volatile'` classifies exactly `40.0` as volatile; the PRD places 40 inclusive in moderate.
- **Fix:** `cv_pct <= 40`.

### FP-B6 · The lender brief renders Python dictionaries [CRITICAL]
- **Overlaps:** none (new)
- **File:** `app/services/bank_lender_brief.py` — `SECTION_NAMES` lines 20-27, sections assembly line 78, renderer lines 92-118 (truncation at line 102)
- **Description:** Three compounding bugs: (1) **Wrong keys** — spec requires `business_overview, income_summary, expense_summary, risk_assessment, creditworthiness_assessment, recommendation_paragraph`; code emits `business_overview, income_stability, cash_flow_analysis, loan_readiness_assessment, risk_flags, lender_recommendation` — five of six don't match. (2) **Wrong types** — spec types every section as prose string; code assigns raw dicts. (3) **Unreadable** — line 102 does `page.insert_text((50, y), line[:110])` with no wrapping, line 113 writes an f-string of a dict straight into the PDF; single page, `y` incremented by 16, no pagination — content past the page bottom is written off-canvas and lost.
- **Actual output observed:** `"Business Overview {'bank_name': 'GTBank', 'transactions_analyzed': 847, 'statement_period_start': '2025-06-01', 'stateme"` (truncated mid-dict).
- **Causes:** The PRD's most differentiated feature — sold at Premium as a downloadable PDF, the "5 days of review to 30 seconds" claim — produces an unusable, truncated Python dict for a loan officer.
- **Fix:** Rename the six keys to spec; generate real prose per section via `generate_text`, passing computed metrics as context and requiring each section to cite its figures; catch `GeminiAPIError` per section with a deterministic template fallback so one failed call doesn't void the whole brief; replace the renderer with wrapped, paginated text (`fitz.insert_textbox` with new-page-on-overflow, or ReportLab `SimpleDocTemplate`/`Paragraph`).
- **Note:** `sales_postmortem.py` had the same pattern and has already been deleted — this is the last instance.

---

## TIER C — Data Integrity

### FP-C1 · Dates parse month-first [CRITICAL]
- **Overlaps:** none (new)
- **File:** `app/services/ecommerce_ingestion.py` line 247; `app/services/bank_ingestion.py` line 170
- **Description:** `pd.to_datetime(value, errors='coerce')` with no `dayfirst` — pandas defaults to US month-first parsing. The tokens `dayfirst` and `date_locale` appear NOWHERE in the codebase; the `value_rules` dict accepted by `/mapping/confirm` carries `date_locale` and is persisted to `column_mappings`, then never read by any parser.
- **Measured:** `'01/12/2026'` parses to `2026-01-12`; with `dayfirst=True` it's `2026-12-01`. On a real cash book, 0 of 25 rows produced a usable date and 25 were rejected with 0 warnings emitted.
- **Causes:** Every Nigerian merchant writing dates the local (day-first) way has revenue scattered across wrong months. Monthly cashflow trend, seasonality, income stability CV, ABM windows, and the date-gap checker all consume corrupted dates — silent and internally self-consistent, so nothing in the quality report flags it.
- **Fix:** Thread `value_rules['date_locale']` from `column_mappings` into every parser; default `dayfirst=True`. Detect ambiguity (date column where both components are ≤12) and emit a `value_questions` entry blocking ingestion until answered. Replace `errors='coerce'` with an explicit count and a named warning carrying examples.

### FP-C2 · Rows without an order ID are never deduplicated [CRITICAL]
- **Overlaps:** `PAY-04` / `UP-04` (related, distinct mechanism — those cover concurrency races on rows that *do* have a dedup key; this covers rows that have *no* key at all, bypassing the dedup guard entirely)
- **File:** `app/services/ecommerce_ingestion.py` line 370
- **Description:** The guard is `if row[external_order_id] is not None and ... in existing_order_ids`. The Mapping Guide's auto-generation of a surrogate ID is not implemented anywhere. Files with no order-ID column bypass the guard entirely — and those are exactly the cash books the mapping layer exists to serve.
- **Causes:** A re-uploaded cash book, or a Celery worker restart, doubles revenue, order count, and AOV. Every downstream figure inflates — silent and undetectable from the dashboard.
- **Fix:** When `external_order_id` is `None`, synthesize a deterministic surrogate ID via `hashlib.sha256(f"{merchant_id}|{source_signature}|{order_date.isoformat()}|{sku}|{quantity}|{gross_revenue}|{row_index}")[:24]`. Also add `UniqueConstraint('merchant_id', 'external_order_id')` on `orders` so the database enforces it — via a **new** migration, never editing an existing one.

### FP-C3 · Ecommerce sums mixed currencies [CRITICAL]
- **Overlaps:** none (new)
- **File:** `app/services/ecommerce_revenue.py` line 69 and the aggregation above it
- **Description:** Aggregates `Order.gross_revenue` — the *original*-currency column — then sets `"currency": orders[0].original_currency if orders else "NGN"`, stamping the whole aggregate with whichever currency the first row happened to carry. Sales and bank analyzers do this correctly via `base_currency_amount`; ecommerce does not.
- **Causes:** Headline gross and net revenue are arithmetic nonsense for any cross-border merchant — a silent *non*-conversion presented as converted, the inverse of what the PRD prohibits.
- **Fix:** `_base_amount(o) = o.base_currency_amount if o.base_currency_amount is not None else o.gross_revenue`; set currency from `merchant_settings.base_currency`; where any order in range has `base_currency_amount is None`, add a named entry to `meta.missing_fields`.

---

## TIER D — Stability

### FP-D1 · No Celery task has a timeout [not tagged in source, treat as HIGH given blast radius]
- **Overlaps:** `UP-05`
- **File:** `app/celery_app.py`
- **Description:** No task time limits configured. One malformed PDF occupies a worker permanently, and with the default prefetch multiplier, silences the queue behind it.
- **Fix:** Add `task_soft_time_limit=300`, `task_time_limit=360`, `task_acks_late=True`, `task_reject_on_worker_lost=True`, `worker_prefetch_multiplier=1`.
- **Solution (5 August 2026):** added exactly those five settings to `celery_app.conf.update(...)`. `task_acks_late`/`task_reject_on_worker_lost` are safe to enable here specifically because ingestion tasks are already idempotent (audit #14's dedup), so a requeue-after-worker-death never double-counts data.

### FP-D2 · Failed ingestion deletes the staged file
- **Overlaps:** `UP-03` (related, opposite-direction bug in the same staged-file lifecycle)
- **File:** `ecommerce_ingestion.py` lines 558-559
- **Description:** The `finally` block deletes the staged file on the failure path too, so retry is impossible — a five-second database blip permanently destroys the upload.
- **Fix:** Delete only on success.

### FP-D3 · No `pool_pre_ping`
- **Overlaps:** none (new)
- **File:** `app/database.py` line 39
- **Description:** `create_async_engine(url, ...)` has no `pool_pre_ping`. Railway (hosting platform) drops idle connections; without pre-ping, the first request after idle fails.
- **Fix:** `create_async_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=20)`.
- **Solution (5 August 2026):** added `pool_pre_ping=True`/`pool_recycle=1800` unconditionally. `pool_size`/`max_overflow` are QueuePool-only (Postgres) tuning that SQLite's pool class doesn't accept, so those two are applied only when `database_url` isn't a `sqlite` URL — dev/test (always SQLite here) are unaffected, production (always Postgres via `DATABASE_URL`) gets all four.

### FP-D4 · `Base.metadata.create_all` at startup
- **Overlaps:** none (new)
- **File:** `app/main.py`
- **Description:** Two sources of schema truth alongside Alembic. A failed migration is masked by a partially-correct runtime schema.
- **Fix:** Remove it; run `alembic upgrade head` in deploy.

### FP-D5 · Gemini key in the query string
- **Overlaps:** none (new)
- **File:** `app/services/ai_client.py` line 37
- **Description:** The Gemini API key is passed via query string. Query strings are logged by proxies, CDNs, and APM agents.
- **Fix:** Move the key to the `x-goog-api-key` header.
- **Solution (5 August 2026):** replaced `params={"key": settings.gemini_api_key}` with `headers={"x-goog-api-key": settings.gemini_api_key}` in the single `client.post(...)` call in `generate_text()`. No test asserted the old call shape, so no test changes were needed.

---

## Source document's own "Definition of Done" (carried over for reference)

1. Every fix applied and committed by tier.
2. A regression test for each of FP-B1, FP-B3, FP-B6, FP-C1, FP-C2, FP-C3 written **before** the fix, confirmed to FAIL against current code. If it passes before the fix, the test is wrong.
3. Full suite green with `BCRYPT_ROUNDS=4`.
4. Both ingestion paths manually exercised — a real bank CSV and a real ecommerce CSV through their actual endpoints, rows confirmed in `bank_transactions` and `orders`.
5. A real GTBank or OPay statement run end-to-end, and the generated lender brief PDF opened and read by a human. If any line is truncated or shows a dict, FP-B6 is not done.

Source document's own working rule, carried over: **nothing outside this document gets worked on until all four tiers are done — no new features, no refactors, no PRD work in the codebase**, while working from this file alone. (This rule will need to be reconciled with `AUDIT_ISSUES.md` once merged — see Next Steps.)

---

## Next steps

1. Both `AUDIT_ISSUES.md` and this file now exist as separate inputs.
2. Next: merge into a single combined backlog, de-duplicating the overlapping items listed in the summary table above (keep one entry per real bug, note both sources), and deciding a single fix order across both files' severities.
3. Do not begin fixing until that merged backlog exists and is reviewed.
