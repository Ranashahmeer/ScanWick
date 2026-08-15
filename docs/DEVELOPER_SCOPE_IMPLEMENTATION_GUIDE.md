# Scanwick Developer Scope — Implementation Handoff

This document consolidates the changes described in the developer-scope PDF into a developer-friendly Markdown guide. It is intended to replace the PDF as the working source of truth for implementation planning, code changes, testing, and agent-assisted execution.

## 1. Purpose of this document

Use this file as the implementation roadmap for the next phase of Scanwick.

The new direction is:
- Bank statement analysis remains the core product.
- Ecommerce ingestion survives only as the cash-verification input.
- Sales analysis is removed as a product surface.
- The product must move toward lender-facing assessment workflows with provenance, auditability, consent, and verifiable reporting.

## 2. Executive summary

### What survives
- The reconciliation spine and provenance model are central.
- Column mapping and mapping persistence remain core capabilities.
- Mono ingestion remains an important data path.
- The bank-analysis engine remains the product center.
- The ecommerce ingestion layer remains relevant only for cash-gap validation.

### What is corrected
- Bank loan-readiness calculations must be corrected.
- Lender-brief rendering must be rebuilt.
- Role-based access control must be tightened so loan officers cannot access full transaction detail.
- Date parsing must become locale-aware and not silently misparse.
- Deduplication must be enforced in a durable way.
- Revenue aggregation must be currency-correct.
- Quality reporting must emit warnings for every rejected row.

### What is deleted
- The sales analyzer and its related services, models, routes, and tables.
- Ecommerce depth features that depend on Shopify-style data not available in the target market.
- Bank features that do not directly support lender decisioning.
- Payment and reporting features are mothballed until there is a real business need.

### What must be built
- Identity and business-entity model.
- Multi-account consolidation.
- Cash-gap reconciliation.
- Consent, retention, and audit logging.
- Shareable assessment links.
- Outcome tracking.
- Currency-realism reporting.

---

## 3. Priority order for implementation

### Tier 1 — Critical correctness and security
These should be handled first because they affect trust, account safety, and lender decision quality.

1. Fix bank loan-readiness ABM calculations.
2. Fix loan-officer authorization scope.
3. Fix lender-brief rendering and output format.
4. Fix date parsing and locale handling.
5. Fix deduplication for ecommerce uploads.
6. Fix mixed-currency revenue aggregation.
7. Harden RBAC so merchant identity is derived from the authenticated session rather than client-supplied values.

### Tier 2 — Medium/high product correctness
8. Enforce warning emission for rejected rows.
9. Fix weight handling in loan readiness.
10. Fix fraud-risk false positives for contributory savings patterns.
11. Fix quality-reporting behavior.

### Tier 3 — Structural product changes
12. Remove sales analyzer surfaces.
13. Remove or mothball ecommerce depth features and payment/reporting functionality.
14. Add identity, consent, business-entity, assessment, assessment-share, and outcome models.
15. Build new endpoints and data flows for assessments and share links.

---

## 4. Keepers — foundation that should remain

These parts of the system should remain in the product and should be treated as first-class in the PRD.

### 4.1 Reconciliation and provenance
Keep:
- [backend/app/services/reconciliation.py](../backend/app/services/reconciliation.py)
- The reconciliation_reports table and related schema logic

Why it matters:
- This is the product’s attestation layer.
- Every analysis should be traceable via analysis_run_id.
- The PRD should build around provenance, not treat it as compliance overhead.

Implementation note:
- Ensure every analysis run writes a record with:
  - source file reference
  - date range
  - currency conversions
  - excluded records and reasons
  - contextual markers applied
  - disabled features

### 4.2 Column mapping
Keep:
- [backend/app/services/column_mapping.py](../backend/app/services/column_mapping.py)
- [backend/app/services/column_mapping_store.py](../backend/app/services/column_mapping_store.py)
- The column_mappings table

