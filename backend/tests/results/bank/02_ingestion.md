# Bank Test Prompt 2 — Ingestion Testing (Consolidated)

**Date:** 2026-07-08
**Mode:** non-isolated — run against the project's real, current dev DB (`backend/app.db`), no fresh/isolated test DB created, no wipe/reset performed.
**Prerequisite:** Bank Test Prompt 1 — all three datasets PASS or PASS WITH ISSUES (confirmed, see `testing/bank/dataset_0*/01_dataset_inspection.md`).

## Datasets ingested (real ingestion path: `ingest_bank_csv` → `_ingest_bank_csv_async` → `ingest_bank_dataframe`)

| Dataset | Input rows | Inserted | Rejected | Balance integrity |
|---|---|---|---|---|
| `scanwick_test_bank_statement.csv` | 465 | 465 | 0 | PASSED (discrepancy: none) |
| `scanwick_bank_savings_clean.csv` | 1,670 | 1,670 | 0 | **FAILED** (discrepancy: 32.76) |
| `scanwick_bank_wallet_clean.csv` | 8,158 | 8,158 | 0 | **FAILED** (discrepancy: 800,624.14 — largest of the three) |

Zero rows rejected across all three datasets in every case.

## Pre-existing DB state / non-isolation note

`app.db` had 0 rows in `accounts`/`bank_transactions`/`uploads` at the very start of this task (confirmed directly). Partway through this task, an initial ingestion attempt crashed because `app.db`'s Alembic version was behind the current migration head (missing the `uploads.analyzer_metadata` column added in a prior session) — `ingest_bank_dataframe` had already committed the `Account` + all `BankTransaction` rows for `scanwick_test_bank_statement.csv` before crashing on the final `Upload` write, leaving an orphaned account+465 rows. `app.db` was brought to head (`alembic upgrade head` — additive-only, zero data loss since all Bank tables were empty beforehand) and the run was repeated cleanly. This orphaned data is documented per-dataset in `testing/bank/dataset_01_.../02_result.json`'s `db_state_before_run` field rather than hidden or silently cleaned up, per this run's non-isolated/no-reset instruction.

## Required checks — cross-cutting results

### `is_own_account_transfer`
`detect_own_account_transfers()` (`app/services/bank_account_integrity.py`) is **not called anywhere in the real ingestion path** — confirmed by searching the entire codebase; its only callers are its own unit tests. `is_own_account_transfer` stays `False` on every ingested row unless this function is invoked manually. Invoked it directly for this test: found 1,197 matched pairs (2,394 flagged rows) across the 4 accounts present at check time. **This number is contaminated** by the accidental orphaned duplicate of the primary file described above — two near-identical copies of the same file's transactions will trivially "match" each other — so it should not be read as a genuine measurement of real cross-account transfer detection. The underlying pairing logic does demonstrably run and produce output; a clean re-measurement would need an environment without the accidental duplicate.

### `is_anomalous`
Created a real `ContextualMarker` (bank, 2025-06-05 to 2025-06-15) via `create_contextual_marker()`. Result: 208 transactions fell inside that range, 208 were flagged `is_anomalous=True`, and **0** were flagged `True` outside the range. Exact match, no false positives — this check is clean and trustworthy.

### Currency conversion
All three files default `original_currency` to `"NGN"` (none has a currency column); `base_currency` also defaults to `NGN` (no `MerchantSettings` row exists for this test user), so every conversion hit the same-currency short-circuit (`exchange_rate=1.000000`, `base_currency_amount == amount`). The mechanism runs correctly, but **none of the three datasets meaningfully exercises real cross-currency conversion** — stated explicitly per the QA script's instruction, not glossed over.

### `account_number_hash`
Confirmed hashed (SHA-256 via `hash_value`) in every case, never plaintext. None of the three files has an account-number column, so every ingestion falls back to `hash_value(f"unknown-account:{upload_id}")` — meaning the hash is derived from the **upload ID**, not the real account. Consequence, confirmed directly: the three copies of `scanwick_test_bank_statement.csv` ingested in this run produced three **different** `account_number_hash` values. The system currently cannot recognize "this is the same real bank account being re-uploaded" for any of these three files.

### Duplicate-ingestion behavior
Re-ran `scanwick_test_bank_statement.csv` a second time (intentional, per this prompt's requirement). Result: a brand-new `Account` row + a full new set of 465 `BankTransaction` rows, with **zero deduplication**. Confirmed by code inspection: no unique constraints on `account_number_hash` or any transaction-identity field in the `accounts`/`bank_transactions` migrations, and no dedup-check logic anywhere in `ingest_bank_dataframe`/`write_canonical_bank_rows`. By the end of this run, **three** total copies of this file's data existed in `app.db` (one accidental orphan, one fresh first-pass run, one intentional duplicate-test run) — none rejected, none merged. This is a genuine, confirmed gap, not inferred from reading code alone.

The other two datasets were not independently re-run for this specific check (only the primary file was, per the test design) — the same behavior is expected there based on code inspection but was not separately re-observed.

## Prompt 1 follow-up issues carried forward

- **Dataset 01** (primary): ambiguous debit+credit row (row 158) — not specifically re-checked at the ingestion level in this pass; would need a targeted row-level query to confirm its final signed amount.
- **Dataset 02** (savings): Prompt 1 flagged the first-row null balance as a precision concern — **confirmed to actually cause a failed integrity check** (discrepancy 32.76), not just reduced precision.
- **Dataset 03** (wallet): Prompt 1 rated this the cleanest file (0 null balances) — **real ingestion shows the opposite on integrity** (largest discrepancy of the three, 800,624.14). This is the single most important finding of this Prompt 2 pass: data completeness and data correctness are not the same thing, and only real ingestion — not static inspection — revealed this.

## Overall verdict

**PASS WITH ISSUES**, all three datasets. Ingestion mechanics (parsing, row counts, hashing, currency defaults, anomaly flagging) all work correctly on real data. Two architectural gaps were found that are not specific to any one dataset: `is_own_account_transfer` is not wired into the automatic ingestion path, and there is no duplicate-ingestion protection at all. Bank Test Prompt 3 (Dashboard Endpoint Testing) can proceed on this data, with the balance-integrity failures on datasets 02/03 and the un-flagged transfer/duplicate rows kept in mind when interpreting dashboard totals.
