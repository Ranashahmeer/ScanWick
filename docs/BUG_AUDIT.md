# Scanwick — Full-System Bug Audit

**Date:** 2026-07-21
**Branch audited:** `integration/frontend-backend`
**Scope:** entire backend (`backend/app`, ~14,400 lines of Python/FastAPI) and entire frontend (`frontend/src`, ~16,000 lines of React/TypeScript), read in full file-by-file, not sampled.

**Method:** nine parallel deep-read audits, each covering a coherent subsystem, cross-referenced against the actual current code (not the integration log's history) so every finding below reflects what the code does *today*. Where a finding matches something the integration log says was already fixed, that's noted explicitly — those are not re-reported unless a real unfixed remnant was found.

Every finding includes a file:line location and a concrete failure scenario. Items marked **(unconfirmed)** are flagged by the auditing agent as plausible but not fully verified as reachable — included for visibility, not because they cross-checked to certainty like everything else here.

---

## Summary

| Area | Critical | Major | Minor |
|---|---|---|---|
| Backend — Auth/Security/Core | 3 | 2 | 5 |
| Backend — Ingestion/Uploads | 2 | 3 | 4 |
| Backend — Bank vertical | 1 | 4 | 3 |
| Backend — Ecommerce vertical | 0 | 3 | 3 |
| Backend — Sales/Reconciliation | 1 | 2 | 1 |
| Frontend — Auth/Routing/Lib | 2 | 3 | 4 |
| Frontend — Dashboard/Commerce | 0 | 3 | 3 |
| Frontend — Sales/Reconciliation/Upload | 1 | 4 | 2 |
| Frontend — Shared/Account/Misc | 1 | 3 | 2 |
| **Total** | **11** | **27** | **27** |

The single highest-impact theme across the whole audit: **several features that look complete and are exercised in tests are never actually wired into the live request path** — an own-account-transfer detector that's never called, an `UploadStatus.failed` value that's never set, a Celery worker/API split that doesn't share a filesystem in the given deployment topology, an `exclusion_detail` field that's never populated, and a `/playground` route that imports the wrong (fake-data) component. None of these throw an error anywhere — they all fail silently, which is why they survived this long.

---

## Backend — Auth, Security & Core Infrastructure

Files read: `main.py`, `config.py`, `database.py`, `dependencies.py`, `celery_app.py`, `tasks.py`, `routes/auth.py`, `models/auth.py`, `models/user_merchant_roles.py`, `models/accounts.py`, `schemas/auth.py`, `schemas/envelope.py`, `utils/security.py`, `utils/otp.py`, `utils/email.py`, `services/rbac.py`, `services/entitlements.py`, `services/merchant_provisioning.py`, `services/encryption.py`.

### Critical

1. **OTP codes and password-reset links are unconditionally printed to server logs, in every environment.** `backend/app/utils/email.py:43,57,72`. `send_otp_email`, `send_login_otp_email`, and `send_password_reset_email` each `print(...)` the raw OTP or reset link *before* checking whether Resend is configured or whether the email actually sends. In production, with real email delivery working fine, every OTP and reset token still lands in stdout/log storage. Anyone with log access (a log drain, a cloud logging bucket, a misconfigured aggregator) can read live OTP codes or reset links and fully bypass registration/login/password-reset without touching email.

2. **`POST /api/auth/register` lets an attacker overwrite an unverified victim's password — account takeover.** `backend/app/routes/auth.py:96-130`, overwrite branch at 107-110. If a user registers but hasn't yet entered their OTP, an attacker who knows only the victim's email can call `/register` again with the same email and their own password; because `existing.is_verified` is still `False`, the 409 "already registered" guard doesn't trigger, and `hashed_password`/name fields are silently overwritten. The victim still verifies successfully (their own OTP still arrives) and logs in normally — with the attacker's password now active. Compounding: `google_callback` (lines 387-395) sets `is_verified=True` on Google sign-in for the same email but never touches `hashed_password`, so the attacker-planted password keeps working indefinitely even after the victim switches to "Sign in with Google."

3. **`dev_mode` defaults to `True` and silently controls both database selection and SQL-echo logging.** `backend/app/config.py:17`, `backend/app/database.py:14,22`. If a production deploy forgets to set `DEV_MODE=false` (or the env var name/casing doesn't match what's expected), the app routes all traffic to local SQLite (`./app.db`) instead of the configured `DATABASE_URL`, and sets `echo=True` on the engine — logging every SQL statement including bound parameters (OTP codes, refresh/reset tokens, encrypted-field ciphertexts).

### Major

4. **`ensure_merchant_provisioned` has a check-then-act race that can split one user across two `merchant_id`s.** `backend/app/services/merchant_provisioning.py:32-60`. No locking, no `SELECT ... FOR UPDATE`, and the unique constraint is `(user_id, merchant_id, vertical)` — not `user_id` alone. Two concurrent first-provisioning calls for the same brand-new user (e.g. two browser tabs polling `/me` right after verification) can both see zero existing roles, both generate a different UUID, and both commit — leaving the user with 6 role rows split across 2 merchant_ids. Later code reading `existing_roles[0].merchant_id` with no `ORDER BY` then picks one nondeterministically per request. Same bug class as the "partial role coverage" issue fixed in the most recent commit, but on the concurrency axis, which that fix didn't address.

5. **`/api/auth/resend-otp` breaks its own anti-enumeration guarantee.** `backend/app/routes/auth.py:158-181`. The code comments that responses should be identical to avoid revealing whether an email is registered, but the unknown-email branch (line 165, *"If that email is registered, a new code has been sent."*) and the known-email branch (line 181, *"A new code has been sent to your email."*) return different literal text — a direct account-enumeration oracle, in contrast to `forgot_password`'s matching messages (lines 257-258, 276) which get this right.

### Minor

6. **Fernet encryption key defaults to a value committed in source, with no runtime enforcement against using it in production.** `backend/app/config.py:65-71`, `backend/app/services/encryption.py:20`. If `FERNET_KEY` is simply omitted from a prod `.env`, the app starts fine and encrypts sensitive fields with a key anyone reading the source already knows.

7. **Google OAuth CSRF `state` is stored in an in-process Python dict, not persisted.** `backend/app/routes/auth.py:46-56,311-312,347`. Any deployment with more than one worker process/replica will intermittently fail legitimate Google logins whenever `/google` and `/google/callback` land on different processes — same "in-memory state that should be shared" class of bug as the already-fixed refresh-token rotation issue.

8. **`verify-otp` with `purpose="login"` issues full tokens with no password check, reachable via the unauthenticated `/resend-otp`.** `backend/app/routes/auth.py:135-181`. The normal `login()` endpoint never exercises this path, and `LoginPendingResponse` is never returned by anything — this looks like leftover/parallel infrastructure rather than an intended passwordless-login feature. Exploitability requires reading the victim's inbox, but as built, anyone who can read/guess a login OTP gets a full session with zero password check.

9. **OTP brute-force protection is only a per-IP rate limiter (10 req/60s), not per-account.** `backend/app/utils/otp.py:12-14`, `backend/app/main.py:41-68`. A 6-digit code (~900k possibilities) with no per-email attempt counter means an attacker spreading guesses across IPs is unthrottled.

10. **CORS allow-list includes localhost origins unconditionally in every environment.** `backend/app/main.py:30-35`. Low exploitability given Bearer-token auth rather than cookies, but an unnecessary trust-boundary widening in production.

11. **`/api/internal/ping-task` has no authentication.** `backend/app/routes/internal.py:12-22`. Anyone can enqueue a Celery task and block a threadpool worker for up to 10s — minor unauthenticated resource-consumption vector, same class as the already-fixed unauthenticated quality-report endpoint. Worth confirming whether this was intentionally left open for health checks.

Also noted, lower severity: `google_callback` has no error handling around an email-collision commit (would 500 with an unhandled `IntegrityError` instead of a clean error) and `Account.user_id` has no FK constraint to `users.id` (documented in the model's own docstring as a known gap).

---

## Backend — Ingestion & Uploads

Files read: `routes/uploads.py`, `routes/internal.py`, `routes/analyze.py`, `services/upload_staging.py`, `services/storage.py`, `services/bank_ingestion.py`, `services/bank_pdf_ingestion.py`, `services/mono_client.py`, `services/mono_ingestion.py`, `services/ecommerce_ingestion.py`, `services/ecommerce_olist_adapter.py`, `services/sales_ingestion.py`, `services/sales_quality.py`, `utils/analyzer.py`, `models/uploads.py`, plus `backend/docker-compose.yml` / `backend/Dockerfile`.

### Critical

12. **The Celery worker and API process don't share the upload staging directory in the given deployment topology — file-based ingestion is unreachable.** `backend/docker-compose.yml` defines `celery-worker`, `redis`, `minio` but no API service and no shared volume for `/tmp/scanwick_uploads`; the API runs via `npm run dev` → `uvicorn` directly on the host. `upload_staging.py:5` and `bank_pdf_ingestion.py:94` hard-code `/tmp/scanwick_uploads` with no shared-storage abstraction (the existing `storage.py` abstraction isn't used here). Result: the API stages a file on the host filesystem, dispatches a Celery task, and that task runs inside the `celery-worker` container's own isolated filesystem where the file was never written — every `POST /api/v1/upload/csv` / `POST /api/v1/bank/upload/pdf` in this topology fails with `FileNotFoundError` inside the worker, invisibly to the caller (see next finding).

13. **`UploadStatus.failed` is never set anywhere in the codebase (verified via repo-wide grep) — every ingestion failure leaves the Upload stuck in "processing" forever.** `services/bank_ingestion.py:390-400`, `bank_pdf_ingestion.py:97-105`, `ecommerce_ingestion.py:439-483`, `sales_ingestion.py:359-367` have no try/except that writes back a failure status. Any exception — the deployment issue above, a corrupt/empty/non-UTF-8 CSV (no `encoding=` is ever passed to `pd.read_csv`, so a Windows-1252 export raises `UnicodeDecodeError`), a malformed PDF, a transient DB error — fails the Celery task silently. `GET /upload/{id}/quality-report` then polls a permanently-`processing` row with null fields, forever.

### Major

14. **No idempotency/dedup on re-ingestion — re-uploading the same file double-counts financial/pipeline data.** None of the three write paths check for an existing record first: `ingest_bank_dataframe` (`bank_ingestion.py:331-346`) always creates a new `Account` with a fresh UUID even if one with the same `account_number_hash` exists; `write_canonical_rows` (`ecommerce_ingestion.py:263-374`) always inserts a new `Order`/`OrderItem` despite carrying `external_order_id`; `write_canonical_deal_rows` (`sales_ingestion.py:283-331`) always inserts a new `Deal` despite carrying `external_deal_id`. No unique constraints back this up at the DB layer either. A routine "did that upload work? let me try again" retry silently doubles revenue/pipeline/cashflow figures.

15. **Dispatch-after-commit with no compensation on broker failure.** `routes/uploads.py:202-210`, `routes/bank.py:485-488`. The `Upload` row is committed as `processing` *before* `ingest_*.delay(...)` is called, uncaught. If Redis is down at that instant, the request 500s but the row and staged file are already orphaned in "processing" permanently.

16. **Staged files are never cleaned up.** Repo-wide grep for `unlink`/`os.remove`/`shutil.rmtree` under `app/` returns nothing — every staged CSV/PDF is left on disk forever regardless of outcome, an unbounded resource leak (worse if `/tmp` is a small tmpfs in production).

### Minor

17. Weak content-type gate (`routes/uploads.py:165-171`, `routes/analyze.py:93-99`) accepts any file whose client-controlled `Content-Type` is `application/octet-stream` regardless of real content, deferring rejection to deep inside the Celery task (feeding finding #13).
18. No explicit CSV encoding handling in the Celery ingestion paths (only `/api/analyze` catches `UnicodeDecodeError` and returns 422).
19. Per-row synchronous exchange-rate DB queries inside `for row in df.iterrows()` loops (`bank_ingestion.py`, `ecommerce_ingestion.py`, `sales_ingestion.py`) mean a large multi-currency file drives one DB round-trip per row serially — can make a big upload "hang" for a very long time with no progress signal.
20. Unbounded PDF rasterization cost: `render_pdf_to_images` (`bank_pdf_ingestion.py:28-40`) rasterizes every page at 200 DPI with no cap on page count/dimensions beyond the 15MB size limit **(unconfirmed exploitability)**.

Verified NOT bugs: Mono ingestion's inability to produce a durable Upload row is a documented, non-silent limitation, not an oversight. RBAC scoping constants across the three upload routes are consistent with each other despite a confusingly shared constant name (`PAUSE_ROLES` reused for Olist ingest — same actual role set, not a scoping bug).

---

## Backend — Bank / Finance Vertical

Files read: `routes/bank.py`, `services/bank_abm.py`, `bank_account_integrity.py`, `bank_cashflow.py`, `bank_cashflow_analysis.py`, `bank_cashflow_forecast.py`, `bank_customer_segmentation.py`, `bank_dashboard.py`, `bank_fraud_risk.py`, `bank_income_stability.py`, `bank_lender_brief.py`, `bank_loan_readiness.py`, `bank_playbook.py`, `bank_revenue_patterns.py`, `bank_transaction_classification.py`, `models/bank_transactions.py`, `bank_account_identifiers.py`, `exchange_rates.py` (model + service), `merchant_currency.py`.

### Critical

21. **`is_own_account_transfer` is never actually set by any real ingestion path — the "don't double-count transfers between a merchant's own accounts" guarantee is currently a no-op in production.** `services/bank_account_integrity.py:88-141` is the only code that ever sets this flag, and it is never called from any route, Celery task, or beat schedule (verified by repo-wide grep). Every place that filters on this column (`eligible_transactions` in `bank_cashflow.py:16-23`, feeding the dashboard, cashflow analysis, fraud risk, loan readiness, forecast, lender brief, income stability, ABM, revenue patterns, and customer segmentation) is filtering against a column that's always `False` in practice. Concrete scenario: a merchant moves ₦3M from their own current account to their own savings account — every headline metric counts it as genuine revenue *and* genuine expense. This is a routine scenario, not an edge case, and it corroborates an independent finding already on record in `backend/tests/results/bank/03_dashboard.md`.

### Major

22. **`compute_cashflow_forecast` has no minimum-data guard and silently forecasts from a fabricated ₦0 balance when `balance_after` data is missing.** `services/bank_cashflow_forecast.py:97-137`, route `routes/bank.py:332-347`. Unlike sibling services, this one never returns `None`/disabled-features; if daily closing balances can't be computed, `current_balance` defaults to `Decimal("0")` instead of falling back to `account.closing_balance` (the way `bank_cashflow_analysis.py:22` does), and the route never surfaces `disabled_features` to the caller. Result: a full 90-day projected-balance curve with 80%-confidence bands, starting from ₦0 instead of the account's real balance, shown with the same confidence as a well-supported forecast — in a lender-facing report.

23. **Mono-ingested transactions always get `original_currency = "NGN"` regardless of the account's real currency.** `services/mono_ingestion.py:28-49`, `services/bank_ingestion.py:107-144` (line 137 defaults to `"NGN"` when no currency column is found). A Ghana- or Kenya-linked Mono account has every transaction's currency stored and *displayed* as NGN — `bank_fraud_risk.py` prints `original_currency` directly into fraud-flag descriptions and lender briefs, so a real GHS 50,000 transaction shows up labeled "NGN 50,000.00" in a document used for actual lending decisions.

24. **`base_currency_amount`/`exchange_rate` are computed at ingestion time but never read by any analytics service.** Computed in `bank_ingestion.py:278-290`; confirmed absent from every read-path service (`bank_dashboard.py`, `bank_cashflow*.py`, `bank_fraud_risk.py`, `bank_loan_readiness.py`, `bank_income_stability.py`, `bank_revenue_patterns.py`, `bank_customer_segmentation.py`, `bank_abm.py`, `bank_lender_brief.py`). Currently latent for single-currency statements, but any mixed-currency row (a USD fee on an NGN account, which ingestion explicitly anticipates via `_CURRENCY_KEYWORDS`) gets its raw foreign-currency amount summed directly into NGN totals with no conversion.

25. **`_statement_integrity`'s sequential-ordering check depends on unspecified same-day row order.** `services/bank_fraud_risk.py:190-215`, query at `routes/bank.py:139-149` has no `ORDER BY` and there's no time-of-day column on transactions. For any statement with multiple same-day transactions (the normal case), the balance-continuity check can compare rows in the wrong order purely due to incidental DB fetch order, producing a false "failed" integrity signal (or masking a real one) on a statement that actually reconciles fine.

### Minor

26. Duplicate-payee fraud flag (`bank_fraud_risk.py:103-135`) groups both credits and debits together but always labels matches "possible duplicate or double-charge" — two legitimate same-day incoming payments from the same customer get flagged with language meant for outgoing duplicate charges, feeding directly into the fraud-risk subscore.
27. Fraud-risk is recomputed redundantly on every loan-readiness, lender-brief, and playbook call (`bank_loan_readiness.py:238`, `bank_lender_brief.py:43`) — not incorrect, but avoidable O(n²)-ish work run at least twice per request on large statements.
28. O(n²) nested loops in `detect_own_account_transfers` and `_detect_timing_anomalies` — a documented limitation, but a real scaling risk on large multi-year statements, compounded by #27.

Verified NOT a bug: the "Placeholder until real auth/RBAC derives this from the session" comment on every `bank.py` account-scoped endpoint is stale/misleading text, not a live IDOR — `check_role` is actually invoked against the account's real owning merchant on every route, confirmed by reading `rbac.py`. Worth cleaning up the comment since it could mislead a future engineer.

---

## Backend — Ecommerce / Commerce Intelligence Vertical

Files read: `routes/ecommerce.py`, `services/ecommerce_ad_kill_switch.py`, `ecommerce_churn.py`, `ecommerce_dashboard.py`, `ecommerce_diagnostics.py`, `ecommerce_holt_winters.py`, `ecommerce_inventory_forecast.py`, `ecommerce_margins.py`, `ecommerce_order_items.py`, `ecommerce_playbook.py`, `ecommerce_returns.py`, `ecommerce_revenue.py`, `ecommerce_rfm.py`, `ecommerce_rfm_endpoint.py`, `ecommerce_sku_matrix.py`, `models/order_items.py`, `orders.py`, `returns.py`, `sku_inventory.py`, `rfm_segment_assignments.py`, `ad_kill_audit_log.py`.

No IDOR was found anywhere in this vertical — merchant-scoping via `check_role`/`get_merchant_role` is applied correctly and consistently before every data access. Null/empty-dataset handling (zero orders, customers, SKUs) is also consistently guarded.

### Major

29. **The ad kill switch silently treats missing net-margin data as break-even, which can suppress a real auto-pause.** `services/ecommerce_ad_kill_switch.py:122-127`: `bucket["net_margin"] += order.net_margin or Decimal("0")`. `Order.net_margin` is legitimately null whenever COGS is unknown, and every sibling diagnostic (profit-leaks, sku-matrix) explicitly gates on COGS coverage before trusting margin data — the auto-evaluator doesn't. A channel whose orders mostly lack COGS gets counted as $0 margin instead of excluded/flagged, which can pull a genuinely lossy channel's summed margin up to ≥0 and prevent the auto-pause from ever firing — a false negative on a feature whose entire job is catching real financial loss and taking automated action.

30. **No exception handling around the Holt-Winters fit/forecast path — one bad SKU can 500 the whole merchant's request.** `services/ecommerce_holt_winters.py:87-118`, `ecommerce_margins.py:56`. `MIN_WEEKS_OF_HISTORY=8` is chosen to be exactly `2 × SEASONAL_PERIODS` — the bare minimum statsmodels needs for a seasonal fit — so any SKU that just barely clears the minimum, or has a degenerate/low-variance series, risks an unhandled optimizer exception taking down `/predictive/inventory-forecast` and `/ai/playbook` for the entire merchant, rather than being cleanly excluded like the already-handled insufficient-history case.

31. **`is_stale` measures upload recency, not order recency, despite the code's own comment quoting a different rule.** `services/ecommerce_dashboard.py:49-69`. The comment cites "last order > 24h ago → show Stale Data alert" but the implementation checks `Upload.created_at`, not `max(Order.order_date)`. For CSV-ingested merchants (the only ingestion path), re-uploading a file whose most recent order is months old immediately reports `is_stale: false`. Confirmed intentional and covered by an existing test, but it doesn't do what its own comment says.

### Minor

32. TOCTOU race in `get_or_create_merchant_settings` (`ecommerce_ad_kill_switch.py:14-26`) against a DB unique constraint on `merchant_id` — two concurrent first-time calls for the same never-configured merchant both read `None` and both try to insert; the second raises an unhandled `IntegrityError` → 500.
33. `threshold_days` has no `gt=0` validation (`routes/ecommerce.py:51-53`) — a zero/negative value makes the kill-switch's date-range query match nothing, silently going inert with no error surfaced to the admin who misconfigured it.
34. `SEASONAL_PERIODS=4` appears reverse-engineered from the minimum-history constant rather than derived from real weekly-retail seasonality **(unconfirmed — a modeling concern more than a code defect)**.

Also noted as a latent (not currently exploitable) risk: profit-leak cost attribution assumes exactly one `order_item` per `order`, an invariant currently upheld everywhere (including the Olist adapter, which deliberately splits multi-item orders to preserve it) but with no DB constraint enforcing it going forward.

---

## Backend — Sales Intelligence & Reconciliation

Files read: `routes/sales.py`, `routes/reconciliation.py`, `services/sales_deals.py`, `sales_forecast.py`, `sales_notifications.py`, `sales_pipeline.py`, `sales_playbook.py`, `sales_postmortem.py`, `sales_rbac_scoping.py`, `sales_rep_leaderboard.py`, `sales_rep_trajectory.py`, `sales_slippage.py`, `sales_stage_timing.py`, `sales_stage_velocity.py`, `sales_stagnation.py`, `sales_win_dna.py`, `sales_win_probability.py`, `services/reconciliation.py`, `recommendation_generation.py`, `ai_client.py`, `contextual_markers.py`, plus related models/schemas.

### Critical

35. **`/api/v1/sales/ai/playbook` fails open for a misconfigured sales rep, leaking the entire merchant's data to that rep.** `routes/sales.py:310` computes `scope_to_rep_id = role_row.rep_id if _is_rep(role_row) else None`, and `sales_playbook.py:36` only scopes `if scope_to_rep_id is not None`. The codebase explicitly documents (`user_merchant_roles.py:50-53`, `sales_rbac_scoping.py:22-24`) that a `sales_rep` role with no linked `rep_id` must "fail closed, not open" — but this specific route collapses "misconfigured rep" and "not a rep at all" into the same `None`, skipping the scoping guard entirely. Every sibling endpoint (stage-velocity, stagnation, forecast, slippage, rep-trajectory) instead fails closed to `[]` on `None` via `scope_items_to_rep`/`scope_reps_list_to_rep_id` — only the playbook route reimplements the check itself and gets it backwards. A sales rep whose role row lacks a `rep_id` (a documented possible provisioning gap) gets full cross-rep intelligence via the AI playbook instead of nothing.

### Major

36. **`/predictive/forecast` leaks a merchant-wide aggregate deal count to a scoped sales rep, contradicting the code's own stated anti-inference design.** `services/sales_forecast.py:85-90` sets `confidence_factors["open_deals_scored"]` to the total open-deal count across the *whole merchant*, computed before rep-scoping; `routes/sales.py:194-202` only overwrites `deal_forecasts`/`forecast_total` for a scoped rep, leaving `open_deals_scored` untouched. `sales_rbac_scoping.py:43-48`'s own docstring explains `forecast_total` is recomputed specifically to prevent a rep inferring peers' collective forecast — `open_deals_scored` provides the same inference vector (rep's own scoped count vs. merchant total) and was missed.

37. **Every sales analyzer silently drops anomalous/excluded deals without ever reporting them as excluded.** Every sales query filters `Deal.is_anomalous.is_(False)` (pipeline, forecast, rep-leaderboard, rep-trajectory, win-DNA, win-probability, postmortem, stage-timing), but not one of the corresponding `record_analysis_run(...)` calls ever passes `records_excluded`/`exclusion_detail`/`contextual_markers_applied` — they all default to `0`/`[]`. The `ReconciliationReport` model exists specifically to surface this kind of exclusion to users, but for the entire Sales vertical it is structurally impossible for a merchant to ever learn that a contextual marker (e.g. a flagged fraud/promo period) silently removed deals from their pipeline, forecast, leaderboard, win-DNA, or postmortem numbers. This is the pervasive, vertical-wide version of the silent-exclusion pattern also found in the frontend reconciliation UI (see finding #43).

### Minor

38. `sales_win_dna.py`'s `_ranked_breakdown()` (lines 21-39) computes `pct_of_won_deals` against only the deals with a non-null value for that dimension (e.g. known acquisition channel), not the true total won-deal count — mislabeled and will overstate each channel's share whenever some won deals have a null channel/rep.

Also flagged as a real-but-unconfirmed-impact vector: free-text CRM fields (e.g. `Deal.stage`, ingested directly from CSV) flow unescaped (beyond JSON encoding) into the Gemini recommendation prompt — actual impact is limited because `parse_recommendations()` strictly validates every returned recommendation against a schema and drops invalid ones, but the injection surface itself is real.

Verified NOT bugs: RBAC/merchant-scoping is otherwise consistent and correct across every other `sales.py` endpoint; timezone handling in stage-timing/stagnation is correctly normalized; quarter/month boundary math in postmortem is correct including year-rollover; division-by-zero is properly guarded in rep-leaderboard, rep-trajectory, and win-probability.

---

## Frontend — Auth, Routing & Shared Lib

Files read: `lib/api-client.ts`, `auth-actions.ts`, `auth-bootstrap.ts`, `auth-guards.ts`, `auth-store.ts`, `auth-tokens.ts`, `cookies.ts`, `env.ts`, `handle-server-error.ts`, `utils.ts`, `hooks/use-auth.ts`, `routes/__root.tsx`, `routes/_app.tsx`, all `routes/_auth.*.tsx`, `features/auth/**`, `main.tsx`.

### Critical

39. **The generic error handler crashes on any real network error, breaking error reporting app-wide.** `lib/handle-server-error.ts:19-21`: `errMsg = error.response?.data.title`. The backend only ever returns FastAPI's `{"detail": "..."}` shape (verified against `routes/auth.py` and a repo-wide grep) — never `"title"` — so for any server error with a body, `errMsg` becomes `undefined` and a blank toast renders. Worse: for a genuine network error (offline, DNS failure, backend down — `error.response` itself is `undefined`), the un-guarded `.data.title` access **throws a `TypeError` inside the interceptor's own rejection handler**, so callers receive a `TypeError` instead of the original `AxiosError` (breaking any `isAxiosError()` check downstream, e.g. login's 403-unverified branch), and the "Something went wrong!" toast never fires at all. This is the app's single generic error handler, invoked from `api-client.ts`'s response interceptor for effectively every failed request.

40. **A failed silent token refresh never marks the user as unauthenticated — the UI reports "authenticated" forever after the session actually died.** `lib/api-client.ts:66-75`: the catch block calls `clearTokens()` but never calls `authStore.setUnauthenticated()`. Contrast with `auth-bootstrap.ts:24-27`, which does call it on the equivalent failure. Concrete scenario: mid-session, a refresh fails once (expired/rotated/revoked refresh token) — the app now has no access token and no refresh cookie, but `authStore` (and every `useAuth()` consumer, including `requireAuth`'s guard) still reports authenticated. The user sees protected content keep rendering, and navigating to another `/_app` route won't redirect to `/login` since the guard reads the never-updated store. Only a hard reload (which re-runs bootstrap) recovers.

### Major

41. **Cross-tab logout doesn't propagate.** `lib/auth-tokens.ts`, `lib/auth-store.ts` — the access token is a plain module-level variable and `authStore` is in-memory only, with no `storage`/`BroadcastChannel` listener. Logging out in tab A clears the shared refresh cookie, but tab B's in-memory state is untouched and keeps working until its access token naturally expires, at which point its refresh attempt fails and hits finding #40 — tab B gets permanently stuck reporting "authenticated" with a fully dead session.

42. **Login and OTP-verify show a misleading "invalid credentials" error if the follow-up `/me` call fails, even though login itself succeeded.** `features/auth/login/index.tsx:74-96`, `features/auth/otp/index.tsx:46-64` both call `setTokens(...)` after a successful login/OTP call, then make a separate `/me` call wrapped in the *same* try/catch as the original request. A transient `/me` failure after a genuinely successful login shows "Invalid email or password." / "Invalid or expired code." — factually wrong — while valid tokens already sit in memory/cookie, with `authStore` never becoming authenticated. The user is stuck on the auth page with orphaned valid tokens until they retry.

43. **`routes/_auth.reset.tsx` is the only auth route missing the `requireGuest` guard** that every sibling (`login`, `register`, `otp`, `getcode`) applies. An already-authenticated user opening a stale/forwarded reset-password link stays on the reset form instead of being bounced to `/upload` like everywhere else — looks like an overlooked omission.

### Minor

44. `routes/__root.tsx:38-47`'s OAuth-callback failure path calls `authStore.setUnauthenticated()` but not `clearTokens()`, unlike the equivalent path in `auth-bootstrap.ts` — an inconsistency that can leave a live refresh cookie in place while the app reports unauthenticated.
45. OTP input has no numeric-only `pattern`, only a `.length(6)` Zod check — a user can submit 6 letters/symbols, wasting an attempt against any backend rate limit.
46. `env.ts:6-9` silently falls back to `http://localhost:8000` if `VITE_*` env vars are missing in a production build, turning a config mistake into a confusing runtime failure (that then hits finding #39) instead of failing the build loudly.
47. `handle-server-error.ts:6`'s `console.log(error)` logs the full `AxiosError`, including the `Authorization: Bearer <token>` header — a latent exposure if any log-scraping tool is ever wired to console output.

Flagged as suspicious but likely dead/vestigial: a `204`-status branch in `handle-server-error.ts` that isn't a realistic axios error case.

---

## Frontend — Bank Dashboard & Commerce Intelligence

Files read: `features/dashboard/**` (bank-api.ts, index, all pages, sections, gauge), `features/commerce-intelligence/**` (ecommerce-api.ts, index, all pages, sections).

No leftover mock data or mock-fallback-on-error was found anywhere in either feature — loading/error/empty-state branching is real throughout.

### Major

48. **The cashflow-analysis donut chart colors slices by array index, not by category — the chart can visually contradict its own caption.** `features/dashboard/pages/cashflow-analysis.tsx:82-104`: `fill={index === 0 ? "#3ddc84" : ...}` assumes index 0 is always "business", but the backend (`bank_cashflow_analysis.py:73`) sorts this array by *amount descending*, and the category can be `"business"`, `"personal"`, or `"unclassified"`. For any merchant whose personal/unclassified spend exceeds business spend, the green "business" wedge is actually colored for personal/unclassified spend, while the center label (computed correctly via `.find()`) still states the right percentage — a lender-facing chart that misrepresents the merchant's spend mix.

49. **An LLM-supplied, unvalidated currency code can crash the AI Commerce Playbook page.** `features/commerce-intelligence/pages/ai-commerce-playbook.tsx:57` calls `.toLocaleString(undefined, { style: "currency", currency: card.currency })` trusting a field that Gemini generates from a free-text prompt instruction and that the backend schema validates only as `currency: str` with no format constraint (unlike other fields in the same schema that do have `Field(ge=..., le=...)` constraints). A malformed/hallucinated currency code throws `RangeError: Invalid currency code` during render, degrading to the app's generic error page rather than a blank screen, but taking down the entire page until the offending recommendation ages out.

50. **The ad-kill-switch "Pause campaign" button fires an irreversible action with no confirmation step.** `features/commerce-intelligence/pages/ad-kill-switch.tsx:89-104`. `pause.mutate(campaign.trim())` runs immediately on click — no `confirm()`, no modal — and the campaign name is free text with no dropdown of real campaigns (confirmed no such confirm/dialog pattern exists anywhere in the codebase). A typo silently pauses whatever string happens to match a real campaign, with no undo step first.

### Minor

51. `ecommerce-api.ts:242`'s `useConfigureAdKillSwitch` invalidates a query key (`["ecommerce", "ad-kill-config"]`) that no query in the codebase actually uses — harmless today, but signals incomplete wiring.
52. `churn-prediction.tsx:14`'s page description renders hardcoded fallback numbers (`?? 70`, `?? 60`) even when the query has errored, showing a confident-sounding sentence with fake numbers directly above the "could not load" error message.
53. None of the 9 commerce-intelligence query hooks pass `enabled: !!merchantId` (unlike every bank-dashboard hook, which does) — currently masked by the parent component's mount-gating, but a latent inconsistency.

Verified NOT bugs: all traced percentage fields are consistently scaled and formatted; `RfmSegmentationPage`'s segment iteration is safe (backend always initializes all 7 segments); `gauge.tsx` correctly clamps its input range; the nullable-envelope pattern in income-stability/avg-monthly-balance is handled correctly.

---

## Frontend — Sales Intelligence, Reconciliation & Upload

Files read: `features/sales-intelligence/**`, `features/reconciliation/**`, `features/upload/**`, `routes/_app.reports.tsx`.

### Critical

54. **A client-side bank-name/filename heuristic blocks legitimate PDF statement uploads before they reach the backend.** `features/upload/index.tsx:333-345`: if the selected bank isn't "Generic", the code rejects the file unless its filename (normalized) contains the bank name as a substring. A user selects "GTBank" and uploads a genuine GTBank statement named `eStatement_2024.pdf` — rejected client-side with "unrecognised bank format," even though the backend's OCR parser never sees the file. This is exactly the filename-substring heuristic the upload rewrite was supposed to eliminate, still gating the real upload call and blocking the majority of realistic bank statement filenames.

### Major

55. **In-flight upload/poll isn't cancelled on reset, tab-switch, or navigation — a stale poll can silently overwrite the current UI state.** `features/upload/index.tsx`'s `acceptFile` (lines 313-385) awaits a poll of up to 120s with no `AbortController`, mount-check, or request-generation guard. Switching tabs or clicking reset while a previous upload is still polling lets that stale promise later resolve and snap the UI back to the *old* upload's review screen, discarding current state (or firing state updates after unmount entirely).

56. **Reconciliation's "Net records analyzed" figure double-subtracts already-net data, producing a number that corresponds to nothing real.** Root cause is backend + frontend together: `routes/bank.py:166-172` sets `records_analyzed=len(eligible)` (already net of exclusions) and `records_excluded=len(transactions) - len(eligible)`; the frontend (`reconciliation-report.tsx:119-125`) then computes `netValue = records_analyzed - records_excluded`, subtracting the excluded count a second time. Example: 100 raw, 10 excluded → backend returns `analyzed=90, excluded=10` → UI shows "Total processed: 90 / excluded: 10 / **net: 80**" — 80 is meaningless; the real total was 100 and 90 already *is* the net figure.

57. **`exclusion_detail` is never populated by any production code path — the "Excluded records" table is always empty even when a nonzero exclusion count is displayed right next to it.** `excluded-records-table.tsx` renders `null` on an empty list; `record_analysis_run` (`reconciliation.py:41`) defaults `exclusion_detail=[]`, and the only caller producing a nonzero `records_excluded` (`routes/bank.py:166-174`) never passes it. Only the test suite ever populates this field, and even there with mismatched field names. Net effect: a bank reconciliation report can show "10 records excluded" in the totals while the accompanying breakdown silently shows nothing — no reason given for exclusions the totals already claim happened. (This is the frontend-visible symptom of backend finding #37's pattern.)

58. **The upload date-range "days" figure shown to users is a crude, sometimes badly wrong approximation of a value the backend already computes correctly but doesn't expose on this endpoint.** `features/upload/uploads-api.ts:226`: `months_of_data * 30` is used as a proxy for elapsed days, but `months_of_data` (`bank_ingestion.py:211`) counts *distinct calendar months touched*, not elapsed time — a statement spanning Jan 30 – Feb 3 (5 real days) touches 2 calendar months, so the UI shows "...60 days" next to a 5-day range. The backend separately computes an accurate `days_of_history` but the bank quality-report endpoint never returns it.

### Minor

59. `ProcessingPanel`'s progress bar (`features/upload/index.tsx:178-193`) is hardcoded to a static 60% width regardless of actual poll state — a leftover visual remnant of the old fake-progress animation that was never reconnected to the real poller.
60. Possible React key collisions: `excluded-records-table.tsx:22` keys on `item.reason` and `warnings-list.tsx:24` keys on `item.field`, neither deduplicated, with no backend guarantee of uniqueness — if two entries ever share a value, React will silently misrender/drop one.

Informational: `routes/_app.reports.tsx` is an unimplemented stub (`<div>Hello "/app/reports"!</div>`) with no data wiring at all — flagged in case it's expected to be functional.

Verified NOT bugs: all sales-intelligence query keys and TypeScript interfaces line up correctly against their backend counterparts; client-side derived math is properly guarded against empty arrays; `pollQualityReport` correctly bounds itself to 120s and distinguishes transient 404s from real errors; `normalizeQualityReport`'s field mapping matches the backend's serialized shapes one-to-one.

---

## Frontend — Shared Components, Account Settings & Misc Features

Files read: `components/**`, `context/theme-provider.tsx`, `features/account/**`, `features/app/**`, `features/landing/**`, `features/blog/**`, `features/intelligence/components/**`, `features/errors/**`, `features/notifications/**`, `features/playground/**`, `features/legal/**`, `features/contact/**`, all `routes/_app/*/index.tsx` and remaining top-level routes.

### Critical

61. **The `/playground` route imports the wrong component — a copy-paste bug that shows a full fake financial dashboard with fabricated numbers to anyone who visits it.** `routes/playground/index.tsx:1` imports `Playground` from `@/features/app` (the legacy prototype dashboard, full of `Math.random()`-driven charts and hardcoded fake metrics in `features/app/components/mock-data.tsx` — "$1.2M Total Revenue", etc.) instead of the actual stub at `features/playground/index.tsx` (a one-line placeholder). This route is public and not gated behind `_app`/auth (confirmed via `routeTree.gen.ts`), so anyone navigating to `/playground` sees a complete-looking fake analytics dashboard with no indication it's mock data.

### Major

62. **Every "Save"/"Update" action across the entire Account/Billing/Settings surface is dead — pure client-side state with zero backend wiring.** Confirmed across `account-tab.tsx:62-64`, `security-tab.tsx:66-68,83-85` ("Save changes", "Update password", "Enable 2FA" have no `onClick` at all), and the same pattern (local `useState` only, no API call on any action) in `notifications-tab.tsx`, `privacy-tab.tsx`, `subscription-tab.tsx`, `contextual-markers.tsx`, `team-permissions.tsx`, and `workspace-settings.tsx`. A user filling in a new password and clicking "Update password" sees nothing happen — no request, no error — and the value is lost the moment the component unmounts.

63. **Footer links all navigate to `/` regardless of label.** `components/Footer/LinksList.tsx:8`: `<NavLink path='/' name={listItem}/>` hardcodes `path='/'` for every item, while `Footer.tsx` renders real-looking labels ("Privacy Policy", "Terms of Service", "Contact Us", "Blog", etc.) that all have real corresponding routes elsewhere in the app. Every footer link click lands on the home page instead of the page it names.

64. **Orphaned duplicate navbar component left in the tree, containing a dead-end and a broken link.** `components/Header/{Header,NavList,NavListItem}.tsx` are not imported anywhere in the app (verified by grep) — apparently the leftover "duplicate navbar" a recent commit meant to remove, with the files never actually deleted. Within it: `NavList.tsx:6-8` links to `/data` (no matching route exists anywhere — a hard 404) and `/reports` (resolves to an unfinished stub). Not currently reachable by users, but confusing dead code and a latent risk if ever re-imported.

### Minor

65. Contact page email is `contact@scamwick.com` — a typo of the domain (every other page consistently uses `@scanwick.com`).
66. The contact form's submit handler (`features/contact/index.tsx:6-8`) only calls `preventDefault()` — it never sends the name/email/message anywhere; a user's message is silently discarded with no success/error feedback.
67. `FormField.tsx:12` derives its `<label>`'s `htmlFor` from `label.toLowerCase()` rather than the actual input `id` prop — coincidentally correct on login/reset-password, but broken on the register page's First/Last Name fields (`label=""`, `id="first-name"`), producing an empty, non-functional label with no screen-reader association.

Verified NOT bugs: all five `_app/*/index.tsx` route files correctly import and render their matching feature component (no copy-paste mismatch among these — that bug is isolated to `/playground`); `navigation-progress.tsx` can't get stuck in a pending state; `theme-provider.tsx` has no SSR/hydration risk (this is a pure client-side SPA); the blog's `$slug.tsx` handles unknown slugs gracefully via a "coming soon" view and uses no `dangerouslySetInnerHTML` anywhere.

---

## Addendum — Security-Focused Review (2026-07-22)    This is doe today means second audit.

A follow-up, security-specific pass over the same branch (auth, RBAC, crypto, injection, upload/storage path handling, CORS, email templating). Most of the ground here overlaps with the Critical/Major items above (#1, #2, #35 especially) — these two are net-new, not previously captured.

68. **Bank account numbers are hashed with unsalted, unkeyed SHA-256 as the sole confidentiality control.** `backend/app/services/encryption.py:53-56` (`hash_value()`), consumed by the new `accounts` table (`backend/app/models/accounts.py`) which deliberately drops the reversible Fernet-encrypted copy the legacy `BankAccountIdentifier` table kept. A 10-digit NUBAN has a keyspace of 10^10 — trivially brute-forced against unsalted SHA-256 at GPU speed. Anyone who gets read access to the `accounts` table (backup leak, replica misconfig, a future SQLi, insider access) can recover every real account number, defeating the "never stored in plaintext" design intent stated in the model's own docstring. **Fix:** switch to HMAC-SHA256 with a server-side pepper — stays deterministic so the existing equality-lookup/dedup queries (`bank_ingestion.py`, `analyze.py`) keep working, but brute force becomes infeasible.

69. **`POST /api/auth/forgot-password` intentionally discloses account existence.** `backend/app/routes/auth.py:278-293` returns a distinct 404 for unregistered emails vs. success for registered ones — the route's own docstring says this is a deliberate reversal of anti-enumeration behavior ("traded off in favor of telling the user plainly what's wrong"). Not a bug in the sense of being unintended, but worth a conscious yes/no: is enumeration risk acceptable for a product handling bank statements and sales pipeline data? If not, revert to the uniform "if registered..." response used by `/resend-otp`.

Investigated and ruled out (documented for completeness, not actionable): a possible cross-merchant IDOR via the client-supplied `mono_account_id` in `POST /api/v1/bank/upload/mono` (`backend/app/routes/bank.py:574-611`) — the endpoint never checks that the Mono account belongs to the caller's merchant, but Mono account IDs are opaque third-party identifiers obtainable only via that specific account's own consent flow, not guessable/enumerable. Binding it explicitly to the merchant would still be good defense-in-depth if Mono's ID scheme ever turns out weaker than assumed.

---

## Suggested priority order for fixing

1. **Data-integrity/financial-correctness criticals first**, since these corrupt numbers merchants and lenders are making real decisions on: own-account-transfer exclusion never wired (#21), reconciliation double-subtraction (#56) and its missing exclusion detail (#57), sales-vertical silent exclusions (#37), Mono currency mislabeling (#23).
2. **Account-takeover and data-exposure criticals**: registration overwrite (#2), OTP/reset-link logging (#1), the RBAC fail-open in the AI playbook (#35).
3. **Deployment-blocking criticals**: the Celery/API filesystem split (#12) and the resulting stuck-forever uploads (#13) — these likely block the ingestion pipeline entirely in whatever environment mirrors the given `docker-compose.yml`.
4. **User-facing criticals that are cheap to fix**: the `/playground` wrong import (#61, one-line fix), the upload bank-name filename heuristic (#54), the frontend error-handler crash (#39) and the stuck-"authenticated" session bug (#40).
5. Everything else, roughly in the severity order listed above.
