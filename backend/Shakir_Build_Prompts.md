# Scanwick — Build Prompts for Shakir

## Your scope
Infra & DB foundation (migrations, Celery/Redis, S3, encryption, test scaffolding) →
the **Bank Statement analyzer**, end to end (ingestion → dashboards → predictive
models → AI lender brief) → the cross-cutting RBAC/billing/reconciliation wiring once
both verticals' RBAC is in place → repo cleanup.

You do **not** need Shoaib's file to do your work — everything you need is below. The
only times you need to coordinate with him directly are marked **"Sync with Shoaib"**.

---

## How every prompt works
Copy the text inside a `>` blockquote straight to your agent. Each one already tells
the agent to:
1. **Build** the one scoped change.
2. **Test** it — write and run automated tests (pytest); don't consider it done until
   they pass.
3. **Document** it — append a dated section to `docs/SYSTEM_DOCUMENTATION.md`.

Do one prompt → review the test output and the doc section it appended → then move to
the next. Don't batch multiple steps into one prompt.

**Terms used below:**
- **"per spec"** = matching the exact field names/response shapes in the original
  *Scanwick Developer Guide* PDF. Keep it accessible to your agent.
- **`is_anomalous`** = flag set when a record falls inside a contextual-marker date
  range. Must be excluded from dashboards and from anything a model trains on.
- **`is_own_account_transfer`** = a transfer between the same business's own bank
  accounts; excluded from inflow/outflow totals.
- **CSV ingestion** = wherever a task says "CSV," an uploaded `.xlsx` file is also
  accepted — both formats are parsed into the same canonical rows via a shared
  reader helper (`app/services/upload_staging.py`). Infrastructure detail, not a
  separate task.

---

## Files that are yours — Shoaib will never touch these
`migrations/`, `alembic.ini`, `services/storage.py`, `services/encryption.py`,
`docker-compose.yml`, the Celery/Redis block in `config.py`, `models/accounts.py`,
`models/bank_transactions.py`, `routes/bank.py`, `models/contextual_markers.py`,
`models/reconciliation_reports.py`, `models/merchant_settings.py`, `pyproject.toml`.

## Files you'll touch that Shoaib also touches (be careful here)
- `docs/SYSTEM_DOCUMENTATION.md` — append-only. Pull latest, add your section, commit,
  push immediately. Don't sit on edits to this file.
- `main.py` (router registration) — only add your own `include_router(bank_router, ...)`
  line; don't touch lines Shoaib added for ecommerce/sales.
- `middleware/rbac.py` — **only touch this in Phase 5, and only after confirming with
  Shoaib that he's pushed his 5.1/5.2 changes first.** See the Phase 5 section below.

## Git habit
One branch per task ID (e.g. `feature/1.20-bank-tables`), one small PR per task, pull
latest before starting your next task.

---

## PHASE 0 — Infra & DB Foundation

**0.1**
> We're going to build out the remaining Scanwick spec on top of the existing FastAPI
> backend. First, create `docs/SYSTEM_DOCUMENTATION.md` with a top section called
> "Architecture Snapshot" that accurately describes the current system as it exists today
> (auth, the CSV analyzer, the DB setup, what's NOT yet built: Celery, S3, migrations,
> tests, billing enforcement, contextual markers, canonical analyzer tables,
> reconciliation reports, RBAC). This is our running build log going forward — every
> future step appends to it.
>
> Test: none needed, this is documentation only — but verify the file renders as valid
> markdown.

**0.2**
> Set up Alembic for migrations against the existing SQLAlchemy models, keeping
> `Base.metadata.create_all` working for fresh dev DBs but adding versioned migrations
> for everything from here forward. Generate the initial migration capturing current
> models as-is.
>
> Test: run `alembic upgrade head` against a clean SQLite and Postgres test DB and confirm
> no errors and tables match the existing models.
>
> Document: append a "Migrations" section to `docs/SYSTEM_DOCUMENTATION.md` explaining the
> Alembic setup and how to create/run future migrations.