Why it matters:
- This is one of Scanwick’s strongest differentiators.
- The mapping system should support a four-tier resolution strategy:
  - exact match
  - fuzzy match
  - confirm
  - unmapped

Implementation note:
- Monetary fields must remain blocked from fuzzy auto-apply.
- Save mapping state per merchant using a header signature so repeated uploads are nearly zero-touch.

### 4.3 Mono ingestion
Keep:
- [backend/app/services/mono_client.py](../backend/app/services/mono_client.py)
- [backend/app/services/mono_ingestion.py](../backend/app/services/mono_ingestion.py)

Why it matters:
- It is the current zero-effort ingestion path.
- It should remain an abstraction-friendly adapter that can later coexist with alternative open-banking providers.

### 4.4 Bank statement core
Keep these services:
- [backend/app/services/bank_ingestion.py](../backend/app/services/bank_ingestion.py)
- [backend/app/services/bank_pdf_ingestion.py](../backend/app/services/bank_pdf_ingestion.py)
- [backend/app/services/bank_account_integrity.py](../backend/app/services/bank_account_integrity.py)
- [backend/app/services/bank_transaction_classification.py](../backend/app/services/bank_transaction_classification.py)
- [backend/app/services/bank_cashflow.py](../backend/app/services/bank_cashflow.py)
- [backend/app/services/bank_dashboard.py](../backend/app/services/bank_dashboard.py)
- [backend/app/services/bank_income_stability.py](../backend/app/services/bank_income_stability.py)
- [backend/app/services/bank_abm.py](../backend/app/services/bank_abm.py)
- [backend/app/services/bank_cashflow_analysis.py](../backend/app/services/bank_cashflow_analysis.py)
- [backend/app/services/bank_fraud_risk.py](../backend/app/services/bank_fraud_risk.py)
- [backend/app/services/bank_loan_readiness.py](../backend/app/services/bank_loan_readiness.py)
- [backend/app/services/bank_lender_brief.py](../backend/app/services/bank_lender_brief.py)
- [backend/app/services/bank_playbook.py](../backend/app/services/bank_playbook.py)
- [backend/app/services/bank_cashflow_forecast.py](../backend/app/services/bank_cashflow_forecast.py)

### 4.5 Ecommerce — only as cash verification input
Keep these services:
- [backend/app/services/ecommerce_ingestion.py](../backend/app/services/ecommerce_ingestion.py)
- [backend/app/services/ecommerce_margins.py](../backend/app/services/ecommerce_margins.py)
- [backend/app/services/ecommerce_revenue.py](../backend/app/services/ecommerce_revenue.py)
- [backend/app/services/ecommerce_order_items.py](../backend/app/services/ecommerce_order_items.py)
- [backend/app/services/ecommerce_dashboard.py](../backend/app/services/ecommerce_dashboard.py)

### 4.6 Platform keepers
Keep:
- encryption and storage logic
- upload staging
- Redis client
- exchange rate and merchant currency services
- dataset detection
- recommendation generation
- AI client integration
- contextual markers
- merchant provisioning
- team management
- privacy
- RBAC and entitlement logic

---

## 5. Fixes that must be implemented

### 5.1 Bank loan readiness — ABM must carry balances forward
File:
- [backend/app/services/bank_loan_readiness.py](../backend/app/services/bank_loan_readiness.py)

Problem:
- Current logic averages only days that had transactions.
- Quiet days are omitted, which materially understates average monthly balance.

Why it matters:
- This directly affects loan-readiness outcomes and lender brief metrics.
- The report notes a 64.9% understatement in a real scenario.

How to fix:
- Carry the last known closing balance forward across days with no transactions.
- Build a daily balance series from the opening balance and transaction events.
- Fill in missing days with the prior closing balance.

Acceptance criteria:
- The ABM calculation reflects a realistic carry-forward balance.
- A regression test proves the corrected value against the supplied scenario.

