# Bank QA — Cumulative Issue Tracker

Append-only. Do not remove or overwrite prior entries; new prompts add new issues below.

---

## Issues established during Bank Prompt 1 (Dataset Inspection)

### Issue B1-1: Ambiguous debit+credit row in primary file
- **Description:** `scanwick_test_bank_statement.csv` row 158 ("LARGE TRANSFER - UNKNOWN BENEFICIARY") has both `debit` and `credit` populated simultaneously, which the file's own convention treats as mutually exclusive.
- **Severity:** Medium
- **Impact:** The signed amount for this one row is derived via netting (`credit − abs(debit)`) rather than a literal column read.
- **Root cause:** Source data anomaly (possibly a deliberately placed synthetic test case).
- **Suggested fix:** None required — code handles it without crashing; worth a manual sanity check.
- **Blocks later prompts:** No.
- **Status:** Resolved/confirmed benign in Prompt 3 — row appears correctly as one coherent top-payee entry in all 3 copies of the file.

### Issue B1-2: Missing `balance` values in `scanwick_bank_savings_clean.csv`
- **Description:** 263 of 1,670 rows (~15.7%) have a null `balance`, including the very first row.
- **Severity:** Medium
- **Impact:** Affects precision of balance-integrity derivation for this file.
- **Root cause:** Source data completeness gap.
- **Suggested fix:** None required at the code level (existing fallback logic handles it).
- **Blocks later prompts:** No.
- **Status:** Escalated in Prompt 2 — see B2-3 (this "precision" concern was confirmed to be a real integrity *failure*, not just imprecision).

### Issue B1-3: `value_date`, `channel`, `transaction_reference` not captured by ingestion
- **Description:** Real, clean columns present in `scanwick_bank_savings_clean.csv`/`scanwick_bank_wallet_clean.csv` that `extract_canonical_bank_rows()` does not read at all.
- **Severity:** Low
- **Impact:** Real, usable data left uncaptured (channel diversity, value-date, transaction reference for future dedup/reconciliation use).
- **Root cause:** No corresponding keyword-detection lists implemented for these fields.
- **Suggested fix:** Add `_VALUE_DATE_KEYWORDS`/channel-to-`mode` mapping if these fields become needed by a future diagnostic.
- **Blocks later prompts:** No.
- **Status:** Open, informational.

---

## Issues established during Bank Prompt 2 (Ingestion Testing)

### Issue B2-1: `is_own_account_transfer` detection not wired into ingestion
- **Description:** `detect_own_account_transfers()` (`app/services/bank_account_integrity.py:88`) exists and is unit-tested, but is never called automatically anywhere in the real ingestion path — confirmed via a full-codebase search (its only callers are its own unit tests).
- **Severity:** High
- **Impact:** Every ingested row's `is_own_account_transfer` stays `False` unless something calls this function manually.
- **Root cause:** Architectural gap — the function was built but never wired into `ingest_bank_dataframe`/a scheduled job/an endpoint.
- **Suggested fix:** Wire this into ingestion (per-account-set, post-ingestion) or expose it as an explicit, deliberately-triggered step with safeguards (see B3-1 below for why "just wire it in as-is" is not sufficient).
- **Blocks Prompt 3/4:** No, but materially affects how their results should be interpreted.
- **Status:** **Confirmed to cause a severe, concrete dashboard-level defect in Prompt 3 — see B3-1.**

### Issue B2-2: No duplicate-ingestion protection
- **Description:** No unique constraints on `account_number_hash` or any transaction-identity field; no dedup-check logic anywhere in `ingest_bank_dataframe`/`write_canonical_bank_rows`.
- **Severity:** High
- **Impact:** Re-ingesting the same file creates a fully duplicated Account + BankTransaction set every time, confirmed twice over in Prompt 2 (once accidentally via a crashed-attempt orphan, once intentionally).
- **Root cause:** No dedup mechanism designed/implemented.
- **Suggested fix:** Add a content-hash or (account_number_hash, statement_period) based duplicate check before creating a new Account row.
- **Blocks Prompt 3/4:** No, but is the direct root cause of B3-1's most dramatic manifestation (three copies of one file coexisting and producing inconsistent dashboard numbers).
- **Status:** **Confirmed to directly cause dashboard inconsistency in Prompt 3 — see B3-1.**

