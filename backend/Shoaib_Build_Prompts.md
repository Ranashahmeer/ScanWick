# Scanwick — Build Prompts for Shoaib Ahmed

## Your scope
The shared AI/schema pieces that have zero dependency on infra → the **Ecommerce
analyzer**, end to end → the **Sales analyzer**, end to end (dashboards, diagnostics,
predictive models, AI playbooks, automation, for both) → RBAC for those two verticals.

You do **not** need Shakir's file to do your work — everything you need is below. The
only times you need to coordinate with him directly are marked **"Sync with Shakir"**.

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
- **"RBAC seam"** = a comment marking exactly where a permission check goes later, so
  Phase 5 knows where to plug in without re-reading the whole endpoint.
- **CSV ingestion** = wherever a task says "CSV," an uploaded `.xlsx` file is also
  accepted — both formats are parsed into the same canonical rows via a shared
  reader helper (`app/services/upload_staging.py`). Infrastructure detail, not a
  separate task.

---

## Files that are yours — Shakir will never touch these
`services/ai_client.py`, `schemas/envelope.py`, `schemas/recommendation.py`,
`models/orders.py`, `models/order_items.py`, `models/returns.py`, `routes/ecommerce.py`,
`models/deals.py`, `models/stage_transition_logs.py`, `routes/sales.py`,
`routes/reconciliation.py`.

## Files you'll touch that Shakir also touches (be careful here)
- `docs/SYSTEM_DOCUMENTATION.md` — append-only. Pull latest, add your section, commit,
  push immediately. Don't sit on edits to this file.
- `main.py` (router registration) — only add your own
  `include_router(ecommerce_router, ...)` / `include_router(sales_router, ...)` lines;
  don't touch lines Shakir added for bank.
- `middleware/rbac.py` — **only touch this in Phase 5.** Push your 5.1/5.2 changes and
  tell Shakir as soon as they're merged — his cross-cutting steps (5.4–5.6) wait on that.

## Git habit
One branch per task ID (e.g. `feature/2.3-profit-leaks`), one small PR per task, pull
latest before starting your next task.

---

## PHASE 0 — Your independent starting tasks (start immediately, no need to wait on Shakir)

**0.7**
> Add Gemini API client setup (`services/ai_client.py`) with a single function
> `generate_text(prompt) -> str`, env-configured API key, and a retry/timeout wrapper.
> No business logic yet — just a working, tested client.
>
> Test: mock the Gemini call and test the wrapper's retry/timeout behavior; add a manual
> smoke-test script (not part of CI) for a real call.
>
> Document: append an "AI Layer (Gemini)" section.

**0.8 — Phase 0 checkpoint (Sync with Shakir)** pending
> Confirm with Shakir that his infra work (migrations, Celery, S3, encryption, test
> scaffolding) is green, and that your Gemini client is green too. Both of you append
> your own results to the "Phase 0 Checkpoint" section he starts in the docs.

---

## PHASE 1, Part A — Shared Schema (your half)

**1.3**
> Implement the shared API response envelope (`success_response`/`error_response`
> helpers) matching: `{success, data, meta:{missing_fields, disabled_features,
> analysis_run_id}}` on success and `{success:false, error:{code, message, details}}` on
> failure. Don't apply it to existing endpoints yet — just build and unit-test it in
> isolation.
>
> Test: unit tests asserting exact JSON shape for both success and error cases.
>
> Document: append a "Standard Response Envelope" section with examples.

**1.4**
> Implement the shared `AIRecommendation` Pydantic model (id, trigger_condition,
> entity_type, entity_id, entity_name, revenue_at_stake, currency, recommended_action,
> reasoning, confidence_score, urgency, created_at) with validation that drops any
> recommendation missing a required field.
>
> Test: unit tests for valid and invalid recommendation payloads.
>
> Document: append an "AI Recommendation Schema" section.