Agent prompt:
> Fix the ABM calculation in bank_loan_readiness so it carries the last known closing balance forward across zero-activity days before averaging. Add a regression test that fails under the current logic and passes with the new implementation.

### 5.2 Bank loan readiness — use calendar months, not 30-day months
File:
- [backend/app/services/bank_loan_readiness.py](../backend/app/services/bank_loan_readiness.py)

Problem:
- The window calculation uses months × 30 days, which is inaccurate over calendar months.

How to fix:
- Use a calendar-aware month offset such as relativedelta.

### 5.3 Bank loan readiness — fixed weights and max achievable score
File:
- [backend/app/services/bank_loan_readiness.py](../backend/app/services/bank_loan_readiness.py)

Problem:
- The implementation silently renormalizes weights when data is missing.
- The reported weight percentage can drift from the PRD.

How to fix:
- Preserve the fixed 30/25/25/20 weight structure.
- If a component is unavailable, mark it as unearned rather than silently redistributing weight.
- Return a max-achievable score alongside the current score.

### 5.4 Bank loan readiness — CV boundary off by one
File:
- [backend/app/services/bank_loan_readiness.py](../backend/app/services/bank_loan_readiness.py)

Problem:
- A coefficient of variation of exactly 40 is treated as volatile, but the PRD says it should be moderate.

How to fix:
- Change the boundary to use <= 40 for the moderate classification.

### 5.5 Lender brief — rebuild rendering and content structure
File:
- [backend/app/services/bank_lender_brief.py](../backend/app/services/bank_lender_brief.py)

Problem:
- The output uses the wrong section keys.
- The values are raw dictionaries instead of prose.
- Rendering is truncated and unreadable.

How to fix:
- Align section names with the PRD: business overview, income summary, expense summary, risk assessment, creditworthiness assessment, recommendation paragraph.
- Generate real narrative prose for each section.
- Render wrapped, paginated text instead of writing a single truncated line.
- Add deterministic fallback text if the AI generation fails.

Acceptance criteria:
- The lender brief produces readable prose.
- No dict string appears in the PDF or output.
- One failed section does not poison the entire brief.

Agent prompt:
> Rebuild the lender brief generation in bank_lender_brief so it emits structured prose sections matching the PRD, uses wrapped paginated rendering, and falls back to deterministic text if AI generation fails. Do not output raw Python dictionaries.

### 5.6 Fraud risk — add contributory savings detection
File:
- [backend/app/services/bank_fraud_risk.py](../backend/app/services/bank_fraud_risk.py)

Problem:
- The current z-score and structuring logic flags ajo, esusu, and adashe as fraud.

How to fix:
- Add a positive-signal pattern for contributory savings behavior.
- Treat this as a legitimate pattern, not as fraud.

### 5.7 Role-based access — loan officers must not see full transaction detail
File:
- [backend/app/routes/bank.py](../backend/app/routes/bank.py)

Problem:
- A single READ_ROLES set grants loan officers access to transaction-level endpoints.

How to fix:
- Split roles into:
  - full-data roles for bank owners/admins/viewers
  - brief-only roles for loan officers
- Restrict transaction-level endpoints to full-data roles.

Acceptance criteria:
- Loan officer receives 403 or equivalent denial for transaction-detail endpoints.

Agent prompt:
> Update the bank routes so loan officers can access lender-brief and summary-style outputs only, while transaction-level diagnostics are restricted to full-data roles. Add tests covering the authorization split.

### 5.8 Ecommerce revenue — use base currency amount
File:
- [backend/app/services/ecommerce_revenue.py](../backend/app/services/ecommerce_revenue.py)

Problem:
- The component aggregates original-currency values and labels the total with the first row’s currency.

How to fix:
- Use base_currency_amount when available.
- Set the currency from the merchant’s base currency.
- Flag missing base currency values in meta.missing_fields.

### 5.9 Ecommerce ingestion — deduplication for rows without order ID
File:
- [backend/app/services/ecommerce_ingestion.py](../backend/app/services/ecommerce_ingestion.py)