### Issue B2-3: Balance-integrity check fails for 2 of 3 real files
- **Description:** `scanwick_bank_savings_clean.csv` fails with discrepancy 32.76; `scanwick_bank_wallet_clean.csv` fails with discrepancy 800,624.14 (the larger, despite this file having zero null balance values and being rated "cleanest" in Prompt 1).
- **Severity:** High (wallet file), Medium (savings file)
- **Impact:** Recorded account balances do not reconcile against the sum of ingested credits/debits.
- **Root cause:** Unknown — could be source-data recording error, or a real gap in how opening/closing balance is derived from partial statement exports.
- **Suggested fix:** Investigate why wallet file's discrepancy is so large despite complete balance data; consider surfacing `balance_integrity_passed` more prominently in dashboard/diagnostic output (see B3-2).
- **Blocks Prompt 3/4:** No.
- **Status:** Open. **Confirmed in Prompt 3 that this failure is invisible from the dashboard endpoint's own output — see B3-2.**

### Issue B2-4: `account_number_hash` cannot recognize repeat uploads of the same account
- **Description:** None of the three real files has an account-number column, so the hash falls back to `hash_value(f"unknown-account:{upload_id}")` — derived from the upload ID, not the real account.
- **Severity:** Medium
- **Impact:** Every re-upload of the same file is indistinguishable from an unrelated new account.
- **Root cause:** Dataset limitation combined with the fallback design.
- **Suggested fix:** None at the code level for these specific files; would need a real account-number column in the source data, or a content-based fingerprint as a secondary matching key.
- **Blocks Prompt 3/4:** No.
- **Status:** Open, contributes to B2-2/B3-1's severity (compounds the duplicate-ingestion problem since accounts can't even be recognized as "the same" after the fact).

---

## Newly discovered Bank Prompt 3 issues (Dashboard Endpoint Testing)

### Issue B3-1: `is_own_account_transfer` false positives severely corrupt dashboard output — up to 100% of an account's outflows suppressed
- **Description:** Confirmed via direct SQL against the real, currently-populated `bank_transactions` table: 933 of 933 debit transactions (100%) in the `scanwick_bank_savings_clean.csv` account are flagged `is_own_account_transfer=True`, causing the dashboard's reported outflows for that account to be **0** instead of the real 3,794,287.92 (905 transactions). The wallet account shows the same problem at smaller scale (240/5,662, ~4.2%). Additionally, two of the three copies of the primary file (`scanwick_test_bank_statement.csv`) report numbers 3,600,000 lower than the third copy, purely due to when the (manually-triggered) detection pass happened to run relative to each copy's ingestion.
- **Severity:** **Critical**
- **Impact:** Directly corrupts the dashboard's headline `outflows` figure — potentially the single most-viewed number on this whole analyzer for a real user. A savings account with real, substantial spending activity would appear to have none at all.
- **Root cause:** Two compounding factors, both already logged in Prompt 2 (B2-1, B2-2): (a) `detect_own_account_transfers`'s greedy same-day/amount-tolerance matching has no safeguard against false positives when run across large, multi-account, real-world data with common round-number transaction amounts; (b) because it is never auto-wired into ingestion, it only ran once, manually, as a single global pass across whatever accounts existed for this user at that moment — meaning its results are entirely dependent on incidental timing/ordering, not a deterministic property of the data.
- **Suggested fix:** Tighten the matching algorithm's tolerance/uniqueness requirements before treating a debit/credit pair as confirmed (e.g., require a materially rarer amount, or a stated counterparty-account reference, not just amount+date proximity); and/or decide deliberately when/how often this detection should run in production (not as an ad-hoc manual call) so its results are reproducible rather than order-dependent.
- **Blocks Prompt 4:** No — Prompt 4 can proceed, but every diagnostic built on `eligible_transactions()` (income-stability, ABM, cashflow-analysis, revenue-patterns, etc.) will inherit this exact same contamination for the savings account and should not be treated as a fresh, independent finding when it resurfaces there.