**0.3**
> Add Celery + Redis to the project (docker-compose service + app config). Add one trivial
> task (`ping_task`) wired through an endpoint `POST /api/internal/ping-task` purely to
> prove the worker, broker, and result backend all work end-to-end. Don't touch the CSV
> analyzer yet.
>
> Test: write a test that calls the ping endpoint and asserts the task result comes back
> within a timeout.
>
> Document: append an "Async Jobs (Celery)" section explaining the setup and how to add
> new tasks.

**0.4**
> Add S3-compatible file storage (real S3 in prod, local filesystem or MinIO in dev) with
> `upload_file(path, bytes) -> url` and `get_file_url(key)` helpers. Wire the existing
> `/api/analyze` CSV upload to also persist the raw file to this storage (in addition to
> whatever it does today), without changing its existing response behavior.
>
> Test: unit test the storage helpers; integration test that an uploaded CSV produces a
> retrievable URL.
>
> Document: append a "File Storage" section.

**0.5**
> Add Fernet field-level encryption helpers (`encrypt_field`/`decrypt_field`) and apply
> them to one real sensitive field that exists today — the bank account identifier(s)
> used in the bank-statement analyzer — replacing any plain storage with
> `account_number_hash` (SHA-256, one-way) for matching and Fernet for any reversible
> sensitive field you still need to read back.
>
> Test: confirm round-trip encryption/decryption, and confirm the raw account number is
> never present in the DB in plaintext (a test that queries the DB directly and asserts
> no plaintext match).
>
> Document: append an "Encryption" section noting exactly which fields are now encrypted
> and which are one-way hashed.

**0.6**
> Add a pytest test suite skeleton (`tests/` with conftest.py, fixtures for a test DB and
> an authenticated test client) since none exists yet. Write at least one smoke test per
> existing route file (`auth.py`, `analyze.py`) to lock in current behavior before we
> change anything else.
>
> Test: run the full suite, confirm green.
>
> Document: append a "Testing" section explaining how to run tests and what's covered so
> far.

**0.8 — Phase 0 checkpoint (Sync with Shoaib)**
> Run the full test suite and confirm: migrations apply cleanly, Celery ping task works,
> S3 upload/retrieve works, encryption round-trips. Append a "Phase 0 Checkpoint" section
> to the docs summarizing pass/fail for each. Shoaib is building his Gemini client and
> shared schemas (0.7, 1.3, 1.4) in parallel — confirm with him that his pieces are also
> green before you both move on.

---

## PHASE 1, Part A — Shared Schema (your half)

**1.1**
> Create the `contextual_markers` table (id, merchant_id, analyzer_type enum
> [ecommerce, sales, bank], label, start_date, end_date, created_by, created_at) as an
> Alembic migration + SQLAlchemy model. No endpoints yet.
>
> Test: migration applies cleanly up and down; model CRUD test.
>
> Document: append a "Contextual Markers" section with the schema.

**1.2**
> Create the `reconciliation_reports` table (id, merchant_id, analyzer_type,
> source_file_id, date_range_start, date_range_end, base_currency,
> exchange_rate_source, records_analyzed, records_excluded, exclusion_detail JSONB,
> disabled_features JSONB, contextual_markers_applied JSONB, created_at). Migration +
> model only.
>
> Test: migration + CRUD test, including round-tripping the JSONB fields.
>
> Document: append a "Reconciliation Reports" section.
>
> Note: as soon as you push this, tell Shoaib — his step 1.5 (reconciliation GET
> endpoint) depends on this table existing.

**1.6 — Phase 1, Part A checkpoint (Sync with Shoaib)**
> Run the full test suite. Append a checkpoint section confirming all shared
> tables/schemas are in place. Once this is green for both of you, you branch off into
> your own vertical (Bank) and won't need to touch shared files again until Phase 4.

---

## PHASE 1, Part D — Bank Statement Canonical Tables (your vertical, solo from here)