Problem:
- Rows without an order ID bypass the dedup guard and can be ingested multiple times.

How to fix:
- Generate a deterministic surrogate ID when external_order_id is missing.
- Use a hash based on merchant_id, source signature, date, sku, quantity, gross revenue, and row index.
- Add a database-level unique constraint so duplicates fail safely.

Agent prompt:
> Implement deterministic surrogate ID generation for ecommerce rows that do not have an external order ID, and add a unique constraint at the persistence layer so duplicate rows cannot be inserted twice.

### 5.10 Date parsing — make it locale-aware and explicit
Files:
- [backend/app/services/ecommerce_ingestion.py](../backend/app/services/ecommerce_ingestion.py)
- [backend/app/services/bank_ingestion.py](../backend/app/services/bank_ingestion.py)

Problem:
- Dates parse month-first by default and silently misparse day-first input.

How to fix:
- Thread date_locale from stored mapping rules into the ingestion code.
- Default parsing to day-first behavior.
- Flag ambiguous values rather than guessing.
- Emit named warnings for ambiguous or rejected dates.

### 5.11 Quality reporting — every rejection needs a warning
Problem:
- Rejected rows currently emit no meaningful warnings.

How to fix:
- Ensure each rejected row contributes a named warning entry.
- Surface the warning in the quality report and downstream diagnostic UI.

### 5.12 RBAC and merchant identity — derive from session, not client input
Files:
- [backend/app/routes/bank.py](../backend/app/routes/bank.py)
- [backend/app/services/merchant_provisioning.py](../backend/app/services/merchant_provisioning.py)
- The relevant route and dependency layers

Problem:
- Merchant identity is client-supplied and sometimes computable from a public identifier.

How to fix:
- Derive merchant_id from the authenticated session and route dependency context.
- Remove client-supplied merchant_id from request handling where possible.
- Enforce ownership checks before any write or read action.

---

## 6. Delete and mothball plan

### 6.1 Delete the sales analyzer
Delete all sales-oriented surfaces, including:
- sales_deals
- sales_forecast
- sales_ingestion
- sales_notifications
- sales_pipeline
- sales_playbook
- sales_postmortem
- sales_quality
- sales_rbac_scoping
- sales_rep_leaderboard
- sales_rep_trajectory
- sales_slippage
- sales_stage_timing
- sales_stage_velocity
- sales_stagnation
- sales_win_dna
- sales_win_probability
- deals
- stage_transition_logs
- all sales routes

Why:
- These features are not aligned with the target market.
- They add build cost and confusion without enough customer value.

### 6.2 Delete ecommerce depth features
Delete:
- ecommerce_rfm
- ecommerce_rfm_endpoint
- ecommerce_churn
- ecommerce_holt_winters
- ecommerce_inventory_forecast
- ecommerce_sku_matrix
- ecommerce_diagnostics
- ecommerce_returns
- ecommerce_ad_kill_switch
- ecommerce_playbook
- ecommerce_olist_adapter
- rfm_segment_assignments
- sku_inventory
- ad_kill_audit_log

Why:
- These features depend on data the target merchant base does not generally have.

### 6.3 Delete bank features that do not support a credit decision
Delete for now:
- bank_customer_segmentation
- bank_revenue_patterns

Why:
- They are not necessary for the lender-facing assessment path.

### 6.4 Mothball payments and reporting features
Mothball:
- [backend/app/routes/payments.py](../backend/app/routes/payments.py)
- [backend/app/services/payments.py](../backend/app/services/payments.py)
- paystack and flutterwave client modules
- subscriptions and payment_transactions
- generated_reports and report_schedules
- notification scheduling layer

Why:
- The pilot and institutional workflow do not require live charging in the current scope.
- Keeping these live adds attack surface without product value.

---

## 7. Build — new product capabilities that must be added

### 7.1 Identity layer
Build:
- BVN capture and verification flow
- Business entity model distinct from the user account
- Link between one business and several accounts

