# Scanwick — QA Testing Scripts (Real Dataset Validation Phase)

## Scope
This file is the QA counterpart to `Shakir_Build_Prompts.md` / `Shoaib_Build_Prompts.md`.
Those covered **Build → Test → Document** during development, task by task (0.1 → 5.8),
across the shared infrastructure (migrations, Celery/Redis, S3, encryption, contextual
markers, reconciliation_reports, response envelope, AIRecommendation schema, RBAC,
billing) and the three verticals (Bank, Ecommerce, Sales).

This phase covers **Run → Verify → Document** — exercising the already-built system
against real dataset files sitting in the project folder, one analyzer at a time, one
script at a time, in this order: **Bank → Ecommerce → Sales → Shared Integration**.

---

## Where results get saved

Every script below tells the agent to write its findings to a specific file under a
`tests/` directory in the project root — not just report back in chat.

### Folder structure
```
tests/
  results/
    bank/
      01_dataset_inspection.md
      02_ingestion.md
      03_dashboard.md
      04_diagnostics.md
      05_predictive.md
      06_ai_layer.md
      07_final_validation.md
    ecommerce/
      01_dataset_inspection.md
      ... (same pattern)
    sales/
      01_dataset_inspection.md
      ... (same pattern)
    integration/
      01_reconciliation.md
      02_contextual_markers.md
      03_rbac.md
      04_billing.md
      05_response_envelope.md
      06_final_system_validation.md
  QA_LOG.md   ← append-only running summary, one line per script run
```

### Naming convention
`tests/results/{analyzer}/{NN}_{short_name}.md` — number matches the script's position
in that analyzer's 7-part sequence (or the integration set's 6-part sequence).

### QA_LOG.md line format
```
{date} | {Analyzer} {NN} — {Short Name} | PASS / PASS WITH ISSUES / FAIL | {one-line summary} | {result file path}
```

---

## Standard prompt template (applies to every script from here on)

Every script in this file — Bank, Ecommerce, Sales, or Integration — is built to this
same shape:

1. **Explicit scope boundary up front** — state exactly what this step is (e.g.
   read-only inspection, ingestion-only, dashboard-only) and what it is *not*
   (no DB writes, no code changes, no modifying source datasets) unless the step's
   whole purpose is to do that thing.
2. **Ground the "canonical/expected behavior" in the real repo, not the spec text.**
   Every canonical field, endpoint shape, threshold, or business rule referenced must
   be located and cited from the actual implementation — models, migrations,
   `routes/*.py`, `docs/SYSTEM_DOCUMENTATION.md` — not assumed from the original build
   prompts, since the spec describes intent, not necessarily what got built. If it
   can't be confidently located, that is itself a blocker to report, not something to
   guess past.
3. **Fixed core scope, prior findings only extend it.** Each subsequent prompt in a
   sequence (e.g. Bank 02 after Bank 01) must preserve its predefined core validation
   scope. Findings from the immediately preceding script may add *follow-up checks* to
   that prompt's checklist — they must not replace, narrow, or redefine the prompt's
   primary purpose. This keeps all ~27 scripts structurally stable and comparable even
   as each one picks up context from the last.
4. **Evidence discipline.** For every claimed canonical field, endpoint behavior,
   threshold, permission rule, or dashboard metric, the result file must cite the exact
   implementation source used to verify it:
   - file path
   - relevant class/function/model/route name
   - line number range if available
   - a short explanation of what that source confirms
   A bare filename with no function/line reference is not sufficient evidence and
   should be flagged as such rather than accepted.
5. **Use the global result-file structure** (below), extended with analyzer-specific
   subsections where needed — never invented from scratch per prompt.
6. **A one-line QA_LOG.md append** in the fixed format above, every time.

---

## Standard result-file structure (applies to every QA script)

Every result file under `tests/results/**` uses this numbered skeleton unless a
specific prompt explicitly adds analyzer-specific subsections under one of these
numbers:

```
1. Run metadata
   (date/time, analyst/agent, branch/commit if available, files/endpoints inspected)
2. Repo/source references used for verification
   (per the Evidence discipline rule above — file path, class/function/route,
   line range, what it confirms)
3. Scope summary
   (dataset(s) or endpoint(s) covered in this run; core scope + any inherited
   follow-up checks from the prior script, listed separately)
4. Detailed findings tables
   (analyzer/prompt-specific — mapping tables, response-shape checks, threshold
   checks, etc.)
5. Issues found
   (Critical / Warning / Minor — each with location and why it matters)
6. Pass/fail checklist
   (one line per check defined in this prompt's scope)
7. Overall verdict
   (PASS / PASS WITH ISSUES / FAIL, with brief reasoning)
8. Next-step readiness / blockers
   (can the next script in sequence proceed immediately, proceed with caution, or is
   it blocked pending fixes — and if follow-up checks are being handed to the next
   script, list them explicitly here)
```

Individual prompts below reference this by saying "use the standard result-file
structure, with the following prompt-specific content for sections 3–6" rather than
repeating the full skeleton each time.

---

## BANK ANALYZER

*(Context only: the Bank vertical was primarily built across Shakir's task range
1.20–1.25 / 2.12–2.17 / 3.11–3.13 / 4.6–4.7 / 5.3. These task references are navigation
hints for locating implementation artifacts — they are not the verification source of
truth. Verification must still be grounded in the actual repo code, migrations, routes,
and `docs/SYSTEM_DOCUMENTATION.md`, per the Evidence discipline rule above.)*

### Bank Test Prompt 1 — Dataset Inspection + Schema Mapping