**1.20**
> Create `accounts` and `bank_transactions` tables exactly per spec (reusing the encrypted
> account-number handling from step 0.5). Migration + models only.
>
> Test: migration applies cleanly up and down; model CRUD test for both tables, including
> a test confirming account_number_hash is stored, not the plain number.
>
> Document: append schema docs for both tables to `docs/SYSTEM_DOCUMENTATION.md`.

**1.21**
> Build a CSV parser Celery task mapping generic bank CSVs into `bank_transactions`,
> reusing whatever parsing logic already exists in the bank-statement industry analyzer
> where applicable. PDF/OCR comes in the next step.
>
> Test: fixture CSV test asserting correct canonical rows.
>
> Document: ingestion docs.

**1.22**
> Build the OCR-based PDF parser for scanned bank statements feeding the *same* canonical
> insert function as the CSV path. Confirm identical downstream shape.
>
> Test: fixture scanned-PDF test (can use a synthetic/test PDF) asserting parity with the
> CSV path's output structure.
>
> Document: append PDF/OCR ingestion docs, including the >95% accuracy note as a stated
> target with how it'll be measured later.

**1.23**
> Build the Mono API ingestor for NG/GH/KE connecting directly (no file), inserting with
> data_source=mono_api through the same canonical function as CSV/PDF.
>
> Test: mock the Mono API and test the ingestion path end-to-end.
>
> Document: ingestion docs, noting the single shared canonical pipeline across all three
> sources.

**1.24**
> Implement the balance integrity check (opening + credits − debits vs closing, 0.01
> tolerance in base currency) and own-account-transfer detection/exclusion.
>
> Test: table-driven tests for pass/fail integrity and for transfer detection.
>
> Document: append docs for both rules.

**1.25**
> Implement currency conversion at transaction_date and contextual-marker flagging for
> bank_transactions.
>
> Test: a test asserting the historical rate at transaction_date is used (not today's
> rate); a test asserting a transaction inside a marker range gets is_anomalous=TRUE.
>
> Document: append docs explaining the rate-lookup and flagging logic for bank
> transactions.

**1.26**
> Build `GET /api/v1/bank/upload/{upload_id}/quality-report` with transactions_parsed,
> date_range, months_of_data, balance_integrity block, date_gaps, warnings — matching the
> spec shape exactly.
>
> Test: fixture test reproducing the spec's example output structure.
>
> Document: endpoint docs.

**1.27 — Phase 1 final checkpoint (Sync with Shoaib)**
> Run the full suite. Append a "Phase 1 Complete" section to the docs summarizing every
> table created, every ingestion path, and confirming all three analyzers share the
> reconciliation_reports + contextual_markers infrastructure consistently. Shoaib is
> finishing the Ecommerce and Sales ingestion paths in parallel — confirm both sides are
> green before moving to Phase 2.

---

## PHASE 2 — Bank Dashboards & Diagnostics

**2.12**
> Build `GET /api/v1/bank/dashboard/summary` per spec shape (inflows, outflows, balance
> block, credit_debit_split, top_payees_by_outflow, top_income_sources,
> monthly_cashflow_trend), excluding is_anomalous and is_own_account_transfer
> transactions.
>
> Test: integration test confirming both exclusion rules are applied to the totals.
>
> Document: append endpoint docs.

**2.13**
> Build `GET /api/v1/bank/diagnostic/income-stability`: coefficient of variation of
> monthly inflows, classified stable (<20%) / moderate (20–40%) / volatile (>40%) per
> spec. Disable with an explanatory message if there's less than 3 months of data.
>
> Test: one test per classification band, plus one test for the under-3-months disabled
> case.
>
> Document: append endpoint docs with the exact thresholds.

**2.14**
> Build `GET /api/v1/bank/diagnostic/abm`: 3/6/12-month average of daily closing
> balances (not transaction-point balances), with abm_trend.
>
> Test: a test that explicitly proves the calculation uses daily closing balances, not
> per-transaction balances (construct a fixture where the two methods would disagree).
>
> Document: append endpoint docs explaining the daily-closing-balance methodology.