Why:
- Open-banking and multi-account assessment require an identity anchor.

### 7.2 Multi-account consolidation
Build:
- One business, several account records, one assessment view
- Consolidation logic that is not an optional enhancement

### 7.3 Cash-gap reconciliation
Build:
- A first-class cash-gap reconciliation output that compares bank inflows with uploaded sales records.
- Report the difference as verified unbanked cash revenue.

Why:
- This is the feature that justifies ecommerce ingestion in the new product model.

### 7.4 Consent, retention, and audit
Build:
- consent_records
- data retention policy support
- delete-my-data workflow
- data_access_log

Why:
- These are required for institutional trust and compliance.

### 7.5 Verifiable assessment link
Build:
- assessment share links
- view history and expiry
- shareable assessment view that points to a verifiable assessment record rather than a static PDF

### 7.6 Outcome tracking
Build:
- assessments
- assessment_outcomes
- logging of score issuance and repayment results

### 7.7 Currency reality
Build:
- reporting in both nominal and real terms
- inflation-aware trend reporting

---

## 8. Data model changes

### 8.1 Tables that survive
- accounts
- bank_transactions
- bank_account_identifiers
- orders
- order_items
- uploads
- column_mappings
- contextual_markers
- reconciliation_reports
- merchant_settings
- exchange_rates
- user_merchant_roles
- users and auth tables
- login_events
- team_invites
- notification_preferences

### 8.2 Tables to delete
- deals
- stage_transition_logs
- rfm_segment_assignments
- sku_inventory
- ad_kill_audit_log
- postmortem_reports
- returns

### 8.3 Tables to mothball
- subscriptions
- payment_transactions
- generated_reports
- report_schedules

### 8.4 New tables to define
- business_entities
- consent_records
- data_access_log
- assessments
- assessment_shares
- assessment_outcomes

### 8.5 Role model redesign
The current generic role model is insufficient for the new product.

The PRD should define semantic roles such as:
- Account Owner or CFO
- Accountant
- Loan Officer
- Analyst read-only

This redesign is necessary because the current generic role matrix cannot express a loan officer seeing the lender brief while being blocked from transaction detail.

---

## 9. Endpoints that survive, delete, and add

### 9.1 Endpoints that survive
Keep these as the core API surface:
- POST /api/v1/bank/upload
- GET /api/v1/bank/upload/{id}/quality-report
- GET /api/v1/bank/dashboard/summary
- GET /api/v1/bank/diagnostic/income-stability
- GET /api/v1/bank/diagnostic/abm
- GET /api/v1/bank/diagnostic/cashflow-analysis
- GET /api/v1/bank/predictive/fraud-risk
- GET /api/v1/bank/predictive/loan-readiness
- GET /api/v1/bank/predictive/cashflow-forecast
- GET /api/v1/bank/ai/lender-brief
- GET /api/v1/bank/ai/financial-health-playbook
- GET /api/v1/reconciliation/{analysis_run_id}
- POST /api/v1/upload/csv
- POST /api/v1/mapping/detect
- POST /api/v1/mapping/confirm
- Auth, team, and privacy routes

### 9.2 Endpoints to delete
Remove everything under /api/v1/sales.

Keep ecommerce endpoints only for:
- upload
- quality report
- minimal revenue endpoint for cash-gap comparison

### 9.3 New endpoints to add
- markers CRUD
- BVN and entity endpoints
- consent endpoints
- assessment share link endpoints
- institution-facing assessment API

---

## 10. Rules for writing the new PRD

1. One document, not four.
2. The PRD must include the security and compliance layer.
3. Define a data maturity ladder:
   - Mono connected
   - Statement uploaded
   - Statement plus sales records
   - Multi-account
4. Never label a number with the wrong economic concept.
5. Write accuracy targets so they can be tested and verified.
6. Write the PRD after the interviews, not before.

---

## 11. Developer implementation checklist