**1.5 (Sync with Shakir first)**
> Confirm Shakir has pushed step 1.2 (the `reconciliation_reports` table) before
> starting this — you depend on that table existing. Once it's there:
>
> Build `GET /api/v1/reconciliation/{analysis_run_id}` returning a reconciliation_reports
> row via the response envelope from 1.3. No RBAC restriction yet — note in code that
> Phase 5 will add it.
>
> Test: integration test for found/not-found cases.
>
> Document: append endpoint docs (path, params, response shape) to the docs file.

**1.6 — Phase 1, Part A checkpoint (Sync with Shakir)** pending
> Run the full test suite. Confirm with Shakir that all shared tables/schemas are in
> place on both sides. Once this is green, you branch off into Ecommerce and won't need
> to touch shared files again until Phase 4.

---

## PHASE 1, Part B — Ecommerce Canonical Tables (your vertical, solo from here)

**1.7**
> Create the `orders` table per spec (external_order_id, gross_revenue,
> original_currency, base_currency_amount, exchange_rate_at_order, refund_amount,
> discount_amount, shipping_cost, processing_fees, allocated_ad_spend, cogs, net_margin,
> channel, customer_id, status, data_source enum [shopify_csv, woocommerce_csv,
> shopify_api], is_anomalous). Migration + model only — this is separate from whatever
> in-memory dataframe the existing `/api/analyze` uses today.
>
> Test: migration + model CRUD test.
>
> Document: append schema docs, and a short note clarifying the relationship between this
> new canonical table and the existing generic CSV analyzer (they coexist for now; we'll
> wire the e-commerce path to write here in 1.10).

**1.8**
> Create `order_items` (sku, quantity, unit_price, unit_cogs, unit_shipping_cost,
> unit_return_cost, unit_net_margin) and `returns` (return_reason_code, carrier_id,
> warehouse_location, return_cost, refund_amount, return_date) tables per spec. Migration
> + models only.
>
> Test: migration + CRUD tests for both.
>
> Document: schema docs for both tables.

**1.9**
> Create `merchant_settings` (base_currency, default_return_cost, ad_kill_mode,
> ad_kill_threshold_days) table per spec. Migration + model only.
>
> Test: migration + CRUD test.
>
> Document: schema docs.

**1.10**
> Build a Celery task `ingest_ecommerce_csv(upload_id, merchant_id)` that takes a Shopify
> or WooCommerce CSV, reuses the existing column-detection logic from `utils/analyzer.py`
> where it overlaps, and writes canonical rows into `orders`/`order_items` (not just an
> in-memory dataframe). Keep both Shopify and WooCommerce column-name mappings feeding the
> same canonical insert function — one analysis path, not two.
>
> Test: integration test with a sample Shopify CSV and a sample WooCommerce CSV, asserting
> identical canonical row shapes land in the DB.
>
> Document: append an "E-commerce Ingestion" section explaining the mapping and reuse of
> existing column-detection code.

**1.11**
> Implement the e-commerce data-quality report (rows_parsed, rows_rejected, date_range,
> days_of_history) plus the COGS≥20%-missing rule (disable unit_margin +
> profit_leak_detector with the exact warning shape from the spec). Build
> `GET /api/upload/{upload_id}/quality-report` for the ecommerce path.
>
> Test: test with a fixture CSV that has >20% missing COGS and confirm the warning/disable
> fires; test with <20% missing and confirm it doesn't.
>
> Document: append endpoint + rule docs.