**2.15**
> Build `GET /api/v1/bank/diagnostic/cashflow-analysis` per spec shape
> (cash_buffer_months, expense_concentration_ratio_pct, recurring_vs_variable,
> by_payment_mode, business_vs_personal).
>
> Test: integration test against a fixture statement with known recurring vs. variable
> outflows.
>
> Document: append endpoint docs.

**2.16**
> Build `GET /api/v1/bank/diagnostic/customer-segmentation` per spec shape (the four
> segment groups). Reuse any existing counterparty-grouping logic from the current bank
> analyzer where it genuinely fits, rather than rewriting it from scratch.
>
> Test: fixture test confirming counterparties land in the correct segment.
>
> Document: append endpoint docs, noting which existing logic was reused vs. newly built.

**2.17**
> Build `GET /api/v1/bank/diagnostic/revenue-patterns` per spec shape (peak day of
> month/week, monthly_index, seasonality_detected). Implement the
> seasonality_confidence="low" flag when months_available < 24, exactly as the spec
> requires.
>
> Test: a test with 12 months of data confirming seasonality_confidence is "low"; a test
> with 24+ months confirming it is not.
>
> Document: append endpoint docs with the 24-month threshold noted.

**2.18 — Phase 2 checkpoint (Sync with Shoaib)**
> Run the full suite, append a checkpoint section confirming every Bank endpoint's
> exclusion rules (is_anomalous, is_own_account_transfer) are correct. Confirm with
> Shoaib that his Ecommerce/Sales Phase 2 work is also green before moving to Phase 3.

---

## PHASE 3 — Bank Predictive Layer

**3.11**
> Build the fraud risk scoring model — reuse/extend the existing bank fraud-flag rules
> (round-number clustering, duplicate transactions, statistical outliers) into the
> spec's weighted score_breakdown (z_score, structuring, duplicate_payee,
> timing_anomaly). Build `GET /api/v1/bank/predictive/fraud-risk` with plain-language
> flag descriptions — no black-box flags.
>
> Test: fixture test with a known anomalous transaction asserting it's flagged with a
> human-readable description and correct score contribution.
>
> Document: append a "Fraud Risk Scoring" section explaining each flag type and weight.

**3.12**
> Build the loan readiness score: income_stability(30%) + abm_trend(25%) +
> fraud_risk_inverted(25%) + cash_buffer(20%). Build
> `GET /api/v1/bank/predictive/loan-readiness` with full score_breakdown,
> improvement_recommendations, and estimated_debt_coverage_indicator.
>
> Test: a test that reruns the same statement twice and asserts the score is stable
> within 1 point, per the spec's stability requirement.
>
> Document: append a "Loan Readiness Score" section with the weighting formula.

**3.13**
> Build `GET /api/v1/bank/predictive/cashflow-forecast`: 90-day daily forecast with
> confidence bands, cash_runway primary/stress scenarios, and
> recurring_commitments_projected.
>
> Test: integration test asserting 90 daily forecast points and that the stress scenario
> produces a shorter runway than the primary scenario.
>
> Document: append endpoint docs.

**3.14 — Phase 3 checkpoint (Sync with Shoaib)**
> Run the full suite. Append a checkpoint confirming the fraud-risk and loan-readiness
> models exclude is_anomalous records and that every minimum-data threshold triggers the
> correct disabled-feature response instead of an error. Confirm with Shoaib that his
> Ecommerce/Sales predictive models are also green.

---

## PHASE 4 — AI Layer (your part)

**4.1 — Build together with Shoaib (pair up for this one)**
> Build the shared `generate_recommendations(analyzer_type, context_data)` service on
> top of the Gemini client Shoaib built in step 0.7, validating every returned
> recommendation against the AIRecommendation schema he built in step 1.4 and dropping
> any that's missing a required field.
>
> Test: mock Gemini returning one valid and one invalid (missing-field) recommendation,
> asserting only the valid one survives.
>
> Document: append a "Recommendation Generation Service" section.
>
> Note: this is the one task in Phase 4 you should sit down and do together — both of
> you need it for your own playbook endpoints right after.