### Backend
- [ ] Fix ABM carry-forward logic.
- [ ] Fix month window logic.
- [ ] Fix lender-brief prose rendering.
- [ ] Fix role-based access restrictions for loan officers.
- [ ] Fix mixed-currency revenue aggregation.
- [ ] Fix date parsing and ambiguous-date handling.
- [ ] Fix deduplication for rows without order ID.
- [ ] Add warnings for every rejected row.
- [ ] Derive merchant identity from session context.
- [ ] Add new identity and assessment models.
- [ ] Implement consent and audit flows.
- [ ] Remove or mothball sales and payment surfaces.

### Frontend
- [ ] Update roles and permissions UI.
- [ ] Surface lender-brief output correctly.
- [ ] Display quality warnings and rejection reasons.
- [ ] Show assessment share and outcome state.

### Tests
- [ ] Add regression tests for ABM.
- [ ] Add authorization tests for loan officers.
- [ ] Add lender-brief rendering tests.
- [ ] Add date-parsing tests.
- [ ] Add deduplication tests.
- [ ] Add mixed-currency aggregation tests.
- [ ] Add consent and assessment flow tests.

---

## 12. Copy-paste prompts for coding agents

### Prompt 1 — general implementation sweep
> Review the Scanwick developer scope document and implement the changes in priority order. Start with the critical correctness and security issues: bank loan-readiness ABM calculations, loan-officer RBAC scope, lender-brief rendering, date parsing, ecommerce deduplication, and mixed-currency revenue aggregation. Update backend services and routes, add regression tests first, keep the existing reconciliation and mapping architecture intact, and avoid adding new product features until the core fixes are complete.

### Prompt 2 — ABM and loan-readiness repair
> Update [backend/app/services/bank_loan_readiness.py](../backend/app/services/bank_loan_readiness.py) to carry the last known closing balance forward across zero-activity days, use calendar-aware month windows, preserve fixed weights, return a max-achievable score, and classify a coefficient of variation of 40 as moderate. Add tests that fail on the current implementation and pass after the fix.

### Prompt 3 — lender brief rebuild
> Rebuild [backend/app/services/bank_lender_brief.py](../backend/app/services/bank_lender_brief.py) so it produces narrative prose sections matching the PRD, uses wrapped paginated rendering, and falls back to deterministic text if AI generation fails. Ensure the output does not render raw Python dictionaries.

### Prompt 4 — RBAC scope tightening
> Update [backend/app/routes/bank.py](../backend/app/routes/bank.py) so loan officers can view lender-brief and summary outputs but cannot access transaction-level detail or full diagnostic views. Add tests that verify 403 responses for the restricted endpoints.

### Prompt 5 — ecommerce deduplication hardening
> Update [backend/app/services/ecommerce_ingestion.py](../backend/app/services/ecommerce_ingestion.py) to generate a deterministic surrogate ID for rows without an external order ID, and enforce a database-level unique constraint so duplicate ingestion cannot silently double-count revenue.

### Prompt 6 — date parsing and quality warnings
> Update the bank and ecommerce ingestion services to parse dates using locale-aware logic from stored mapping rules, flag ambiguous dates instead of guessing, and emit named warnings for every rejected row in the quality report.

### Prompt 7 — product-scope cleanup
> Remove or mothball the sales-analysis surfaces and non-core ecommerce features described in the scope document. Keep the core reconciliation, mapping, bank-analysis, and cash-verification paths intact, and delete the old sales routes/models/tables and the extra ecommerce depth features that are not required for the new product direction.

---

## 13. Definition of done

The implementation work is not complete until:
- the critical correctness issues are fixed and tested
- the lender-facing outputs are readable and correct
- loan-officer permissions are correct
- the ingestion and deduplication paths are durable
- the new identity, consent, and assessment model requirements are planned and implemented
- the sales analyzer and non-core features are removed or mothballed
- the PRD has been written from the corrected, product-centered perspective