**1.12**
> Implement currency conversion at order_date (not today's rate) and contextual-marker
> flagging (is_anomalous) for orders, including the re-flag-on-new-marker job.
>
> Test: test that a known historical rate is used (not current), and that adding a marker
> retroactively flags existing orders inside its range.
>
> Document: append docs explaining the rate-lookup and re-flag mechanism.

**1.13**
> Implement net_margin calculation per the exact formula and the unit_return_cost
> fallback (SKU override → merchant default → 0 + warning).
>
> Test: table-driven tests covering all three fallback branches.
>
> Document: append the formula and fallback logic to the docs.

**1.14 — Phase 1, Part B checkpoint**
> Run full suite, append checkpoint section confirming the Ecommerce ingestion pipeline
> is solid before moving on to Sales. (This one's about your own vertical — no need to
> wait on Shakir.)

---

## PHASE 1, Part C — Sales Canonical Tables

**1.15**
> Create `deals` and `stage_transition_logs` tables exactly per spec. Migration + models
> only.
>
> Test: migration applies cleanly up and down; CRUD test for both tables.
>
> Document: schema docs for both tables.

**1.16**
> Build Celery parsers for salesforce_csv, hubspot_csv, pipedrive_csv, zoho_csv that map
> into canonical `deals`, populating `stage_transition_logs` during ingestion (from
> explicit history fields or inferred from the export).
>
> Test: one fixture CSV per CRM source, asserting canonical rows and at least one stage
> transition row land correctly for each.
>
> Document: append a "Sales Ingestion" section per source.

**1.17**
> Implement multi-currency handling for deals (original + base_currency_amount at
> open_date rate) and contextual-marker flagging for deals.
>
> Test: a test asserting the historical rate at open_date is used; a test asserting a
> deal inside a marker range gets is_anomalous=TRUE.
>
> Document: append docs explaining the rate-lookup and flagging logic for deals.

**1.18**
> Build the sales data-quality endpoint
> (`GET /api/v1/sales/diagnostic/data-quality-cost`) with missing_stage_history_count,
> missing_loss_reason_count/pct, missing_close_date_count, reps_with_data_gaps, and the
> summary_message, matching the spec's exact shape.
>
> Test: fixture-driven test reproducing the example numbers in the spec.
>
> Document: endpoint docs.

**1.19 — Phase 1, Part C checkpoint**
> Run full suite, append checkpoint section confirming the Sales ingestion pipeline is
> solid. (Your own vertical — no need to wait on Shakir.)

---

## PHASE 1 final sync

**1.27 — Phase 1 final checkpoint (Sync with Shakir)**
> Run the full suite. Append to the "Phase 1 Complete" section confirming your
> Ecommerce and Sales ingestion paths are done and using the shared
> reconciliation_reports + contextual_markers infrastructure consistently. Confirm with
> Shakir that his Bank ingestion path is also green before both of you move to Phase 2.

---

## PHASE 2 — Ecommerce & Sales Dashboards and Diagnostics

**2.1**
> Build `GET /api/v1/ecommerce/dashboard/summary` per the exact spec shape (gross_revenue,
> net_revenue, total_orders, avg_order_value, profit_leak_count, dead_stock_count,
> data_freshness), excluding is_anomalous orders from every aggregate.
>
> Test: integration test asserting the response shape and that an is_anomalous order is
> excluded from the totals.
>
> Document: append endpoint docs (path, response shape, exclusion rule) to
> `docs/SYSTEM_DOCUMENTATION.md`.

**2.2**
> Build `GET /api/v1/ecommerce/dashboard/revenue` per spec, including gap_breakdown
> (returns/discounts/shipping/processing/ad_spend) and monthly_trend.
>
> Test: integration test asserting gap_breakdown values sum correctly against
> gross − net.
>
> Document: append endpoint docs.

**2.3**
> Build `GET /api/v1/ecommerce/diagnostic/profit-leaks`: SKUs in the top-30 by revenue
> with negative net_margin, sorted worst first, with leak_breakdown and
> primary_leak_driver. Respect the unit_margin/profit_leak_detector disabled-feature rule
> from step 1.11 — return it as disabled in `meta` rather than computing wrong numbers
> when COGS coverage is below threshold.
>
> Test: one test with healthy COGS coverage asserting real leak data; one test with
> COGS-coverage below 20% asserting the endpoint returns disabled_features instead of
> data.
>
> Document: append endpoint docs, explicitly noting the disabled-feature behavior.

**2.4**
> Build `GET /api/v1/ecommerce/diagnostic/dead-stock` per spec shape
> (days_without_sale, estimated_carrying_cost, recommended_action).
>
> Test: integration test with a fixture SKU that has zero sales for >60 days.
>
> Document: append endpoint docs.

**2.5**
> Build `GET /api/v1/ecommerce/diagnostic/return-forensics`: group by carrier_id +
> return_reason_code, compute occurrence_count, total_return_cost,
> as_pct_of_carrier_returns, and the HIGH_RISK flag threshold from the spec.
>
> Test: fixture test reproducing a known HIGH_RISK case and a known low-risk case.
>
> Document: append endpoint docs including the HIGH_RISK threshold value used.

**2.6**
> Build `GET /api/v1/ecommerce/dashboard/sku-matrix` (stars/cash_cows/question_marks/dogs)
> per spec shape.
>
> Test: integration test confirming SKUs land in the correct quadrant given known
> revenue/margin fixtures.
>
> Document: append endpoint docs explaining the quadrant logic used.

**2.7**
> Build `GET /api/v1/sales/dashboard/pipeline-overview` per spec shape (by_stage array,
> totals), excluding is_anomalous deals.
>
> Test: integration test asserting totals and that an is_anomalous deal is excluded.
>
> Document: append endpoint docs.

**2.8**
> Build `GET /api/v1/sales/dashboard/rep-leaderboard` per spec shape. Don't add RBAC
> filtering yet — leave an explicit `# RBAC SEAM: filter to rep_id == current_user when
> role == sales_rep` comment exactly where Phase 5 will plug in the check.
>
> Test: integration test confirming the unfiltered response shape is correct today.
>
> Document: append endpoint docs and note the RBAC seam location (file + line context).

**2.9**
> Build `GET /api/v1/sales/diagnostic/stage-velocity` (avg_days per stage,
> stall_threshold_days, stalled_deals list). Disable this endpoint (return
> disabled_features) when `stage_transition_logs` is empty for the merchant, per the
> validation rule in the spec.
>
> Test: one test with populated stage_transition_logs asserting real velocity data; one
> test with an empty table asserting the disabled response.
>
> Document: append endpoint docs noting the disable condition.

**2.10**
> Build `GET /api/v1/sales/diagnostic/stagnation-alerts` per spec shape
> (days_since_activity vs threshold_days).
>
> Test: fixture test with a deal past the threshold and one within it.
>
> Document: append endpoint docs.

**2.11**
> Build `POST /api/v1/sales/deals/{deal_id}/capture-loss-reason`. Trigger an in-app +
> email notification to the rep within 60 seconds of a deal's status changing to "lost",
> with a one-click loss-reason prompt that calls this endpoint. Populate
> `loss_reason_captured_at` on success.
>
> Test: test that changing a deal to "lost" fires the notification within the time
> budget (mock email/in-app sender); test that calling the endpoint sets
> loss_reason_captured_at correctly.
>
> Document: append endpoint docs and the notification trigger flow.

**2.18 — Phase 2 checkpoint (Sync with Shakir)**
> Run the full suite, append a checkpoint section confirming every Ecommerce/Sales
> endpoint's is_anomalous exclusion and disabled-feature responses are correct. Confirm
> with Shakir that his Bank Phase 2 work is also green before moving to Phase 3.

---

## PHASE 3 — Ecommerce & Sales Predictive Layer

**3.1**
> Implement Holt-Winters forecasting per SKU, enforcing the minimum-8-weeks-of-history
> rule (excluded SKUs named in the response) and excluding is_anomalous orders from
> training.
>
> Test: a test with a SKU at 7 weeks of history asserting it's excluded and named; a
> test with a SKU at 8+ weeks asserting a forecast is produced.
>
> Document: append a "Holt-Winters Forecasting" section explaining the model and
> exclusion rules.

**3.2**
> Build `GET /api/v1/ecommerce/predictive/inventory-forecast` using the model from 3.1,
> matching the exact response shape (predicted_stockout_date, revenue_at_risk,
> confidence_score, confidence_interval_80, weeks_of_history_used, recommendation,
> skus_excluded_insufficient_history, minimum_weeks_required).
>
> Test: integration test asserting the full response shape against a fixture dataset.
>
> Document: append endpoint docs.

**3.3**
> Implement RFM clustering with k-means, k=6, using the exact 7 segment labels from the
> spec (Champions, Loyal Customers, At Risk, Hibernating, Lost, New Customers,
> Promising), excluding is_anomalous orders from training.
>
> Test: a test asserting exactly 6 clusters are produced and labels match the spec's set.
>
> Document: append an "RFM Segmentation" section.

**3.4**
> Build `GET /api/v1/ecommerce/predictive/rfm-segments`, including
> segment_movement_since_last_run by comparing against the prior run's stored
> assignments, specifically flagging Loyal Customers → At Risk moves as the spec calls
> out.
>
> Test: a test running the model twice with a customer moved from Loyal to At Risk
> between runs, asserting the movement is flagged.
>
> Document: append endpoint docs.

**3.5**
> Implement Kaplan-Meier survival analysis for churn; build
> `GET /api/v1/ecommerce/predictive/churn-risk`, returning customers above 70% 60-day
> churn probability per spec shape.
>
> Test: fixture test with a known high-churn-risk customer and a known low-risk one.
>
> Document: append a "Churn Risk (Kaplan-Meier)" section.

**3.6**
> Build the ad-kill switch: `POST /api/v1/ecommerce/predictive/ad-kill-switch/configure`.
> Default mode=manual; build the audit log table and write an entry (timestamp,
> threshold, campaign) on every pause event, whether manually or automatically
> triggered.
>
> Test: test that manual mode is the default for a new merchant; test that a pause event
> writes a complete audit log row.
>
> Document: append an "Ad-Kill Switch" section with the audit log schema.

**3.7**
> Implement the win-probability logistic regression (features: stage, deal age, deal
> value bucket, rep historical win rate, channel win rate). Reuse the existing
> from-scratch NumPy/gradient-descent approach used for the high-value-order predictor,
> adapted to this feature set. Enforce the minimum-30-closed-deals rule
> (model_available: false below it) and exclude is_anomalous deals from training.
>
> Test: a test with 29 closed deals asserting model_available: false; a test with 30+
> asserting a trained model and scored deals.
>
> Document: append a "Win Probability Model" section.

**3.8**
> Build `GET /api/v1/sales/predictive/forecast`: confidence-adjusted forecast
> (deal_value × win_probability — never static stage weights), with the mandatory
> confidence_rating, confidence_explanation, and confidence_factors that can never be
> hidden from the response.
>
> Test: an assertion that confidence_rating/explanation/factors are present on every
> response, even when the forecast itself is simple/high-confidence.
>
> Document: append endpoint docs.

**3.9**
> Implement rep trajectory comparison (30-day attainment vs. prior 60-day window),
> flagging intervention_flag=true only when declining AND below 60% attainment for two
> consecutive 30-day windows. Build `GET /api/v1/sales/predictive/rep-trajectory`.
>
> Test: table-driven tests covering improving/declining/below-threshold combinations,
> confirming intervention_flag only fires on the exact combination specified.
>
> Document: append endpoint docs with the intervention rule spelled out.

**3.10**
> Implement slippage prediction tied to `stage_transition_logs`, folding its
> disabled-state into the same stage_transition_logs-empty rule used for stage velocity
> and win probability.
>
> Test: test that slippage prediction is disabled under the same condition as 2.9's
> stage-velocity disable.
>
> Document: append a note tying slippage prediction's disable rule to the shared
> stage_transition_logs check.

**3.14 — Phase 3 checkpoint (Sync with Shakir)**
> Run the full suite. Append a checkpoint confirming your Holt-Winters, RFM, churn,
> win-probability, and rep-trajectory models all exclude is_anomalous records and that
> every minimum-data threshold triggers the correct disabled-feature response instead of
> an error. Confirm with Shakir that his fraud-risk and loan-readiness models are also
> green.

---

## PHASE 4 — AI Layer & Automation (your part)

**4.1 — Build together with Shakir (pair up for this one)**
> Build the shared `generate_recommendations(analyzer_type, context_data)` service on
> top of the Gemini client you built in step 0.7, validating every returned
> recommendation against the AIRecommendation schema you built in step 1.4 and dropping
> any that's missing a required field.
>
> Test: mock Gemini returning one valid and one invalid (missing-field) recommendation,
> asserting only the valid one survives.
>
> Document: append a "Recommendation Generation Service" section.
>
> Note: this is the one task in Phase 4 you should sit down and do together with Shakir
> — both of you need it for your own playbook endpoints right after.

**4.2**
> Build `GET /api/v1/ecommerce/ai/playbook` using the service from 4.1, fed by
> profit-leak, dead-stock, and inventory-forecast data.
>
> Test: integration test (with Gemini mocked) asserting the response contains valid
> recommendation objects tied to real fixture data.
>
> Document: append endpoint docs.

**4.3**
> Build `GET /api/v1/sales/ai/playbook` fed by stage-velocity, forecast, and
> rep-trajectory data.
>
> Test: same pattern as 4.2, sales-specific fixtures.
>
> Document: append endpoint docs.

**4.4**
> Implement Win DNA: pattern analysis on closed-won deals only, minimum 20 required;
> below that, return disabled with the exact message "Win DNA requires 20 closed-won
> deals. You currently have N." Build `GET /api/v1/sales/predictive/win-dna`.
>
> Test: a test with 19 closed-won deals asserting the exact disabled message with N=19;
> a test with 20+ asserting a real win_profile is returned.
>
> Document: append a "Win DNA" section with the minimum-data rule.

**4.5**
> Build the Celery beat schedule for quarter/month post-mortems: runs on the 1st of each
> month/quarter, generates the report, stores the PDF in S3, and emails the account
> owner within 24 hours of period close. Build
> `GET /api/v1/sales/reports/quarter-postmortem` to read the stored report only — it must
> not generate on demand.
>
> Test: test the beat schedule trigger logic directly (don't wait for a real month
> boundary); test that calling the GET endpoint before a report exists returns a clear
> "not yet generated" response rather than generating one inline.
>
> Document: append a "Quarter Post-Mortem Automation" section explaining the schedule
> and the storage/email flow.

**4.8 — Phase 4 checkpoint (Sync with Shakir)**
> Run the full suite. Append a checkpoint confirming every recommendation returned by
> your Ecommerce and Sales playbook endpoints validates against the shared
> AIRecommendation schema, and that Win DNA's minimum-data message and the
> post-mortem's 24-hour/no-on-demand rules are enforced. Confirm with Shakir that his
> bank lender-brief timing and financial-health playbook are also green.

---

## PHASE 5 — Ecommerce & Sales RBAC

**5.1 (do this in parallel with Shakir's 5.3 — different files, no conflict)**
> Implement real RBAC rules (replacing any "allow everything" stub) for the four
> e-commerce roles exactly per the spec's access table.
>
> Test: one test per role per endpoint group, including explicit "should be denied" cases.
>
> Document: append an "RBAC — E-commerce" section listing every role/endpoint pairing
> tested.

**5.2 (do this in parallel with Shakir's 5.3 — different files, no conflict)**
> Implement RBAC for the four sales roles, with an explicit adversarial test proving a
> Sales Rep cannot see another rep's deal values or quota attainment under any request
> shape.
>
> Test: one test per role per endpoint group, plus the adversarial test described above
> (try every plausible way a Sales Rep could request another rep's data — direct ID,
> filter param, leaderboard endpoint — and assert each is denied or scoped down).
>
> Document: append an "RBAC — Sales" section listing every role/endpoint pairing tested
> and the adversarial test's result.

**Tell Shakir as soon as both of these are merged.** His cross-cutting steps
(reconciliation access, reconciliation wiring, billing enforcement) touch all three
analyzers' route files and need to wait until your RBAC changes are settled first.

**5.8 — Final checkpoint (Sync with Shakir)**
> Run the entire test suite end to end. Append your part of a final "System Complete"
> section to `docs/SYSTEM_DOCUMENTATION.md` covering every Ecommerce/Sales endpoint, and
> the Definition-of-Done targets relevant to your verticals (dashboard load time, data
> accuracy, forecast variance, RBAC visibility, Win DNA minimum data, etc.). Do this one
> together with Shakir — it's a full-system review covering both of your work.

---

### Reminder
Don't skip the Test or Document part of any prompt. If a "Sync with Shakir" step says
to confirm something with him first, actually do that before proceeding — those are the
points where your work and his come together.