**4.6**
> Build `GET /api/v1/bank/ai/lender-brief`: must generate within 10 seconds of analysis
> completion, populate all six sections plus key_metrics and data_source_footnote, and
> produce a PDF in S3.
>
> Test: a timing test asserting generation completes within the 10-second budget (using
> a mocked Gemini call with realistic latency); a content test asserting all six
> sections and key_metrics are present.
>
> Document: append endpoint docs including the measured generation time from the test
> run.

**4.7**
> Build `GET /api/v1/bank/ai/financial-health-playbook` using the shared service from
> 4.1.
>
> Test: same pattern as your other playbook endpoints, bank-specific fixtures.
>
> Document: append endpoint docs.

**4.8 — Phase 4 checkpoint (Sync with Shoaib)**
> Run the full suite. Append a checkpoint confirming your bank recommendations validate
> against the shared AIRecommendation schema. Confirm with Shoaib that his Ecommerce/
> Sales playbooks (plus his Win DNA and post-mortem automation) are also green.

---

## PHASE 5 — Bank RBAC, then Cross-Cutting Wiring

**5.3 (do this in parallel with Shoaib's 5.1/5.2 — different files, no conflict)**
> Implement RBAC for the four bank roles, especially confirming Loan Officer never
> receives transaction-level detail in any response.
>
> Test: one test per role per endpoint group, plus a specific test asserting the Loan
> Officer role's response from every bank endpoint excludes transaction-level fields.
>
> Document: append an "RBAC — Bank" section listing every role/endpoint pairing tested.

**Wait here.** Steps 5.4–5.6 touch the Ecommerce, Sales, and Bank route files all at
once. Don't start them until Shoaib confirms his 5.1 (Ecommerce RBAC) and 5.2 (Sales
RBAC) PRs are merged — pull latest after he confirms, then continue.

**5.4**
> Confirm and test that all roles with read access (including Analyst) can reach
> `GET /api/v1/reconciliation/{analysis_run_id}`.
>
> Test: one test per role asserting each can successfully read a reconciliation report.
>
> Document: append a note to the RBAC docs confirming reconciliation-report read access
> is universal across roles, as required by the spec.

**5.5**
> Wire reconciliation_reports to be written on every analysis run across all three
> analyzers, and confirm every dashboard metric's `meta.analysis_run_id` resolves to a
> real, accurate record.
>
> Test: for one run per analyzer, assert the reconciliation record's records_analyzed/
> excluded counts match the actual data.
>
> Document: append a "Reconciliation Wiring" section.

**5.6**
> Implement the billing/entitlement enforcement for the `basic`/`premium` tier markers
> that already exist in the health-score code but aren't enforced. Gate the relevant
> premium endpoints/features behind a real subscription-status check tied to the user
> model.
>
> Test: test that a basic-tier user gets a clear "upgrade required" response (using the
> standard error envelope) on premium-gated features, and a premium user doesn't.
>
> Document: append a "Billing & Entitlements" section listing exactly which features are
> gated and how the check works.

**5.7**
> Update `pyproject.toml` metadata to correctly describe the FastAPI backend (fix the
> stale "Flask backend" description) and do a final dependency audit.
>
> Test: confirm `pip install`/build still works after metadata changes.
>
> Document: append a "Cleanup" note.

**5.8 — Final checkpoint (Sync with Shoaib)**
> Run the entire test suite end to end. Append a final "System Complete" section to
> `docs/SYSTEM_DOCUMENTATION.md` that includes: a table of every endpoint implemented
> across all three analyzers, every DB table, every Celery task, and a pass/fail summary
> against the Definition-of-Done targets from the original developer guide. Do this one
> together with Shoaib — it's a full-system review covering both of your work.

---

### Reminder
Don't skip the Test or Document part of any prompt. If a "Sync with Shoaib" step says
to confirm something with him first, actually do that before proceeding — those are the
points where your work and his come together.