### Issue B3-2: Balance-integrity failures are invisible from the dashboard endpoint
- **Description:** `dashboard/summary` returns `Account.opening_balance`/`closing_balance` as plain numbers with no indication of whether they reconcile against the transaction history. Both accounts with a confirmed balance-integrity failure (B2-3) return their (unreconciled) balances with no flag, warning, or `disabled_features` entry.
- **Severity:** Medium
- **Impact:** A user viewing this dashboard has no way to know the account's balance figures failed reconciliation elsewhere in the system.
- **Root cause:** `compute_dashboard_summary` reads `account.opening_balance`/`account.closing_balance` directly; `balance_integrity_passed`/`balance_discrepancy` exist on the `Account` model but are never surfaced in this endpoint's response.
- **Suggested fix:** Consider including `balance_integrity_passed` (or a corresponding `disabled_features`/warning entry) in the dashboard response when it's `False`.
- **Blocks Prompt 4:** No.

### Issue B3-3: `disabled_features` has no implemented condition for `dashboard/summary`
- **Description:** The route never passes `disabled_features` to `success_response`, so it is unconditionally `[]` regardless of data volume, account age, or any other factor. Confirmed empirically across all 5 accounts tested, including ones with as little as ~12 months and as much as ~37 months of data.
- **Severity:** Low (factual/informational, not necessarily a defect)
- **Impact:** None observed — just means this endpoint never degrades gracefully via the standard mechanism; it either returns full data or (implicitly) would error if `account_id` doesn't exist.
- **Root cause:** Not implemented — no minimum-data threshold was ever coded for this specific endpoint (unlike `diagnostic/income-stability`'s 3-month minimum).
- **Suggested fix:** None required unless product intent calls for a minimum-data gate on the summary dashboard too.
- **Blocks Prompt 4:** No.

### Issue B3-4: Pre-existing RBAC scaffolding data stored in an inconsistent UUID format
- **Description:** A `user_merchant_roles` row for this exact (user, merchant, vertical) already existed in `app.db` before this prompt, but its `merchant_id` was stored as a dashed 36-character UUID string, while `accounts.user_id` (the same conceptual value) is stored via the ORM's 32-character hex form — the two never string-match, so the real RBAC check silently 403'd until a second, ORM-consistent row was added.
- **Severity:** Low (this specific row is test/verification scaffolding from an earlier ad-hoc script in this session, not application-generated data)
- **Impact:** None on real application behavior — the actual app always writes/reads through the ORM consistently. Noted here only because it caused a genuine 403 during this prompt's execution and is worth being aware of if similar ad-hoc scaffolding is reused later.
- **Root cause:** An earlier verification script inserted this row via raw SQL rather than the ORM.
- **Suggested fix:** None needed in application code. If cleaning up test scaffolding later, this specific malformed row can be identified by its 36-character `merchant_id` string.
- **Blocks Prompt 4:** No.

---

## Previously Known Issues carried into Bank Prompt 4 (Diagnostics Endpoint Testing)

Confirmed still applicable, re-verified against the diagnostic endpoints specifically (not re-logged as new):

- **B3-1** (`is_own_account_transfer` contamination) — confirmed to propagate into `cashflow-analysis` and `customer-segmentation` for the savings account (`cash_buffer_months`/`expense_concentration_ratio_pct` return `null`, only 2 counterparties appear instead of the real set). No new behavior beyond what B3-1 already predicted.
- **B2-3** (balance-integrity failures) — checked against `abm`/`cashflow-analysis` for the wallet account; no incorrect output observed as a direct result (both endpoints operate on `balance_after` day-to-day values, which recomputed correctly). Noted as checked, not newly impactful.

## Newly Discovered Bank Prompt 4 issues (Diagnostics Endpoint Testing)

### Issue B4-1: ABM `trend` label is sign-incorrect for accounts with a negative 12-month average balance
- **Description:** `compute_abm` (`app/services/bank_loan_readiness.py`) derives `trend` from `pct_change = (abm_3m - abm_12m) / abm_12m * 100`, labeling `improving` when `pct_change > 2`. For the primary test account (a genuinely, persistently overdrawn account: `abm_12m = -2,915,069.24`, `abm_3m = -5,976,353.55` — i.e. the account's average balance became *more* negative in the recent window, a real worsening), the endpoint returns `trend: "improving"`. Confirmed via independent recomputation that `abm_3m`/`abm_6m`/`abm_12m` themselves are numerically correct (exact match to the cent) — only the derived label is wrong, and specifically only when the 12-month baseline is negative (dividing a more-negative recent average by a negative baseline flips the sign of the resulting percentage).
- **Severity:** High
- **Impact:** A loan officer or business owner viewing this diagnostic for an overdrawn account would be told their average balance trend is "improving" when it is factually getting worse — directly contradicts the diagnostic's stated purpose.
- **Root cause:** The `pct_change` formula does not account for the sign of `abm_12m` when it's negative; the two accounts with a positive `abm_12m` (savings, wallet) both correctly show `declining` in this same test run, confirming the bug is specific to the negative-baseline case, not universal.
- **Suggested fix:** Base the trend on the sign of `abm_3m - abm_12m` directly (a real increase vs. decrease in average balance) rather than a percentage computed by dividing by a value that can itself be negative; or explicitly branch the percentage formula's sign handling when `abm_12m < 0`.
- **Blocks Prompt 5:** No — Prompt 5 (predictive models) can proceed, but `loan-readiness`'s composite score reuses this same `compute_abm`/trend logic (per `app/services/bank_loan_readiness.py`'s own docstring), so this bug should be assumed to also affect the `abm_trend` component of the loan-readiness score for any account with a negative 12-month average balance, until checked directly in that prompt.

### Issue B4-2: Inconsistent insufficient-data signaling across the 5 diagnostic endpoints
- **Description:** `income-stability` and `abm` use the shared `disabled_features` mechanism (clear `feature_name`/`reason`/`data_needed`) when data is insufficient. `cashflow-analysis`, `customer-segmentation`, and `revenue-patterns` do not — they silently return `null`/empty-list values in `data` with `disabled_features` always `[]`, confirmed via safe in-memory calls with an empty transaction list for all 5 (no DB writes involved).
- **Severity:** Low
- **Impact:** Not a crash and not misleading (null/empty values are honest, not fabricated), but a consuming client can't distinguish "genuinely zero" from "not enough data to compute" for 3 of the 5 diagnostics the way it can for the other 2.
- **Root cause:** `cashflow-analysis`/`customer-segmentation`/`revenue-patterns`'s route handlers never pass `disabled_features` to `success_response`, and their service functions have no minimum-data gate at all.
- **Suggested fix:** Consider adding an explicit minimum-data condition (e.g. matching `income-stability`'s 3-month threshold) to these three for consistency, if that's the intended product behavior.
- **Blocks Prompt 5:** No.

---

## Previously Known Issues carried into Bank Prompt 5 (Predictive Model Testing)

- **B4-1** (ABM trend sign-incorrect) — confirmed to have a concrete, quantified downstream effect on `loan-readiness`: inflates the primary account's score by the full 25-point `abm_trend` weight and suppresses a legitimate improvement recommendation. New, measurable impact — logged as **B5-3** below (cross-referenced, not a duplicate).
- **B3-1** (transfer-flag contamination, savings account) — confirmed to gracefully disable `cash_buffer` in `loan-readiness` (properly listed in `disabled_components`) and correctly null `cash_runway` in `cashflow-forecast`. No new behavior — both are correct graceful degradations of the already-known contamination.
- **B2-3** (balance-integrity failures) — confirmed correctly reflected in `fraud-risk`'s `statement_integrity.balance_check`/`date_continuity` (both `"failed"` for savings/wallet, `"passed"` for primary). No incorrect score resulted — these are informational fields, not scoring inputs. No new behavior.
- **B1-1** (ambiguous debit+credit row, primary file) — newly linked to a concrete effect: plausibly causes `fraud-risk`'s `statement_integrity.sequential_ordering` to report `"failed"` for the primary account (otherwise fully passing). Logged as **B5-4** below.

## Newly Discovered Bank Prompt 5 issues (Predictive Model Testing)

### Issue B5-1: Cash-runway calculation produces backwards/misleading results for already-overdrawn accounts
- **Description:** `_cash_runway_months` (`app/services/bank_cashflow_forecast.py`) computes `current_balance / avg_monthly_net_burn`. For the primary account (`current_balance = -6,521,829.63`, already negative), `primary_scenario_months = -10.7` and `stress_scenario_months = -5.9` — the stress scenario's number is numerically *greater* (less negative) than the primary scenario's, the opposite of "stress should show an equal-or-shorter runway."
- **Severity:** High
- **Impact:** A lender or business owner comparing the two numbers at face value would read `-5.9 > -10.7` as "the stress scenario is better," backwards from the actual, worse financial reality (a higher burn rate under stress).
- **Root cause:** The formula was designed for a positive starting balance (months until reaching zero); it was never guarded against a starting balance that's already negative, where dividing by a larger positive burn rate produces a less-negative (not more-negative) result.
- **Suggested fix:** For `current_balance <= 0`, return `0` (already out of runway) rather than a signed division result, or otherwise special-case the negative-balance path so "worse" always reads as a smaller/more-negative number.
- **Blocks Prompt 6:** No.

### Issue B5-2: `loan-readiness` scores a zero-transaction account as perfectly creditworthy (100/Tier A)
- **Description:** Calling `compute_loan_readiness(None, [])` returns `loan_readiness_score: 100, creditworthiness_tier: 'A'`. `income_stability`/`abm_trend`/`cash_buffer` correctly become unavailable with no data, but `compute_fraud_risk` returns a trivial 0-risk score for empty input rather than also signaling "no data" — so `fraud_risk_inverted` (100) becomes the *only* available component and receives 100% of the re-normalized weight.
- **Severity:** Critical
- **Impact:** An account with zero verifiable transaction history — the least creditworthy-assessable case possible — produces the single best possible score and tier. This is the kind of result a real lending decision could be made on.
- **Root cause:** `compute_fraud_risk` has no minimum-data floor (no data = no fraud signals = a perfect score by default), and `compute_loan_readiness`'s weight-renormalization has no floor on how few components must be available before it's willing to produce a score at all.
- **Suggested fix:** Either make `compute_fraud_risk` return `None`/a distinct "insufficient data" state for very small transaction counts (so it can join the other three in `disabled_components`), or add an explicit minimum-available-components gate to `compute_loan_readiness` (e.g. require at least 2 of 4, or require `income_stability` specifically) before producing a score.
- **Blocks Prompt 6:** No — Prompt 6 (AI layer) should be aware this same zero-data edge case may need checking if the lender-brief/financial-health-playbook endpoints consume `loan_readiness_score` directly.

### Issue B5-3: Confirmed quantified impact of B4-1 on `loan-readiness`
- **Description:** See "Previously Known Issues" above — the primary account's `abm_trend` component contributes the full 25.0/25.0 weighted points to its `loan_readiness_score` (62 total) because it's wrongly labeled `"improving"`, and the same mislabeling suppresses a legitimate `abm_trend` entry in `improvement_recommendations`.
- **Severity:** High
- **Impact:** A materially inflated loan-readiness score and a missing recommendation for a real, deteriorating account.
- **Root cause:** B4-1 (`app/services/bank_loan_readiness.py`'s `compute_abm` trend-sign logic), not a new defect in `loan-readiness` itself — logged separately here only because this is where its quantified downstream effect was first measured.
- **Suggested fix:** Fix B4-1 at the source; no separate fix needed in `loan-readiness` itself.
- **Blocks Prompt 6:** No.

### Issue B5-4: Confirmed concrete effect of B1-1 on fraud-risk's statement integrity check
- **Description:** The primary file's one ambiguous debit+credit row (B1-1) plausibly causes `fraud-risk`'s `statement_integrity.sequential_ordering` to report `"failed"` for an otherwise fully-passing account.
- **Severity:** Low
- **Impact:** Minor — one informational integrity field reads "failed" instead of "passed"; does not affect the fraud score itself.
- **Root cause:** B1-1 (source data anomaly), not a new code defect — logged here only because this is where its first concrete downstream effect was observed. Not confirmed with row-level certainty.
- **Suggested fix:** None required; noted for completeness.
- **Blocks Prompt 6:** No.

### PaySim fraud evaluation — Not Implemented (confirmed, not a defect)
- **Description:** `PS_20174392719_1491204439457_log.csv`'s columns don't match any accepted date-keyword in `COLUMN_CANDIDATES['date']` (`app/utils/analyzer.py`), so it cannot pass through `ingest_bank_csv` (100% of rows would be rejected for missing `transaction_date`), and `compute_fraud_risk` requires real `BankTransaction` ORM objects, not raw PaySim fields.
- **Severity:** N/A (build-completeness observation, not a QA failure, per this prompt's explicit instruction)
- **Blocks Prompt 6:** No.

---

## Previously Known Issues carried into Bank Prompt 6 (AI Layer Testing)

- **B4-1 / B5-3** (ABM trend sign-incorrect, inflates loan-readiness) — **confirmed to propagate verbatim into the lender-brief.** The primary account's `sections.loan_readiness_assessment.score_breakdown.abm_trend` shows `trend: "improving"` and `contribution: 25.0/25.0`, matching Prompt 5's numbers exactly. This also suppresses the primary account's `abm_trend` entry from `improvement_recommendations` (only a `cash_buffer` entry is present), confirmed against the actual live response. A lender reading this brief sees an unqualified "improving" label for an account whose true 12-month trend is worsening, with no caveat anywhere in the document. No new behavior — a confirmed, exact propagation of an existing defect into a new, more consequential surface (a lender-facing document rather than a raw diagnostic).
- **B5-2** (`compute_loan_readiness([])` scores a zero-transaction account 100/Tier A) — **confirmed to reproduce identically** inside `get_lender_brief_response(None, [])` (safe in-memory sparse-data test): `loan_readiness_score: 100`, `creditworthiness_tier: "A"`, `fraud_risk_inverted` contributing 100% of weight. Its compounded, lender-brief-specific impact (no disabled-features warning anywhere in this endpoint) is logged as new issue **B6-4** below.
- **B3-1** (savings account transfer-flag contamination) — **confirmed to propagate into the savings account's lender-brief** as `cash_flow_analysis.cash_buffer_months: null` and `cash_buffer` present in `disabled_components`, consistent with the zero-visible-outflow condition already documented in Prompts 3–5. The financial-health-playbook's Gemini-generated recommendation (`REC_MISSING_CASH_BUFFER_005`) independently notices the null value and recommends a generic "verify data completeness" action — a reasonable diagnosis given what little context it was given, but it has no way to name the true root cause (the AI's context never includes raw transaction-level flag data). No new behavior.
- **B2-3** (balance-integrity failures, savings/wallet) — confirmed reflected identically in the lender-brief's `risk_flags.statement_integrity.balance_check: "failed"` for both accounts. No AI narrative comments on this field directly (lender-brief's own `lender_recommendation` never ran successfully in any tested case — see B6-1). No new behavior.
- **B5-4** (ambiguous row → `sequential_ordering` failure, primary account) — confirmed reflected identically in the lender-brief's `risk_flags.statement_integrity.sequential_ordering: "failed"` for the primary account. No new behavior.
- **B5-1** (cash-runway backwards for overdrawn accounts) — **confirmed NOT to propagate into the AI layer.** Neither `bank_lender_brief.py` nor `bank_playbook.py` calls `compute_cashflow_forecast` anywhere; no "runway"/"forecast" concept appears in either endpoint's context data or in any of the 6 real Gemini responses read. Explicitly does not apply here.
- **B1-1/B1-2/B1-3** — no additional AI-layer-specific effects beyond what's already captured via B2-3/B5-4 above; the uncaptured columns from B1-3 (`value_date`/`channel`/`transaction_reference`) don't feed any `compute_*` function consumed by either AI endpoint.

## Newly Discovered Bank Prompt 6 issues (AI Layer Testing)

### Issue B6-1: `lender_recommendation` is always empty — the Gemini call for the lender-brief endpoint is guaranteed to fail given this environment's real API latency
- **Description:** Across all 4 real-Gemini calls to the lender-brief path tested (primary account, savings account, wallet account, and a safe in-memory zero-transaction call), `sections.lender_recommendation` was `[]` in every single case, with the log line `[recommendations] Gemini call failed for analyzer_type=bank: Gemini API call failed after 3 attempts` printed every time (4/4). The sibling `financial-health-playbook` endpoint, calling the exact same `generate_recommendations("bank", ...)` function with the same "bank" prompt template against the same real Gemini API/model, succeeded in generating real recommendations in every case tested (4/4, including the zero-transaction case).
- **Severity:** Critical
- **Impact:** The `lender_recommendation` section of the customer/lender-facing PDF brief — the one AI-generated narrative element specific to the lender-brief endpoint — has never once produced real content in this environment; it silently degrades to an empty list with no error surfaced to the caller (`success: true` in every response), so a consumer of this endpoint would have no way to know the AI recommendation step failed rather than legitimately having nothing to say.
- **Root cause:** `bank_lender_brief.py` calls `generate_recommendations("bank", context, timeout=8.0)` (`LENDER_RECOMMENDATION_TIMEOUT_SECONDS = 8.0`). `generate_text()` (`app/services/ai_client.py`) applies the `timeout` parameter as the **per-attempt** `httpx.AsyncClient` timeout inside its own internal 3-attempt retry loop, not as a total call budget. `recommendation_generation.py`'s own docstring states this value is meant for a caller "which must complete within 10 seconds total," but passing `8.0` as a per-attempt timeout to a 3-retry loop (with 1s/2s linear backoff between attempts) means the real worst-case time-to-failure is up to ~27 seconds — nearly three times the intended total budget — and, more importantly, every individual 8-second attempt is confirmed too short for this "bank" prompt's real Gemini response time in this environment (the identical prompt template succeeds reliably within the sibling endpoint's default 30-second timeout, 4/4 times). The result is not occasional flakiness but a deterministic, 100%-reproducible failure given this model/environment/prompt-size combination.
- **Suggested fix:** Treat `timeout` as a total call budget (e.g. track elapsed time across attempts and stop retrying once the budget is exhausted, rather than granting a fresh full timeout per attempt), and/or raise `LENDER_RECOMMENDATION_TIMEOUT_SECONDS` to a value empirically confirmed sufficient for a single real Gemini round-trip with this prompt's typical payload size (30s, matching the sibling endpoint's default, would likely resolve it outright).
- **Blocks Prompt 7:** No — the rest of the lender-brief response (all non-AI-generated sections) is correct and independently verified; only the `lender_recommendation` field is affected.

### Issue B6-2: `revenue_at_stake` (a required `AIRecommendation` field) is fabricated with no traceable basis whenever the account's real data offers no natural anchor value
- **Description:** For accounts/calls with rich, high-volume transaction data (wallet account, 6/8 recommendations; several of the primary account's recommendations), the AI reliably reuses an exact real dollar figure already present in its context data for `revenue_at_stake`. But for the savings account (all 5/5 recommendations: 4000.0, 3500.0, 7500.0, 1000.0, 500.0) and the fully-empty sparse-data test (both recommendations: 50000.0, 25000.0), every `revenue_at_stake` value is a round, plausible-looking number with no match anywhere in the real context data supplied to the model.
- **Severity:** Medium
- **Impact:** `revenue_at_stake` cannot be trusted as an authoritative, data-derived figure across the board — it is sometimes real and sometimes invented outright, with no way for a consuming client to distinguish the two cases from the response alone.
- **Root cause:** `_PROMPT_TEMPLATE` (`app/services/recommendation_generation.py`) asks the model for "a number representing the revenue impact" with no defined methodology; when no natural anchor value exists in the supplied context (sparse/degraded accounts), the model fabricates a plausible one rather than, e.g., returning 0 or omitting the recommendation.
- **Suggested fix:** Either define an explicit, code-computed methodology for `revenue_at_stake` (passed into the prompt as a suggested value per finding) rather than asking the LLM to invent it, or clearly document/flag this field as an LLM estimate rather than a verified figure (as the neighboring `estimated_debt_coverage_indicator.methodology_note` field already does for a different metric).
- **Blocks Prompt 7:** No.

### Issue B6-3: `created_at` (a required `AIRecommendation` field) is never grounded to the actual generation time
- **Description:** Across all 18 real Gemini-generated recommendations read (5 primary + 5 savings + 8 wallet) plus the 2 from the sparse-data test, every `created_at` value is a plausible-looking but fabricated past timestamp (e.g. `"2023-10-27T10:00:00Z"`, recurring identically across multiple unrelated calls including the fully-empty sparse test; `"2024-07-30T10:00:00Z"` for the savings account) — none match the actual test-execution date (2026-07-10) or anything derivable from the request.
- **Severity:** Low
- **Impact:** All values are valid ISO 8601 timestamps (so schema validation passes), but none can be trusted as "when this recommendation was actually generated" — currently no code path reads or relies on this field, so there is no active consequence today, but it's a latent trust gap.
- **Root cause:** `_PROMPT_TEMPLATE` never supplies the model with the actual current date/time, so the model has no way to produce a correct value and defaults to a plausible placeholder.
- **Suggested fix:** Have the caller (`generate_recommendations` or its callers) overwrite/set `created_at` to the real current timestamp server-side after parsing, rather than trusting the LLM to supply it.
- **Blocks Prompt 7:** No.

### Issue B6-4: The lender-brief endpoint has no `disabled_features`/insufficient-data signaling at any level, compounding B5-2's inflated zero-transaction score
- **Description:** Unlike its sibling `financial-health-playbook` (which returns a `(data, disabled_features)` tuple, correctly wired by its route handler into `meta.disabled_features`, and confirmed via the sparse-data test to populate an `income_stability` entry for a zero-transaction account), `get_lender_brief_response` returns only a plain `dict`, and its route handler (`app/routes/bank.py`, `/ai/lender-brief`) calls `success_response(data, analysis_run_id=analysis_run_id)` with no `disabled_features` argument at all — confirmed by direct code inspection and by all 4 tested calls (3 real accounts + 1 sparse) uniformly returning `meta.disabled_features: []` regardless of data volume. For a zero-transaction account, this means the lender-brief shows `loan_readiness_score: 100`, `creditworthiness_tier: "A"` (per pre-existing B5-2) with no top-level warning anywhere in the response — the only signals are buried in `sections.loan_readiness_assessment.score_breakdown.disabled_components` and a plain-text footnote ("Based on 0 transactions...").
- **Severity:** Medium
- **Impact:** Compounds B5-2's risk by presenting the inflated perfect score in the most prominent, human-readable, decision-facing document in the Bank vertical, with the least guardrail messaging of any endpoint tested in Prompts 3–6. Notably, in the same sparse-data test, the sibling `financial-health-playbook` endpoint's own Gemini-generated recommendation (`REC-002-SCORE-CLARITY`) independently and correctly flagged this exact same risk in its `reasoning` text ("the high loan readiness score is potentially misleading... derived exclusively from a low fraud risk score") — showing the model recognizes the issue when given the chance, but the lender-brief endpoint's document structure carries no equivalent warning.
- **Root cause:** `get_lender_brief_response`/its route handler were never built with a `disabled_features` return path, unlike the financial-health-playbook endpoint built alongside it.
- **Suggested fix:** Add the same `disabled_features` mechanism to the lender-brief response (e.g. surfacing an entry when `transactions_analyzed` is below a minimum threshold, or when `loan_readiness_assessment.disabled_components` is non-empty).
- **Blocks Prompt 7:** No.

### AI response schema validation — confirmed PASS
- **Description:** All 18 real recommendations (5 primary + 5 savings + 8 wallet, financial-health-playbook only, since lender-brief's own recommendations never generated — B6-1) plus the 2 from the sparse-data test were checked field-by-field against `AIRecommendation` (`app/schemas/recommendation.py`): `entity_type` is always the valid literal `"account"`; `urgency` is always one of the 3 valid literals; `confidence_score` is always within `[0.0, 1.0]`; all string fields are non-empty; `created_at` is always a valid (if ungrounded — see B6-3) ISO 8601 timestamp. No recommendation would be dropped by `parse_recommendations()`'s validation step.
- **Severity:** N/A (confirms correct behavior, not a defect)
- **Blocks Prompt 7:** No.

### Response envelope — confirmed PASS
- **Description:** All 6 live endpoint calls (3 accounts × 2 endpoints) returned the standard `{success, data, meta: {missing_fields, disabled_features, analysis_run_id}}` envelope with no deviation. `financial-health-playbook`'s route correctly forwards its service function's `disabled_features` return value into `meta.disabled_features` (confirmed via code inspection at `app/routes/bank.py:318-320`; not exercised by the 3 live accounts tested since all had sufficient data, but confirmed functionally correct via the sparse-data test). `lender-brief`'s route never forwards any `disabled_features` at all (see B6-4).
- **Severity:** N/A (confirms correct behavior aside from the gap noted in B6-4)
- **Blocks Prompt 7:** No.