> We are now in the **QA/testing phase** for the **Bank Statement analyzer**. This step
> is **read-only dataset inspection and schema-mapping verification only**. **Do not run
> ingestion, do not write to the database, do not modify source datasets, and do not
> patch application code in this step.**
>
> ### Datasets to inspect
> Use these files from the project folder:
> - `scanwick_test_bank_statement.csv` **(primary test input)**
> - `scanwick_bank_savings_clean.csv`
> - `scanwick_bank_wallet_clean.csv`
>
> **Pre-QA alignment note (2026-07-07):** a prior alignment audit found and fixed a
> real ingestion bug affecting all three files: `_CREDIT_KEYWORDS` in
> `app/services/bank_ingestion.py` included the bare token `"cr"`, which matched as a
> substring of the ordinary word `"description"` (a narration column present in all
> three files, positioned before the real `credit` column) — this silently zeroed
> every credit-side transaction's amount on ingestion. Fixed and regression-tested
> (`tests/services/test_bank_ingestion.py::test_credit_column_not_shadowed_by_a_narration_column_containing_cr`).
> No action needed here, just don't be surprised if inflow figures now look larger
> than an earlier manual run — that's the fix, not new noise.
>
> ### Objective
> Inspect the columns, structure, and raw values of all three files and verify how they
> map to the **canonical Bank analyzer schema** already implemented in the project.
>
> ### Canonical schema source of truth
> Before mapping, locate and cite the actual source of truth for the canonical schema
> from the project code/docs — do not guess from the original build-prompt spec text.
> Look for it in (these task numbers are navigation hints only, not proof — verify
> against the real files):
> - bank analyzer models (`models/accounts.py`, `models/bank_transactions.py`)
> - migration files (Alembic revisions covering the accounts/bank_transactions tables)
> - `docs/SYSTEM_DOCUMENTATION.md` (schema docs sections + the encryption section
>   covering `account_number_hash`)
> - `routes/bank.py` if it reveals field usage
>
> Per the **Evidence discipline** rule: for every canonical field you confirm, cite the
> exact file, class/model name, and line range where it's defined — not just the
> filename.
>
> The canonical fields expected for this inspection include fields such as:
> `transaction_date`, `amount`, `original_currency`, `base_currency_amount`,
> `is_anomalous`, `is_own_account_transfer`, `account_number_hash` — and any additional
> canonical fields actually defined in the project's implemented Bank schema.
>
> ### Required checks
> For **each of the three datasets**, verify and document:
>
> **1. Source → canonical field mapping**
> - Which source columns map **1:1** to canonical fields
> - Which source columns require **normalization/transformation** before fitting
>   canonical fields
> - Which canonical fields have **no source column** and would therefore be
>   null/derived/defaulted during ingestion
> - Which source columns appear **extra/unused/unmapped**
>
> **2. Cross-file structural consistency** — column names, column order (if relevant),
> data types/value patterns, date formats, amount formatting, debit/credit
> representation, currency representation, account identifier format.
>
> **3. Data quality issues that could break ingestion** — missing/malformed dates,
> non-numeric/malformed amounts, empty mandatory columns, duplicate headers, encoding
> issues, inconsistent currency formatting, unexpected null patterns, obviously invalid
> transaction rows.
>
> ### Deliverable format
> Save results to `tests/results/bank/01_dataset_inspection.md` (create the folder
> structure if it doesn't exist yet). **Use the standard result-file structure** (see
> top of this document), with the following Bank-specific content:
>
> - **Section 2** — the canonical schema source references located, with file/class/
>   line-range evidence per field, per the Evidence discipline rule.
> - **Section 3** — per-file summary (filename, row count, column count, header list);
>   this is the first script in the sequence, so there are no inherited follow-up
>   checks yet.
> - **Section 4** — a source-to-canonical mapping table **per dataset**:
>   `Source Column | Sample Values / Observed Format | Canonical Field | Mapping Type`
>   (`direct` / `transformed` / `derived` / `default-null` / `unused`), plus a
>   sub-section listing canonical fields missing from each source and how they'd
>   likely be populated (null/default/derived/unsupported), plus a cross-file
>   consistency assessment.
> - **Section 5** — every data-quality/ingestion-risk finding with severity.
> - **Section 6** — checklist: canonical schema located from real project sources /
>   all columns mapped or explicitly marked unmapped / missing canonical fields
>   identified / extra source columns identified / cross-file consistency assessed /
>   ingestion blockers identified.
> - **Section 8** — explicit statement of whether Bank Test Prompt 2 (Ingestion) can
>   proceed immediately, proceed with caution, or is blocked — and if any follow-up
>   checks should be added to Prompt 2's scope as a result of this run, list them here
>   explicitly (they will extend, not replace, Prompt 2's core scope).
>
> ### QA log update
> Append one line to `tests/QA_LOG.md`:
> `{date} | Bank 01 — Dataset Inspection | PASS / PASS WITH ISSUES / FAIL | {short summary} | tests/results/bank/01_dataset_inspection.md`
>
> ### Important constraints
> - This step is **inspection only** — no ingestion, no DB writes, no dataset edits, no
>   code changes.
> - Use the **actual implemented Bank analyzer schema from the repo/docs**, not
>   assumptions from the original spec.
> - If the canonical schema cannot be confidently located, mark that explicitly as a
>   blocker instead of guessing.

---

### Bank Test Prompt 2 — Ingestion Testing

> **Prerequisite:** Bank Test Prompt 1 must show a verdict of PASS or PASS WITH ISSUES
> before running this. If Prompt 1 found ingestion-blocking issues, resolve or
> explicitly accept them first.
>
> **Scope boundary:** This step runs the actual ingestion pipeline against the three
> Bank datasets and writes to the database (dev/test environment only — confirm you
> are not pointed at a production database before proceeding). Do not modify ingestion
> code in this step; only run it and observe.
>
> **Core objective:** Run `scanwick_test_bank_statement.csv`, then
> `scanwick_bank_savings_clean.csv`, then `scanwick_bank_wallet_clean.csv` through the
> real ingestion path (CSV upload → parser → canonical insert), one at a time, and
> verify:
> - Row counts in vs. rows actually inserted into `accounts`/`bank_transactions`
>   (account for any rows correctly rejected/skipped, and confirm *why* each was
>   skipped)
> - `is_own_account_transfer` correctly flags transfers between the user's own accounts
>   (per the implemented detection logic — cite the actual function used)
> - `is_anomalous` flagging fires per the implemented rule (cite it), not just on rows
>   that look obviously odd to a human
> - Currency conversion: `original_currency` → `base_currency_amount` produces correct
>   converted values (spot-check several rows against the actual FX source/rate used)
> - `account_number_hash` is actually hashed, not stored in plaintext
> - Duplicate-ingestion behavior: re-running the same file a second time — does it
>   correctly detect/skip duplicates, or does it double-insert?
> - Any encoding/malformed rows flagged in Prompt 1 — confirm whether they were
>   actually rejected, silently coerced, or silently dropped (all three are different
>   outcomes and must be distinguished)
>
> **Follow-up checks (if any) from Bank Prompt 1:** incorporate whatever specific
> items Prompt 1's Section 8 flagged for this step, as additions to the above — not
> replacements.
>
> **Deliverable:** `tests/results/bank/02_ingestion.md`, using the standard
> result-file structure. Section 4 should include a per-dataset table:
> `Check | Expected Behavior (cited source) | Observed Behavior | Result`.
> Section 8 must state whether Prompt 3 (Dashboard) can proceed, and list any
> follow-ups for it.
>
> **QA log:** append to `tests/QA_LOG.md` in the standard format.

---

### Bank Test Prompt 3 — Dashboard Endpoint Testing

> **Prerequisite:** Bank Test Prompt 2 PASS or PASS WITH ISSUES, using the data it
> ingested.
>
> **Scope boundary:** Read-only endpoint testing against already-ingested data. No new
> ingestion, no code changes.
>
> **Core objective:** Locate the actual Bank dashboard endpoint(s) in `routes/bank.py`
> (or equivalent) — cite exact route path(s), do not assume a path from the original
> spec without confirming it in code — and call them against the ingested test data.
> Verify:
> - Response follows the shared envelope (`success`, `data`, `meta` with
>   `missing_fields`/`disabled_features`/`analysis_run_id`) — cite the shared envelope
>   implementation used to confirm the shape
> - Every summary figure returned (balances, totals, trend figures, whatever the real
>   endpoint returns) is independently recomputed by hand/script from the ingested rows
>   and matches
> - Anomalous/own-transfer rows are correctly excluded from the aggregates where the
>   spec requires exclusion (cite the exclusion logic)
> - `disabled_features` correctly appears when the ingested dataset doesn't meet the
>   minimum-data threshold for a given feature (cite the actual threshold check in
>   code, e.g. "<3 months of data") — you may need to test this with a deliberately
>   short-window subset of one dataset if the full test file exceeds the threshold
>
> **Follow-up checks from Prompt 2:** incorporate as additions.
>
> **Deliverable:** `tests/results/bank/03_dashboard.md`, standard structure. Section 4:
> a table of `Metric | Recomputed Value | Endpoint Returned Value | Match?`.

---

### Bank Test Prompt 4 — Diagnostics Endpoint Testing

> **Prerequisite:** Bank Prompt 3 PASS or PASS WITH ISSUES.
>
> **Scope boundary:** Read-only endpoint testing.
>
> **Core objective:** Locate and test each implemented Bank diagnostic endpoint (the
> spec described income-stability, ABM, cashflow-analysis, customer-segmentation, and
> revenue-patterns — confirm which of these actually exist in the repo and at what
> route paths; do not assume all five were built). For each one that exists:
> - Cite the calculation logic used (file/function/line range)
> - Recompute the underlying calculation independently against the ingested data and
>   compare to the endpoint's output
> - Check edge behavior: what happens when the dataset is too small/uniform for the
>   diagnostic to be meaningful (does it degrade gracefully via `disabled_features`, or
>   error?)
> - Note any of the five spec'd diagnostics that don't appear to be implemented at all
>   — flag as a finding, not a blocker for this test (that's a build-completeness gap,
>   not a QA failure of this step)
>
> **Deliverable:** `tests/results/bank/04_diagnostics.md`, standard structure.

---

### Bank Test Prompt 5 — Predictive Model Testing

> **Prerequisite:** Bank Prompt 4 PASS or PASS WITH ISSUES.
>
> **Scope boundary:** Read-only endpoint testing, plus one volume/stress run.
>
> **Core objective:** Locate and test the implemented Bank predictive endpoints
> (fraud-risk, loan-readiness, cashflow-forecast — confirm which exist and their
> actual route paths/model implementation files). Then:
> - Run the three primary Scanwick test datasets through each model and sanity-check
>   outputs (scores in valid range, forecasts directionally reasonable given the
>   underlying transaction trend)
> - Run `PS_20174392719_1491204439457_log.csv` (PaySim) specifically through the
>   fraud-risk model as a volume/labeled-data stress test, since this dataset carries
>   an `isFraud` ground-truth column — compare model flags against it and report
>   precision/recall at whatever threshold the model uses (cite the threshold from
>   code). **Note:** PaySim's own columns (`step, type, amount, nameOrig,
>   oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud,
>   isFlaggedFraud`) don't match `bank_transactions` at all — this can't go through
>   the normal CSV ingestion path. Score it directly against the fraud-risk model's
>   own feature functions instead (a custom mapping from PaySim's fields to whatever
>   inputs `compute_fraud_risk` takes), not via `ingest_bank_csv`. Also: **471MB** —
>   read in chunks (`pd.read_csv(..., chunksize=...)`), never load whole
> - Confirm the model degrades gracefully (not with an unhandled error) on datasets
>   below its minimum-data threshold
>
> **Deliverable:** `tests/results/bank/05_predictive.md`, standard structure. Include a
> dedicated subsection under Section 4 for the PaySim fraud-risk precision/recall
> results.

---

### Bank Test Prompt 6 — AI Layer Testing

> **Prerequisite:** Bank Prompt 5 PASS or PASS WITH ISSUES.
>
> **Scope boundary:** Read-only endpoint testing. If AI generation calls an external
> LLM API, confirm cost/rate-limit implications before running repeatedly.
>
> **Core objective:** Locate and test the implemented Bank AI endpoints (lender-brief,
> financial-health-playbook — confirm actual route paths). For each:
> - Confirm the output validates against the shared `AIRecommendation` schema (cite the
>   schema definition file) — flag any output that doesn't conform or that gets
>   silently dropped
> - Confirm the AI narrative content is actually grounded in the analyzer's own
>   computed data (dashboard/diagnostics/predictive outputs) rather than generic or
>   hallucinated content — spot check specific numbers mentioned in the AI output
>   against the underlying data
> - Test behavior when underlying data is sparse (does it produce a reasonable
>   "insufficient data" response or a confidently wrong one?)
>
> **Deliverable:** `tests/results/bank/06_ai_layer.md`, standard structure.

---

### Bank Test Prompt 7 — Bank Analyzer Final Validation Report

> **Prerequisite:** Bank Prompts 1–6 all completed (any status).
>
> **Scope boundary:** No new testing — this is a consolidation/synthesis step.
>
> **Core objective:** Read all six prior Bank result files and produce one consolidated
> final report:
> - One-paragraph summary per prior script (dataset inspection → ingestion →
>   dashboard → diagnostics → predictive → AI)
> - A single running table of every Critical/Warning issue found across all six
>   scripts, with current status (open/resolved)
> - An overall Bank Analyzer verdict: READY FOR INTEGRATION TESTING / READY WITH
>   OPEN ISSUES / NOT READY
> - Explicit list of anything that should feed into Integration testing (e.g. if
>   reconciliation figures from Prompt 3/4 need to be checked against the
>   `reconciliation_reports` table in Integration Prompt 1)
>
> **Deliverable:** `tests/results/bank/07_final_validation.md`, standard structure
> (Section 4 becomes the consolidated issue table; Section 8 states integration
> readiness).
>
> **QA log:** append a final Bank-analyzer summary line to `tests/QA_LOG.md`.

## ECOMMERCE ANALYZER

*(Context only: the Ecommerce vertical was primarily built across Shoaib's task range
1.7–1.14 / 2.1–2.11 / 3.1–3.10 / 4.2–4.4 / 5.1. These task references are navigation
hints for locating implementation artifacts — they are not the verification source of
truth. Verification must still be grounded in the actual repo code, migrations, routes,
and `docs/SYSTEM_DOCUMENTATION.md`, per the Evidence discipline rule.)*

### Ecommerce Test Prompt 1 — Dataset Inspection + Schema Mapping

> **Scope boundary:** Read-only inspection only. No ingestion, no DB writes, no
> dataset edits, no code changes.
>
> **Datasets to inspect:**
> - `scanwick_test_ecommerce_orders.csv` **(primary test input)** — ingest with
>   `source=generic_csv` (see Pre-QA alignment note below), not `shopify_csv`/`woocommerce_csv`
> - `ecommerce_orders_10k_updated.csv` (volume test) — same `source=generic_csv`;
>   note it has no `sku`/`cogs`/`customer_email` columns at all, so it's a
>   row-count/volume test only, not a COGS or SKU-level fidelity test
> - ~~`diversified_ecommerce_dataset.csv`~~ **excluded** — this is a product catalog
>   (Price/Discount/Stock Level/Customer Age Group/Return Rate/Seasonality), not a
>   transaction dataset at all: no `order_id`, `order_date`, or `customer_id`. Cannot
>   be mapped onto `orders` regardless of ingestion source; do not use it here
> - `product-supplier.csv` (hyphen, not underscore — the file is named
>   `product-supplier.csv`) — **note this file has no cost/price column at all**
>   (Product ID/Line/Category/Group/Name, Supplier Country/Name/ID only), so it
>   cannot actually serve as a COGS/supplier-fallback source despite the label below.
>   If you need a real per-unit cost reference, `archive (19)/orders.csv`'s
>   `Cost Price Per Unit` column is the better (currently unused) candidate
> - The Olist set (`olist_orders_dataset.csv`, `olist_order_items_dataset.csv`,
>   `olist_order_payments_dataset.csv`, `olist_customers_dataset.csv`,
>   `olist_products_dataset.csv`, `olist_sellers_dataset.csv`,
>   `olist_geolocation_dataset.csv`, `olist_order_reviews_dataset.csv`,
>   `product_category_name_translation.csv`) as a real multi-table join/ingestion
>   stress test — note this set is NOT pre-shaped to Scanwick's schema, and has no
>   `generic_csv`/Shopify/WooCommerce column map of its own yet (would need one
>   built, or the 9 files joined into one Shopify/WooCommerce-shaped CSV first)
> - ~~`df_Customers.csv`, `df_OrderItems.csv`, `df_Orders.csv`, `df_Payments.csv`,
>   `df_Products.csv`~~ **excluded** — confirmed these are a train/test-split
>   subset of the Olist set's own columns (e.g. `df_Orders.csv` has 4 of Olist's 8
>   `orders` columns), not a separate/independent dataset; testing both is redundant
>
> **Pre-QA alignment note (2026-07-07):** `scanwick_test_ecommerce_orders.csv` and
> `ecommerce_orders_10k_updated.csv` previously could not ingest correctly under
> either `shopify_csv` or `woocommerce_csv` — verified empirically: `sku`/`unit_cogs`/
> `customer_email`/`original_currency`/`channel`/`discount_amount`/`refund_amount`/
> `shipping_cost` all resolved to `None`, and `gross_revenue` incorrectly resolved to
> `unit_price`. A new `OrderDataSource.generic_csv` source was added
> (`app/services/ecommerce_ingestion.py::GENERIC_COLUMN_MAP`) that maps these files'
> own canonical-named columns directly. Use `source=generic_csv` for both files in
> Prompt 2. Verified: 982/982 rows now ingest with 0 missing `sku`/`unit_cogs`.
>
> **Objective:** Map all of the above onto the canonical `orders`/`order_items`/
> `returns` schema. Locate and cite the actual implementation (models, migrations,
> `docs/SYSTEM_DOCUMENTATION.md`) — do not assume field names from the original spec.
> Expected canonical fields to look for include order/line-item identifiers, SKU,
> quantity, unit price, COGS/cost fields (and the SKU-override → merchant-default →
> zero fallback rule), currency, order/return timestamps, and channel/source fields —
> plus any others actually defined in the repo.
>
> **Required checks (per dataset):** source→canonical mapping (direct/transformed/
> derived/default-null/unused), cross-file structural consistency, and data-quality
> issues that would break ingestion (malformed prices, missing SKUs, currency mixing,
> encoding issues, duplicate order IDs, orphaned order_items with no parent order).
> For the Olist set specifically, also assess how the multi-table joins (orders ↔
> items ↔ payments ↔ products ↔ sellers) would need to be flattened before they'd fit
> the single-file ingestion path, and whether the current ingestion pipeline can
> actually handle a multi-file/joined source at all.
>
> **Deliverable:** `tests/results/ecommerce/01_dataset_inspection.md`, standard
> result-file structure, mirroring Bank Prompt 1's Section 4 mapping-table format
> per dataset. Section 8 states whether Ecommerce Prompt 2 can proceed and lists
> follow-ups.
>
> **QA log:** append to `tests/QA_LOG.md`.

---

### Ecommerce Test Prompt 2 — Ingestion Testing

> **Prerequisite:** Ecommerce Prompt 1 PASS or PASS WITH ISSUES.
>
> **Scope boundary:** Runs real ingestion, writes to dev/test DB only. No code changes.
>
> **Core objective:** Ingest `scanwick_test_ecommerce_orders.csv` first (source=
> `generic_csv`), then `ecommerce_orders_10k_updated.csv` (source=`generic_csv`,
> volume run), then attempt the Olist set per whatever multi-file handling Prompt 1
> determined is actually possible. `diversified_ecommerce_dataset.csv` is excluded
> per Prompt 1 (not a transaction dataset). Verify:
> - Row counts in vs. inserted into `orders`/`order_items`, with reasons for any
>   skipped rows
> - COGS fallback logic: SKU-level override → merchant default → zero — cite the
>   actual implementation. Note: `product-supplier.csv` (hyphen) has no cost column
>   and cannot serve as a real override source (see Prompt 1) — test this tier using
>   a merchant-default `default_return_cost`/manually-seeded SKU override instead,
>   or accept that this tier is untestable against currently available data
> - `net_margin` calculation correctness — recompute by hand for a sample of orders
>   and compare
> - Returns handling (if `returns` data/logic exists) — does a returned order/item
>   correctly adjust downstream aggregates?
> - Duplicate-ingestion behavior on re-run
>
> **Deliverable:** `tests/results/ecommerce/02_ingestion.md`, standard structure.

---

### Ecommerce Test Prompt 3 — Dashboard Endpoint Testing

> **Prerequisite:** Ecommerce Prompt 2 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test the actual dashboard endpoints (spec described
> dashboard/summary, dashboard/revenue, dashboard/sku-matrix — confirm real route
> paths). For each: confirm shared envelope shape, recompute every returned figure by
> hand against ingested data, confirm anomaly/return exclusions apply where the spec
> requires, and confirm `disabled_features` fires correctly below the SKU-history
> minimum-data threshold (e.g. "<8 weeks SKU history" — cite the actual threshold).
>
> **Deliverable:** `tests/results/ecommerce/03_dashboard.md`, standard structure.

---

### Ecommerce Test Prompt 4 — Diagnostics Endpoint Testing

> **Prerequisite:** Ecommerce Prompt 3 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test whichever of profit-leaks, dead-stock, and
> return-forensics are actually implemented (confirm route paths; flag any not
> implemented as a build-completeness finding, not a failure of this test). For each:
> cite the calculation logic, independently recompute against ingested data, and check
> graceful degradation on thin data.
>
> **Deliverable:** `tests/results/ecommerce/04_diagnostics.md`, standard structure.

---

### Ecommerce Test Prompt 5 — Predictive Model Testing

> **Prerequisite:** Ecommerce Prompt 4 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test the implemented predictive endpoints (Holt-
> Winters inventory forecast, RFM segmentation, churn-risk model, ad-kill-switch logic
> — confirm actual implementations/route paths and the real RFM cluster count used,
> don't assume k=6 without checking code). Run the larger-volume datasets
> (`ecommerce_orders_10k_updated.csv`, Olist set if ingestible) through the forecast
> and RFM/churn models specifically, since these need volume/time-series depth to
> produce meaningful output. Sanity-check forecast direction against the actual
> historical trend, and confirm RFM segment assignments are internally consistent
> (e.g. no customer assigned to two segments). Confirm graceful degradation below
> minimum-data thresholds.
>
> **Deliverable:** `tests/results/ecommerce/05_predictive.md`, standard structure.

---

### Ecommerce Test Prompt 6 — AI Playbook Testing

> **Prerequisite:** Ecommerce Prompt 5 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test the Ecommerce AI playbook endpoint(s). Confirm
> output validates against the shared `AIRecommendation` schema, confirm narrative
> content is grounded in the analyzer's own computed figures (spot-check numbers
> against dashboard/diagnostics/predictive outputs), and confirm reasonable behavior
> on sparse data.
>
> **Deliverable:** `tests/results/ecommerce/06_ai_layer.md`, standard structure.

---

### Ecommerce Test Prompt 7 — Ecommerce Analyzer Final Validation Report

> **Prerequisite:** Ecommerce Prompts 1–6 completed (any status).
>
> **Core objective:** Consolidate all six prior result files exactly as Bank Prompt 7
> did: per-script summary, running Critical/Warning issue table with status, overall
> verdict (READY FOR INTEGRATION / READY WITH OPEN ISSUES / NOT READY), and explicit
> items to carry into Integration testing.
>
> **Deliverable:** `tests/results/ecommerce/07_final_validation.md`, standard
> structure. Append final summary line to `tests/QA_LOG.md`.

## SALES ANALYZER

*(Context only: the Sales vertical was primarily built across Shoaib's task range
1.15–1.19 / 2.7–2.11 / 3.7–3.10 / 4.3–4.5 / 5.2. These task references are navigation
hints for locating implementation artifacts — they are not the verification source of
truth. Verification must still be grounded in the actual repo code, migrations, routes,
and `docs/SYSTEM_DOCUMENTATION.md`, per the Evidence discipline rule.)*

### Sales Test Prompt 1 — Dataset Inspection + Schema Mapping

> **Scope boundary:** Read-only inspection only. No ingestion, no DB writes, no
> dataset edits, no code changes.
>
> **Datasets to inspect:**
> - `scanwick_test_sales_pipeline.csv` **(primary test input)** — ingest with
>   `source=generic_csv` (see Pre-QA alignment note below), not any of the four CRM
>   sources
> - `sales_pipeline.csv` (in either `archive (24)/` or `archive (25)/` — **confirmed
>   byte-identical duplicates, use either one**; `sales_pipeline_dataset.csv` does
>   not exist under that name anywhere in the project) — same `source=generic_csv`,
>   volume/secondary test
> - `sales_teams.csv` (plural — **not** `sales_team.csv`, which doesn't exist; also a
>   confirmed byte-identical duplicate across `archive (24)/` and `archive (25)/`) —
>   rep-roster reference file, not a deal-data primary input; use it only to
>   cross-check rep assignment after ingestion
> - `sales_data_sample.csv` — confirmed the classic Kaggle "Sales Data Sample"
>   dataset (order-transaction shaped: `ORDERNUMBER`, `ORDERDATE`, `PRODUCTCODE`,
>   `SALES`...). **Confirmed mismatched** — no `deal_id`/`stage`/`rep`/pipeline
>   concept at all. Exclude from Sales testing
> - ~~`Sales-Pipeline-Dataset`~~ — **this is not a directory.** It's
>   `Sales-Pipeline-Dataset.xlsx` (confirmed byte-identical in both `archive (17)/`
>   and `sales dataset/`). The codebase has zero `read_excel`/`openpyxl` support
>   anywhere (confirmed via repo-wide grep) — unusable without manual conversion to
>   CSV first. Excluded; use `scanwick_test_sales_pipeline.csv`/`sales_pipeline.csv`
>   instead, both already CSV and both now ingestible
>
> **Pre-QA alignment note (2026-07-07):** every dataset above previously failed to
> ingest at all — verified empirically: 0 fields resolved under all four supported
> CRM sources (salesforce/hubspot/pipedrive/zoho) for every available Sales file
> (0/12, 0/11, 0/13, 0/9 respectively), meaning 100% of rows would have been
> rejected (`deal_value`/`open_date` both required). A new `DealDataSource.generic_csv`
> source was added (`app/services/sales_ingestion.py::GENERIC_COLUMN_MAP`) that maps
> `scanwick_test_sales_pipeline.csv`/`sales_pipeline.csv`'s own canonical-named
> columns directly, including their explicit `status` (open/won/lost) and
> `actual_close_date` columns — the cleanest of the five sources on that front. Use
> `source=generic_csv` for both files in Prompt 2. Verified:
> `scanwick_test_sales_pipeline.csv` now ingests 130/130 rows with 0 rejected.
>
> **Objective:** Map viable datasets onto the canonical `deals`/`stage_transition_logs`
> schema. Locate and cite the actual implementation (models, migrations,
> `docs/SYSTEM_DOCUMENTATION.md`) rather than assuming field names from the original
> spec. Expected canonical fields to look for include deal identifiers, stage/pipeline
> fields, stage-transition timestamps, deal value/currency, rep/owner identifiers,
> close date, and won/lost outcome fields — plus any others actually defined in the
> repo.
>
> **Required checks (per usable dataset):** source→canonical mapping, cross-file
> consistency, and data-quality issues (missing stage values, inconsistent stage
> naming across files, malformed dates, missing rep identifiers, orphaned stage-
> transition rows with no parent deal).
>
> **Deliverable:** `tests/results/sales/01_dataset_inspection.md`, standard
> result-file structure. Section 8 must explicitly state which datasets are usable
> for Sales Prompt 2 and which were excluded (with reasons — e.g. schema mismatch,
> confirmed duplicate, unreadable directory).
>
> **QA log:** append to `tests/QA_LOG.md`.

---

### Sales Test Prompt 2 — Ingestion Testing

> **Prerequisite:** Sales Prompt 1 PASS or PASS WITH ISSUES.
>
> **Scope boundary:** Runs real ingestion, writes to dev/test DB only. No code changes.
>
> **Core objective:** Ingest `scanwick_test_sales_pipeline.csv` first (source=
> `generic_csv`), then `sales_pipeline.csv` (source=`generic_csv`, volume run — use
> either the `archive (24)/` or `archive (25)/` copy, they're identical). Verify:
> - Row counts in vs. inserted into `deals`/`stage_transition_logs`, with reasons for
>   skipped rows
> - Stage-transition log correctness: does each stage change produce a correctly
>   timestamped transition row, and is stage ordering internally consistent (no
>   transitions logged out of chronological order)?
> - Rep/owner assignment correctness against `sales_teams.csv` (plural)
> - Won/lost/open outcome classification correctness — `generic_csv` reads this
>   directly from the file's own `status` column rather than inferring it from stage
>   text, so this should be a straightforward direct comparison, not a heuristic check
> - Duplicate-ingestion behavior on re-run
>
> **Deliverable:** `tests/results/sales/02_ingestion.md`, standard structure.

---

### Sales Test Prompt 3 — Dashboard Endpoint Testing

> **Prerequisite:** Sales Prompt 2 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test the actual dashboard endpoints (spec described
> pipeline-overview and rep-leaderboard — confirm real route paths). For each: confirm
> shared envelope shape, recompute every returned figure (pipeline value by stage, win
> rate, rep rankings) by hand against ingested data, and confirm `disabled_features`
> fires correctly below the minimum-data thresholds (e.g. "<30 closed deals" for
> pipeline metrics, "<20 closed-won deals" for win-rate-dependent metrics — cite the
> actual thresholds in code).
>
> **Deliverable:** `tests/results/sales/03_dashboard.md`, standard structure.

---

### Sales Test Prompt 4 — Diagnostics Endpoint Testing

> **Prerequisite:** Sales Prompt 3 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test whichever of stage-velocity, stagnation-alerts,
> and data-quality-cost are actually implemented (confirm route paths; flag any not
> implemented as a build-completeness finding). For each: cite the calculation logic,
> independently recompute against ingested data (e.g. manually compute average
> time-in-stage from `stage_transition_logs` and compare to the stage-velocity
> endpoint's output), and check graceful degradation on thin data.
>
> **Deliverable:** `tests/results/sales/04_diagnostics.md`, standard structure.

---

### Sales Test Prompt 5 — Predictive Model Testing

> **Prerequisite:** Sales Prompt 4 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test the implemented predictive endpoints
> (win-probability, pipeline forecast, rep-trajectory, slippage prediction — confirm
> actual implementations/route paths). Sanity-check win-probability scores fall in
> valid range and correlate directionally with deal stage/age; sanity-check forecast
> figures against the actual closed-won trend; confirm graceful degradation below the
> minimum closed-deal thresholds identified in Prompt 3.
>
> **Deliverable:** `tests/results/sales/05_predictive.md`, standard structure.

---

### Sales Test Prompt 6 — AI / Playbook / Report Testing

> **Prerequisite:** Sales Prompt 5 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and test the Sales AI outputs (playbook, "Win DNA"
> analysis, quarter post-mortem — confirm which are implemented and how the
> post-mortem's scheduled/Celery-beat trigger actually works, since the spec described
> it as an automated job rather than a plain endpoint). Confirm output validates
> against the shared `AIRecommendation` schema, confirm narrative content is grounded
> in the analyzer's own computed figures, and confirm reasonable behavior on sparse
> pipelines.
>
> **Deliverable:** `tests/results/sales/06_ai_layer.md`, standard structure.

---

### Sales Test Prompt 7 — Sales Analyzer Final Validation Report

> **Prerequisite:** Sales Prompts 1–6 completed (any status).
>
> **Core objective:** Consolidate all six prior result files: per-script summary,
> running Critical/Warning issue table with status, overall verdict (READY FOR
> INTEGRATION / READY WITH OPEN ISSUES / NOT READY), and explicit items to carry into
> Integration testing.
>
> **Deliverable:** `tests/results/sales/07_final_validation.md`, standard structure.
> Append final summary line to `tests/QA_LOG.md`.

## SHARED / INTEGRATION TESTING

*(Context only: shared infrastructure was primarily built across tasks 0.1–0.6 /
1.1–1.6 / 1.3–1.4 / 5.4–5.6 in the build sequence, jointly maintained by both
developers. These task references are navigation hints only, not verification source
of truth. Verification must still be grounded in the actual repo code.)*

**Prerequisite for this whole section:** Bank Prompt 7, Ecommerce Prompt 7, and Sales
Prompt 7 should each be at least READY WITH OPEN ISSUES before starting Integration
testing — integration tests assume each analyzer's own data is already in the DB from
the per-analyzer ingestion runs above.

### Integration Test Prompt 1 — Reconciliation Report Testing

> **Scope boundary:** Read-only endpoint testing against data already ingested across
> all three analyzers in the prior stages. No new ingestion.
>
> **Core objective:** Locate and cite the actual `reconciliation_reports` table schema
> and the `GET /api/v1/reconciliation/{analysis_run_id}` (or actual real route — confirm
> path) implementation. For each analyzer's most recent ingestion run:
> - Confirm a reconciliation report row was actually created
> - Confirm `records_analyzed` + `records_excluded` reconciles against the raw row
>   count of the source file used in that ingestion run
> - Confirm the excluded-record reasons line up with what Bank/Ecommerce/Sales Prompt 2
>   (ingestion) actually observed being skipped/excluded (anomalies, own-transfers,
>   duplicates, malformed rows)
> - Confirm the reconciliation endpoint is genuinely readable across roles per its
>   "universal read access" design (test with more than one role if RBAC is testable
>   at this point, otherwise flag for Integration Prompt 3)
>
> **Deliverable:** `tests/results/integration/01_reconciliation.md`, standard
> result-file structure, with a per-analyzer reconciliation-accuracy table in
> Section 4.
>
> **QA log:** append to `tests/QA_LOG.md`.

---

### Integration Test Prompt 2 — Contextual Marker Testing Across Analyzers

> **Prerequisite:** Integration Prompt 1 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and cite the `is_anomalous`/contextual-marker
> implementation and the retroactive re-flagging job. Verify:
> - Anomaly flags set during Bank/Ecommerce/Sales Prompt 2 ingestion are still
>   consistent now (no drift between what was flagged then and what's stored now)
> - The retroactive re-flagging job actually runs and correctly updates flags when
>   triggered (test by introducing a condition that should flip a flag, if feasible
>   without violating "no code changes" — otherwise document as untestable in this
>   pass and note what would be needed)
> - Flag consistency logic is applied uniformly across all three analyzers (same
>   underlying marker mechanism, not three divergent implementations that happen to
>   look similar)
>
> **Deliverable:** `tests/results/integration/02_contextual_markers.md`, standard
> structure.

---

### Integration Test Prompt 3 — RBAC Testing

> **Prerequisite:** Integration Prompt 2 PASS or PASS WITH ISSUES.
>
> **Scope boundary:** Requires test accounts/tokens for each of the four roles per
> analyzer (confirm what these roles actually are in the repo — do not assume role
> names from the spec without checking `models/roles.py` or equivalent).
>
> **Core objective:** For each analyzer, test all four roles against representative
> endpoints from dashboard/diagnostics/predictive/AI layers already validated in
> earlier prompts:
> - Confirm the Bank "Loan Officer" role (or whatever the actual restricted role is
>   named in code) is correctly blocked from transaction-level detail while still
>   allowed dashboard-level access — cite the actual permission check
> - Run adversarial tests for the Sales "Sales Rep" role (or actual name): attempt to
>   access another rep's deals/pipeline data and confirm it's correctly blocked, not
>   just hidden in the UI layer
> - Spot-check the remaining roles across all three analyzers for correct
>   allow/deny behavior on at least one endpoint per layer
> - Confirm denied requests return the correct error shape via the shared response
>   envelope, not a raw 500 or stack trace
>
> **Deliverable:** `tests/results/integration/03_rbac.md`, standard structure, with a
> Role × Endpoint × Expected × Observed table in Section 4.

---

### Integration Test Prompt 4 — Billing / Entitlement Testing

> **Prerequisite:** Integration Prompt 3 PASS or PASS WITH ISSUES.
>
> **Core objective:** Locate and cite the actual tier-gating implementation (basic vs.
> premium). For each analyzer, using test accounts on each tier:
> - Confirm premium-only features (predictive/AI layers, per the spec — confirm which
>   features are actually gated in code) are correctly blocked or degraded for basic
>   tier accounts, and what the actual response looks like (disabled_features flag vs.
>   hard error — confirm which the implementation uses)
> - Confirm premium accounts get full access to the same endpoints
> - Confirm a tier-downgrade or expired-subscription scenario is handled correctly if
>   testable
>
> **Deliverable:** `tests/results/integration/04_billing.md`, standard structure.

---

### Integration Test Prompt 5 — Response Envelope / Shared Schema / AI Recommendation Validation

> **Prerequisite:** Integration Prompt 4 PASS or PASS WITH ISSUES.
>
> **Core objective:** This is a cross-cutting consistency check across everything
> tested in Bank/Ecommerce/Sales Prompts 3–6 plus Integration 1–4:
> - Confirm every successful response observed across all prior test runs conformed to
>   the exact same envelope shape (no analyzer-specific drift in field names/nesting)
> - Confirm every error response conformed to the shared error shape
> - Confirm every AI output observed across Bank/Ecommerce/Sales Prompt 6 actually
>   validated against the single shared `AIRecommendation` schema (not three
>   similar-but-different schemas) — cite the schema file and note any per-analyzer
>   deviations found
> - Confirm `analysis_run_id` is consistently present and correctly correlates a given
>   response back to its corresponding reconciliation report from Integration Prompt 1
>
> **Deliverable:** `tests/results/integration/05_response_envelope.md`, standard
> structure. This prompt should draw on evidence already gathered in prior result
> files rather than re-running every endpoint from scratch — cite which earlier
> result file each conformance check is based on.

---

### Integration Test Prompt 6 — Final System Integration Validation Report

> **Prerequisite:** Integration Prompts 1–5 completed (any status).
>
> **Scope boundary:** No new testing — consolidation/synthesis only.
>
> **Core objective:** Produce the final QA report for the entire Scanwick testing
> phase:
> - Read all 27 result files (7 Bank + 7 Ecommerce + 7 Sales + 6 Integration) and the
>   full `tests/QA_LOG.md`
> - One consolidated table of every Critical and Warning issue found across the whole
>   project, with current status and which analyzer/layer it affects
> - Overall system verdict: READY FOR PRODUCTION / READY WITH OPEN ISSUES (list them
>   by priority) / NOT READY
> - A short "what would need synthetic test data" section, pulling together anything
>   flagged across all 27 scripts as untestable from the current real datasets alone
>
> **Deliverable:** `tests/results/integration/06_final_system_validation.md`, standard
> result-file structure (Section 4 = the full consolidated issue table, Section 7 =
> the overall system verdict).
>
> **QA log:** append the final system-wide summary line to `tests/QA_LOG.md`.

---

## Execution order reminder

1. Bank Test Prompts 1 → 7 (in order, reviewing each result before the next)
2. Ecommerce Test Prompts 1 → 7
3. Sales Test Prompts 1 → 7
4. Integration Test Prompts 1 → 6

Run one at a time. Review each result file before moving to the next, and carry any
flagged follow-up checks forward as additions to the next script's fixed core scope —
never as a replacement of it.
