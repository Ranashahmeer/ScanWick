# Scanwick — Developer Guide

This is the current-state reference for anyone joining this codebase. Unlike `SYSTEM_DOCUMENTATION.md` (an append-only historical build log from the two developers who built this — useful for archaeology, not for onboarding), this document describes **what exists in the code today** and is meant to be kept up to date as the system changes.

**What Scanwick is:** a business-intelligence SaaS. A merchant uploads their raw business data (CSV exports or bank statement PDFs) and Scanwick turns it into dashboards — cashflow/fraud/loan-readiness analysis for a bank account, or revenue/margin analysis for an e-commerce store. There are exactly **two verticals** today: `ecommerce` and `bank`. (A third vertical, "sales" — a CRM pipeline analyzer — existed earlier in the project's history and was deliberately removed in full, backend and frontend, along with several non-core depth features. See [History: what got removed](#history-what-got-removed) if you find references to it in old docs or git history.)

---

## Table of contents

1. [Repo layout](#repo-layout)
2. [Getting started (local dev)](#getting-started-local-dev)
3. [Product model](#product-model)
4. [Backend architecture](#backend-architecture)
   - [Entrypoint & middleware](#entrypoint--middleware)
   - [Configuration](#configuration)
   - [Database](#database)
   - [Models](#models)
   - [Routes](#routes)
   - [RBAC](#rbac)
   - [Upload / ingestion pipeline](#upload--ingestion-pipeline)
   - [Plans, billing & entitlements](#plans-billing--entitlements)
   - [Celery](#celery)
   - [Migrations](#migrations)
   - [Backend testing](#backend-testing)
   - [Other backend services](#other-backend-services)
   - [Backend dependencies](#backend-dependencies)
5. [Frontend architecture](#frontend-architecture)
   - [Build tooling](#build-tooling)
   - [Routing](#routing)
   - [API client & auth state](#api-client--auth-state)
   - [Auth UI flow](#auth-ui-flow)
   - [Feature folders](#feature-folders)
   - [Upload / mapping UI flow](#upload--mapping-ui-flow)
   - [Plan/billing UI](#planbilling-ui)
   - [Shared components](#shared-components)
   - [Theming](#theming)
   - [Frontend testing & linting](#frontend-testing--linting)
6. [Cross-cutting conventions](#cross-cutting-conventions)
7. [Known gaps & things that look wired but aren't](#known-gaps--things-that-look-wired-but-arent)
8. [History: what got removed](#history-what-got-removed)
9. [Where else to look](#where-else-to-look)

---

## Repo layout

This is a **pnpm + Turborepo monorepo** with two workspace packages:

```
scanwick/
├── backend/          # FastAPI + SQLAlchemy + Celery (Python, Poetry-managed)
├── frontend/          # React + TanStack Router/Query (TypeScript, Vite)
├── docs/              # Architecture docs (this file lives here)
├── issues/            # Point-in-time audit/scope docs (see "Where else to look")
├── testing/           # Manual QA logs, not automated tests
├── docker-compose.yml # redis + api + celery-worker + celery-beat + minio, for local/prod-like runs
├── pnpm-workspace.yaml
├── turbo.json
└── package.json       # root scripts: dev/build/lint delegate to turbo
```

Both `backend/` and `frontend/` have their own `package.json` with `dev`/`build`/`lint` scripts, so **`pnpm dev` at the repo root runs both simultaneously** via Turborepo (`turbo run dev`, `cache: false, persistent: true`). Backend's `dev` script is `node scripts/venv-run.js python -m uvicorn app.main:app --reload` — `scripts/venv-run.js` is a small cross-platform shim that resolves into `backend/.venv/Scripts/<tool>.exe` (Windows) or `.venv/bin/<tool>` (Unix), since Python venvs aren't laid out the same way `node_modules/.bin` is and npm scripts can't hardcode a Unix-style path that also works from `cmd.exe`.

---

## Getting started (local dev)

### Prerequisites
- Node.js + pnpm (`packageManager: pnpm@10.33.0` pinned in root `package.json`)
- Python 3.11 + Poetry (backend `pyproject.toml` pins `^3.11`)
- Redis (Celery broker/result backend + rate limiting + OTP lockout + OAuth CSRF state) — or just run `docker compose up redis` for it alone
- A Postgres database for anything beyond quick local hacking (SQLite is the zero-setup default — see [Database](#database))

### Backend
```bash
cd backend
poetry install                 # or: pip install -r requirements.txt
# create backend/.env — see Configuration below for the full field list.
# NOTE: there is currently no committed .env.example in backend/; you'll
# need to hand-assemble one from the table in this doc, or copy a
# teammate's (minus secrets).
poetry run uvicorn app.main:app --reload
```
With `DEV_MODE=true` and no `DATABASE_URL` override, the backend defaults to a local SQLite file (`./app.db`) and needs nothing else running to boot — but Celery-dispatched features (uploads, webhooks) will fail without Redis reachable, and `CELERY_TASK_ALWAYS_EAGER=true` (the default) makes tasks run **synchronously in-process** in dev, sidestepping that.

Run the Celery worker/beat separately if you need to test genuinely-async behavior:
```bash
poetry run celery -A app.celery_app worker --loglevel=info
poetry run celery -A app.celery_app beat --loglevel=info
```

### Frontend
```bash
cd frontend
pnpm install
cp .env.example .env           # VITE_API_BASE_URL / VITE_AUTH_API_BASE_URL
pnpm dev
```
`frontend/README.md` is currently still the **stock Vite React+TS template README** — it has no Scanwick-specific instructions. Use this doc instead.

### Everything via Docker
`docker-compose.yml` at the repo root brings up `redis`, `api`, `celery-worker`, `celery-beat`, and `minio` (S3-compatible storage, only relevant if `STORAGE_BACKEND=s3`). It does **not** include the frontend or a Postgres container — bring your own Postgres and point `DATABASE_URL` at it, or stay on SQLite for `api`/`celery-worker`/`celery-beat` (they share a named volume `upload-staging-data` mounted at `/data/uploads` so both containers see the same staged-upload files when `STORAGE_BACKEND=local`).

### Turborepo shortcuts (repo root)
```bash
pnpm dev      # backend (uvicorn --reload) + frontend (vite) together
pnpm build    # frontend production build; backend build is a no-op
pnpm lint     # frontend eslint + backend ruff/black --check
```

---

## Product model

- **Merchant** = the tenant unit. Every user gets a deterministic `merchant_id` (UUID5, auto-provisioned on first login/`/me` call — see `merchant_provisioning.py`). Multiple users can share a merchant via team invites.
- **Vertical** = `ecommerce` or `bank`. A merchant can have roles/data in both independently — they're not mutually exclusive product tiers, just two different data domains with their own role sets and dashboards.
- **Upload → detect → map → ingest → dashboard** is the core loop for both verticals: a user uploads a CSV (or bank PDF), the system detects which vertical it belongs to and maps its columns onto canonical fields, a Celery task ingests it into canonical tables, and dashboards read from those tables once ingestion succeeds. See [Upload / ingestion pipeline](#upload--ingestion-pipeline) for the full walkthrough.
- **Plan tiers**: `free` / `basic` / `premium`, gating which dashboard sections are visible (`FULL`/`LIMITED`/`NONE` per feature) — see [Plans, billing & entitlements](#plans-billing--entitlements).
- **RBAC**: within a merchant + vertical, a user has one role (e.g. `owner`, `admin`, `manager`, `viewer` for ecommerce; `bank_owner`, `bank_admin`, `loan_officer`, `bank_viewer` for bank) that governs which endpoints/data they can reach — independent of plan tier.

---

## Backend architecture

Root: `backend/`. FastAPI + SQLAlchemy (async) + Celery/Redis + Alembic.

### Entrypoint & middleware

`app/main.py`:
- `FastAPI(title="Scanwick API")`.
- **CORS**: allows `https://scanwick.com` / `https://www.scanwick.com` always; in `DEV_MODE` also allows `localhost:3000`/`localhost:5173` and any `*.trycloudflare.com` origin (for cloudflared quick-tunnel dev sharing). Credentials on, all methods/headers.
- **Rate limiting**: a custom `@app.middleware("http")` (`rate_limit_auth`) — Redis-backed, per-IP, applies only to `/api/auth/*` paths: 10 requests / 60s window, else `429`.
- **Routers mounted**: `auth`, `analyze` (legacy), `bank`, `ecommerce`, `internal`, `mapping`, `notifications`, `payments`, `plans`, `privacy`, `reconciliation`, `team`, `uploads`, `webhooks`.
- **Static mount**: `/static/uploads` only when `STORAGE_BACKEND == "local"` (S3 backend serves via presigned URLs, no mount needed).
- `GET /health` → `{"status": "ok"}`.
- **`startup_event`** (production safety guards, both introduced to stop the app from booting with dev-only secrets):
  - Refuses to start if `not DEV_MODE` and `FERNET_KEY` is still the public default dev key.
  - Refuses to start if `not DEV_MODE` and `SECRET_KEY` is the default placeholder or shorter than 32 chars.
  - Also runs `Base.metadata.create_all` (belt-and-suspenders alongside Alembic migrations).

### Configuration

`app/config.py` — `Settings(BaseSettings)`, reads from `backend/.env` (`extra: "ignore"`). Full field reference:

| Field | Default | Notes |
|---|---|---|
| `database_url` / `local_database_url` | `sqlite+aiosqlite:///./app.db` | see [Database](#database) |
| `secret_key` | `"change-me-in-production"` | JWT signing key. **Required, 32+ chars, non-default in prod** (enforced at startup) |
| `algorithm` | `HS256` | JWT alg |
| `access_token_expire_minutes` | `15` | |
| `refresh_token_expire_days` | `7` | |
| `dev_mode` | `False` | flips SQLite default, Celery eager mode, CORS localhost allowance |
| `use_remote_db_in_dev` | `False` | set true to point dev at a real `DATABASE_URL` instead of local SQLite |
| `google_client_id` / `google_client_secret` / `google_redirect_uri` | — | Google OAuth |
| `frontend_url` | `http://localhost:5173` | used to build redirect URLs |
| `resend_api_key` / `resend_from_email` | `""` | email provider; unset → logs to console instead of sending |
| `bcrypt_rounds` | `12` | |
| `gemini_api_key` / `gemini_model` | `""` / `gemini-2.5-flash` | **required for AI features** (dataset-detection LLM fallback, lender brief, health playbook) |
| `celery_broker_url` / `celery_result_backend` | `redis://localhost:6379/0` / `.../1` | separate Redis DB indices |
| `celery_task_always_eager` | `True` | only takes effect when `dev_mode=True` — never eager in prod regardless of this flag |
| `storage_backend` | `"local"` | `"local"` or `"s3"` |
| `local_storage_dir` | `./uploads` | |
| `backend_base_url` | `http://localhost:8000` | |
| `s3_bucket` / `s3_region` / `s3_endpoint_url` / `s3_access_key_id` / `s3_secret_access_key` / `s3_presigned_url_expiry_seconds` | — | S3-compatible storage (works with MinIO locally, `s3_endpoint_url` set) |
| `fernet_key` | public dev-only key | **required, non-default, in prod** — field-level encryption key |
| `mono_secret_key` | `""` | Mono open banking (NG/GH/KE) |
| `paystack_secret_key` + plan codes | `""` | primary billing provider |
| `flutterwave_secret_key` + plan IDs + webhook secret hash | `""` | automatic fallback billing provider |
| `basic_plan_price_usd` / `premium_plan_price_usd` | `8.99` / `16.99` | converted to NGN at checkout via live FX rate |
| `fallback_usd_ngn_rate` | `1500.0` | emergency-only, used if live FX fetch fails |

There is currently no committed `.env.example` in `backend/` — this table is the closest thing to one.

### Database

`app/database.py`:
- URL resolution: `dev_mode and not use_remote_db_in_dev` → SQLite (`local_database_url`). Otherwise reads `DATABASE_URL` from the environment directly — **raises `RuntimeError` if unset** (never silently falls back to SQLite in a non-dev context). Normalizes Railway-style `postgresql://` URLs to `postgresql+psycopg://`.
- Pooling: `pool_pre_ping=True, pool_recycle=1800` always; `pool_size=10, max_overflow=20` added only for non-SQLite engines (SQLite's pool class rejects those kwargs).
- `get_db()` — async generator dependency, one `AsyncSession` per request.
- `app/dependencies.py`: `get_current_user` (JWT Bearer, 401 on failure) and `get_current_user_optional` (same decode, returns `None` instead of raising — used by the invite-accept flow, which must work for both logged-in and anonymous callers).

### Models

All in `app/models/`, registered via `app/models/__init__.py`, sharing `Base` from `app/models/auth.py`.

| File | Table(s) | What it holds |
|---|---|---|
| `auth.py` | `users`, `refresh_tokens`, `otp_records`, `password_resets` | `User` (email, hashed_password, google_id, `subscription_tier`, TOTP fields, `deletion_requested_at`), refresh-token rows (device/IP tracked) |
| `accounts.py` | `accounts` | Bank `Account`: hashed account number, bank name, base currency, statement period, opening/closing/computed balance + integrity check result |
| `bank_account_identifiers.py` | `bank_account_identifiers` | Legacy support table for the old `/api/analyze` bank-statement path — reversible Fernet-encrypted account number + one-way hash |
| `bank_transactions.py` | `bank_transactions` | Canonical bank transaction row: amount, currency + historical FX rate, type/mode/category enums, recurring/own-transfer/anomalous flags, fraud flags (JSON), running balance, data source |
| `column_mappings.py` | `column_mappings` | Persisted, confirmed column mapping per (merchant, analyzer_type, header-set signature) — lets a repeat upload with the same headers skip the confirmation step |
| `contextual_markers.py` | `contextual_markers` | Merchant-defined date ranges to exclude/flag as anomalous in analytics |
| `exchange_rates.py` | `exchange_rates` | (currency pair, date) → rate, used for historical FX conversion |
| `generated_reports.py` | `generated_reports` | Report-library rows (module, template, stats/chart JSON, export URLs) |
| `login_events.py` | `login_events` | Login attempt audit log (success/blocked + reason) |
| `merchant_settings.py` | `merchant_settings` | Per-merchant settings: owner email, base currency, default return cost |
| `notification_preferences.py` | `notification_preferences` | (user, event, channel) → enabled |
| `order_items.py` | `order_items` | Line items for an order (SKU, quantity, unit cost/price/shipping/return-cost/net-margin) |
| `orders.py` | `orders` | Canonical ecommerce order: revenue, currency+FX, refunds/discounts/shipping/fees/ad-spend, COGS, net margin, channel, customer, status, data source; unique on (merchant, data_source, external_order_id) |
| `payment_transactions.py` | `payment_transactions` | One row per billing charge attempt, keyed by `provider_reference` (webhook idempotency) |
| `reconciliation_reports.py` | `reconciliation_reports` | Per-analysis-run record of what was included/excluded from an ingestion and why |
| `report_schedules.py` | `report_schedules` | Scheduled report config (frequency, recipients, format) |
| `subscriptions.py` | `subscriptions` | One active subscription per user: provider, tier, status, period end |
| `team_invites.py` | `team_invites` | Pending/accepted/revoked team invites (email, vertical, role, token, expiry) |
| `uploads.py` | `uploads` | One row per upload attempt: status, rows parsed/rejected, date range, warnings, metadata, error message |
| `user_merchant_roles.py` | `user_merchant_roles` | The RBAC table: (user, merchant, vertical) → role. Also defines the core enums below |

**Core enums** (`app/models/user_merchant_roles.py`):
- `Vertical`: `ecommerce`, `bank` — this is the two-vertical model referenced throughout the codebase.
- `EcommerceRole`: `owner`, `admin`, `manager`, `viewer`.
- `BankRole`: `bank_owner`, `bank_admin`, `loan_officer`, `bank_viewer`.

### Routes

All under `app/routes/`. RBAC role sets and plan-feature keys are noted where relevant — see [RBAC](#rbac) and [Plans, billing & entitlements](#plans-billing--entitlements) for how those checks work.

**`auth.py`** — prefix `/api/auth`, identity-only (no merchant RBAC):
register → OTP verify → login (or TOTP challenge if 2FA enabled) → refresh/logout; `/me` (get/patch), avatar upload, change-password, 2FA setup/enable/disable, session listing/revocation, login history, account-deletion request/cancel, forgot/reset-password, Google OAuth (`/google`, `/google/callback`).

**`uploads.py`** — prefix `/api/v1/upload`:
- `POST /detect` — classify a CSV's vertical from its headers (auth only, no merchant scoping).
- `POST /csv` — the main ingestion entrypoint (202 Accepted). Role-gated per vertical (`owner`/`admin`/`manager` for ecommerce, `bank_owner`/`bank_admin` for bank). Runs column-mapping resolution and either auto-dispatches ingestion or returns `needs_mapping`.
- `GET /{upload_id}/quality-report` — any granted role for that upload's merchant/vertical.

**`mapping.py`** — prefix `/api/v1/mapping`:
`POST /detect` (re-run detection on a staged upload), `POST /confirm` (persist a confirmed mapping, dispatch ingestion).

**`ecommerce.py`** — prefix `/api/v1/ecommerce` — deliberately small today (see [History](#history-what-got-removed)):
- `GET /dashboard/summary` — any `EcommerceRole` + feature `ecommerce.dashboard_summary`.
- `GET /dashboard/revenue` — any `EcommerceRole` + feature `ecommerce.net_margin_dashboard`.

**`bank.py`** — prefix `/api/v1/bank`, the largest single route file:
`GET /accounts` (role-shaped response for `loan_officer`), `GET /dashboard/summary`, `GET /diagnostic/income-stability`, `GET /diagnostic/abm`, `GET /diagnostic/cashflow-analysis`, `GET /predictive/fraud-risk` (flags redacted for non-owner/admin roles), `GET /predictive/loan-readiness` (3-tier plan gating: free=grade only, basic=score+grade+tier, premium=full), `GET /predictive/cashflow-forecast` (premium-only), `GET /ai/lender-brief` (premium-only), `GET /ai/financial-health-playbook` (premium-only), `GET /upload/{id}/quality-report`, `POST /upload/pdf` (15MB limit, dispatches Celery), `POST /upload/mono` (synchronous, no durable `Upload` row).

**`reconciliation.py`** — prefix `/api/v1/reconciliation` — `GET /{analysis_run_id}`, any granted role for that report's own merchant/analyzer_type.

**`privacy.py`** — prefix `/api/v1/privacy` (GDPR-style): `GET /export` (synchronous JSON bundle as a download), `POST /delete-data` (wipes orders/order_items/bank_transactions/accounts/uploads/reconciliation_reports/bank_account_identifiers — deliberately leaves the user row, billing history, and login records intact).

**`team.py`** — prefix `/api/v1/team`: `GET /members`, `GET /my-businesses`, invite/resend/revoke, member role update/removal — all owner-only actions enforced inside the service layer; `POST /invite/{token}/accept` works for both new and existing accounts.

**`payments.py`** — prefix `/api/v1/payments`: checkout (Paystack primary, Flutterwave automatic fallback), verify, subscription, history, cancel.

**`plans.py`** — prefix `/api/v1/plans`: `GET /permissions` — **public, no auth** — serializes the entire plan-feature matrix (the frontend fetches this once and caches it for an hour).

**`webhooks.py`** — prefix `/api/v1/webhooks` (signature-verified, not auth-gated): `POST /paystack` (HMAC-SHA512), `POST /flutterwave` (`verif-hash` header compare) — both dispatch async Celery processing.

**`notifications.py`** — prefix `/api/v1/notifications`: `GET`/`PUT /preferences`, layered over a hardcoded default matrix.

**`internal.py`** — `POST /api/internal/ping-task` — Celery/Redis connectivity smoke test, any authenticated user.

**`analyze.py`** — prefix `/api/analyze` — the **legacy, original single-file analyzer** (predates the vertical-specific pipeline). Still live: generic CSV upload → `app/utils/analyzer.py`'s industry-scoring engine, persists bank-account identifiers if it detects a bank statement, gates `health_score.components` by subscription tier. Left alone deliberately during the Section 4 cleanup (an explicit "leave it alone" decision, not an oversight) — don't assume it's dead code.

### RBAC

`app/services/rbac.py` + `app/services/merchant_dependencies.py`. `UserMerchantRole` (user, merchant, vertical) → role string is the single source of truth; the role string is validated against the right enum (`EcommerceRole` or `BankRole`) at the service layer, not by a DB constraint.

- **`check_role(db, user, merchant_id, vertical, allowed_roles)`** → `(error_or_None, role_row_or_None)`. Distinguishes two 403 cases: no role at all for this merchant/vertical, vs. a role that exists but isn't in `allowed_roles`.
- **`check_any_role(...)`** — any role at all is sufficient (used for reconciliation/quality reports, which any granted role can read).
- **`check_any_merchant_access(...)`** — any role in *any* vertical (genuinely cross-vertical features).
- **`require_merchant_role(vertical, allowed_roles)`** — a FastAPI dependency factory; reads `merchant_id` from the query string, validates it *before* the route body runs. Used where the route takes `merchant_id` directly (ecommerce dashboards, `bank /accounts`).
- **`require_account_role(vertical, allowed_roles)`** — same idea but for `account_id`-scoped bank routes: resolves only the `Account` row (not its transactions) before authorizing, specifically because an earlier bug let an unauthorized caller trigger a side-effecting transaction scan just by guessing an `account_id`.

`loan_officer` (bank vertical) gets a narrower, redaction-heavy view enforced ad hoc in `bank.py`'s `_shape_*` helpers at the route layer, not via a separate permission system — worth knowing if you're adding a new bank endpoint that should also be loan-officer-visible.

### Upload / ingestion pipeline

This is the core data-in flow, worth understanding end to end:

1. **Detect** (`POST /upload/detect`, optional standalone call, also run inline during `/upload/csv`) — `app/services/dataset_detection.py::detect_dataset_type` scores bank vs. ecommerce using independent heuristics per vertical (bank: 4 signals — date/amount/balance/narration columns; ecommerce: literal-header-match ratio). Below `MIN_CONFIDENCE = 0.4`, returns no verdict. `detect_dataset_type_async` adds a Gemini LLM fallback (`_classify_with_llm`) when the heuristic's top score is under `0.75` — degrades gracefully to the heuristic result on any LLM failure, never raises.

2. **Map** (`app/services/column_mapping.py`, the "Data Mapping Layer") — a four-tier resolver:
   - **Exact**: normalized header matches a known synonym in `CANONICAL_SYNONYMS[analyzer_type]`.
   - **Fuzzy**: rapidfuzz `token_sort_ratio` above `FUZZY_THRESHOLD=0.82` with a `FUZZY_MARGIN=0.10` gap over the runner-up.
   - **Needs confirmation**: genuine ambiguity, or — deliberately — **any money field that only fuzzy-matched**. `MONEY_FIELDS` (e.g. `gross_revenue`, `amount`, `credit_amount`) never auto-apply on a fuzzy match; only an exact match or a previously-confirmed mapping is trusted for money.
   - **Unmapped**: no candidate scored ≥ `MIN_CANDIDATE_SCORE=0.5`.
   - `compute_source_signature(columns, analyzer_type)` hashes the normalized header set so a repeat upload with identical headers reuses a previously-confirmed mapping with zero user interaction (`column_mapping_store.py`).
   - If mapping produces any `needs_confirmation` entries, `POST /upload/csv` returns `status: "needs_mapping"` instead of ingesting immediately; the frontend collects the user's answers and calls `POST /mapping/confirm`, which then dispatches ingestion.

3. **Ingest** (Celery tasks, one per vertical+format):
   - `ingest_bank_csv` / `ingest_bank_pdf` (`app/services/bank_ingestion.py`, `bank_pdf_ingestion.py`) — signed-amount resolution (5 cases depending on which columns exist), balance-integrity check, quality-report computation (date gaps, warnings), dedup by (date, amount, description).
   - `ingest_ecommerce_csv` (`app/services/ecommerce_ingestion.py`) — platform-specific literal maps for Shopify/WooCommerce plus a generic fallback, deterministic surrogate order IDs for rows with no real order ID (prevents duplicate-on-reupload), deterministic customer IDs (UUID5 from email), dedup on `(merchant, data_source, external_order_id)` with savepoint-retried inserts for real concurrent-upload races.
   - Currency conversion always uses the **historical rate at the transaction/order date**, never the current rate (`exchange_rates.py::get_historical_rate`).
   - Contextual markers (`contextual_markers.py`) flag rows in a merchant-defined date range as `is_anomalous=True` at ingestion time; creating a new marker immediately re-flags already-ingested rows in range too.

4. **Dashboard** — once `Upload.status == "ready"`, dashboard endpoints read directly from the canonical tables (`orders`/`order_items` or `accounts`/`bank_transactions`).

Uploads are staged through `app/services/storage.py` (local disk in dev, S3/R2 in prod) rather than a fixed filesystem path — this is what lets the API and Celery worker be independently-deployed services with no shared filesystem in production, while `docker-compose.yml` gives them a shared named volume locally for the same effect when `STORAGE_BACKEND=local`.

### Plans, billing & entitlements

- **`app/services/plan_permissions.py`** — `PLAN_FEATURES`, a flat list of `PlanFeature` entries (key, category, label, per-tier `FeatureAccess{level, detail}`, whether it's actually implemented, whether enforcement is `"route"`-level or just descriptive `"aggregate"`). `AccessLevel` is `FULL`/`LIMITED`/`NONE`; unknown feature key or tier **fails closed to `NONE`**. Exposed publicly, unauthenticated, at `GET /api/v1/plans/permissions` — the frontend fetches this matrix once and reuses it everywhere (see [Plan/billing UI](#planbilling-ui)).
- **`app/services/entitlements.py`** — `check_feature_access(user, feature_key)` mirrors `rbac.check_role`'s `(error, value)` convention: `NONE` → 403 `UPGRADE_REQUIRED`; `LIMITED`/`FULL` → the route gets the `FeatureAccess` back to shape its own response (e.g. redact some fields for `LIMITED`).
- **Billing**: `routes/payments.py` + `services/payments.py` (checkout/verify/subscription/history/cancel), `routes/webhooks.py` (Paystack/Flutterwave inbound, signature-verified). Paystack is primary; Flutterwave is an automatic server-side fallback if the Paystack call itself fails. `apply_successful_charge` is the single idempotent "a charge succeeded" handler shared by both the webhook path and the manual `/verify` (post-redirect) path, keyed on `PaymentTransaction.provider_reference` (unique). Prices are fixed in USD and converted to NGN at checkout time using a live, hourly-synced FX rate with a hardcoded emergency fallback.

### Celery

`app/celery_app.py` + `app/tasks.py`. JSON serialization, UTC, `task_soft_time_limit=300`/`task_time_limit=360`, `task_acks_late=True`, `task_reject_on_worker_lost=True`, `worker_prefetch_multiplier=1`. `task_always_eager` only takes effect when `dev_mode=True` (never eager in production regardless of the config flag).

**Beat schedule**: `"sync-usd-ngn-rate"` → hourly (`crontab(minute=0)`). This is the *only* scheduled job today — earlier versions of this codebase also beat-scheduled postmortem-report generation and an ad-kill-switch evaluation; both were removed along with the features they served (see [History](#history-what-got-removed)). If you see a comment or doc elsewhere still listing those, it's stale.

**Registered tasks**: `ping_task` (broker/worker/backend smoke test), `ingest_bank_csv`, `ingest_bank_pdf`, `ingest_ecommerce_csv`, `fx.sync_usd_ngn_rate` (beat-scheduled), `payments.process_webhook_event_paystack`/`payments.process_webhook_event_flutterwave`. `app/services/mono_ingestion.py` also defines a Celery-wrapped `ingest_mono_account_task`, but `routes/bank.py`'s `/upload/mono` handler calls the plain async `ingest_mono_account(...)` directly, not the task — the Celery wrapper is currently dead code, not actually in the async path. Every ingestion/webhook task follows the same shape: a sync `@celery_app.task` wrapper that does `asyncio.run(_async_impl(...))` and opens its own DB session inside the task rather than reusing a request-scoped one.

### Migrations

`backend/migrations/`, Alembic. Single linear chain (verified — every revision id is exactly one other migration's `down_revision`, no branches/merges), base `6aad96943bb2` → head `b1c4d7e2f3a8`.

`migrations/env.py` reuses `app/database.py`'s URL-resolution logic directly rather than duplicating it in `alembic.ini`, and converts `sqlite+aiosqlite://` → `sqlite://` since migrations run synchronously. `ALEMBIC_DATABASE_URL_OVERRIDE` lets tests point at a disposable database.

**SQLite-vs-Postgres divergence**: a few migrations use `op.batch_alter_table` (needed because SQLite can't `ALTER`/`DROP COLUMN` natively — batch mode recreates the table under the hood, harmless on Postgres too), and one migration (`74b3becc9b81_...`) uses Postgres-only `ALTER TYPE ... ADD VALUE` to widen a native enum, which is a no-op on SQLite (no enum type there). That migration is specifically why `tests/migrations/test_migrations_apply_cleanly_postgres.py` exists — it's the only test that needs a real Postgres instance and is skipped without one.

**If you ever need to delete a migration** (as happened during the Section 4 cleanup): check whether it creates more than one table/column — if it creates both a surviving and a doomed one, you have to edit it (strip the doomed DDL, keep the rest) rather than delete the file outright, and re-point the `down_revision` of whatever migration follows it. Always re-verify the chain is still linear afterward (walk `revision`/`down_revision` pairs — a small script, not a manual eyeball, since even one wrong pointer produces a broken chain that's easy to miss visually).

### Backend testing

`pytest` from `backend/` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`, both in `pyproject.toml`). Directory mirrors `app/`: `tests/{migrations,models,routes,schemas,services,utils}/`.

Three client fixtures exist side by side in `tests/conftest.py`, deliberately — pick the right one:
- **`client`** (async httpx) — the majority convention (~90 tests). Auto-authenticates as a fixed fixture user (premium tier, so plan gating never interferes) **and bypasses the merchant-role lookup entirely** (always full owner access). Use this for business-logic tests that aren't specifically about RBAC.
- **`rbac_client`** (async httpx) — for `test_ecommerce_rbac.py`/`test_bank_rbac.py` only. No bypass: seed real `UserMerchantRole` rows yourself, then `as_user(user)` per request. This is what actually exercises RBAC enforcement — use it whenever you're testing who can/can't reach an endpoint.
- **`sync_client`** / **`authenticated_client`** (sync `TestClient`) — an older convention, isolated per-test SQLite file (not `:memory:`). `sync_client` unauthenticated (register/login tests), `authenticated_client` with a fixed `get_current_user` override.

Autouse fixtures (apply to every test, no opt-in needed): real emails are no-op'd, real payment-provider calls are blocked (secrets blanked), FX rate is pinned at 1500 NGN/USD, and the Redis in-memory fallback's state is reset before/after each test.

`tests/migrations/test_migrations_apply_cleanly_postgres.py` is the only test that needs real infra (`POSTGRES_TEST_DATABASE_URL` env var) and skips cleanly without it. Everything else runs against SQLite/in-memory fallbacks with zero external dependencies — a fresh clone can run the full suite with just `poetry install && pytest`.

### Other backend services worth knowing about

- **`contextual_markers.py`** — merchant-defined "exclude/flag this date range" markers; creating one immediately re-flags already-ingested rows in range, doesn't wait for the next upload.
- **`privacy.py`** (both `routes/` and `services/` — two separate files with the same name, easy to edit only one by mistake) — GDPR export/delete. Export is synchronous and in-request; delete removes transactional data but deliberately keeps the user account, billing history, and login records.
- **`app/utils/email.py`** — Resend HTTP API; if unconfigured, logs to console instead of sending (zero-setup in dev).
- **`app/services/ai_client.py`** — Gemini wrapper (`generate_text`). API key goes in the `x-goog-api-key` header, not a `?key=` query param (avoids the key ending up in proxy/access logs). Retries on timeouts/5xx with linear backoff, fails fast on 4xx.
- **`app/services/encryption.py`** — Fernet field encryption (`encrypt_field`/`decrypt_field`, reversible — TOTP secrets, legacy bank-identifier storage) plus one-way `hash_value` (SHA-256 — account-number hashing/dedup, never reversible). Warns at import time if still on the default key in dev; the hard failure lives in `main.py`'s startup check, not here.
- **`app/services/merchant_provisioning.py`** — auto-provisions a merchant + owner role for any vertical the user doesn't yet have on every `/me`/login call (idempotent). Doesn't backfill for a merchant the user only has an *invited* role in.
- **`app/services/redis_client.py`** — shared Redis facade (locking, TTL'd values, TTL'd counters) with an automatic in-process fallback when Redis is unreachable. The fallback is explicitly **not safe across multiple processes/replicas** — dev/test-only, don't rely on it in a multi-instance deployment.
- **`app/services/upload_staging.py`** — routes staged uploads through the storage abstraction rather than a shared filesystem path (see [Upload pipeline](#upload--ingestion-pipeline) above for why). `read_csv_bytes` tries utf-8 → cp1252 → latin-1 in order.
- **`app/services/fx_rates.py`** — live USD→NGN rate from a free keyless API, cached in `exchange_rates`, hourly Celery-beat sync, fetch-if-stale on demand, hardcoded emergency fallback.

### Backend dependencies

Python `^3.11`, Poetry-managed (`pyproject.toml` + `poetry.lock`), with a generated `requirements.txt` for non-Poetry installs/Docker. Core stack: FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, `aiosqlite` + `psycopg[binary]` (Postgres), Alembic, Celery + Redis, `boto3` (S3), `pandas`/`numpy`/`openpyxl`, `pymupdf` (PDF text extraction), `statsmodels`/`scikit-learn`/`scipy`, `rapidfuzz` (fuzzy column mapping), `pyotp`/`qrcode` (2FA), `python-jose` (JWT), `passlib[bcrypt]`, `httpx`. Dev/test: `ruff`, `black`, `pytest` + `pytest-asyncio`, `moto[s3]`.

---

## Frontend architecture

Root: `frontend/`. React 19 + TanStack Router (file-based) + TanStack Query + Vite + TypeScript (strict).

### Build tooling

- `package.json` scripts: `dev` (vite), `build` (`tsc -b && vite build`), `lint` (eslint), `preview`.
- Routing/data: `@tanstack/react-router`, `@tanstack/router-plugin` (generates `routeTree.gen.ts`), `@tanstack/react-query`.
- Styling: Tailwind CSS v4 (`@tailwindcss/vite`, config lives in `components.json` + CSS, no separate `tailwind.config.*`) **plus** a large hand-written plain-CSS system (`src/styles/index.css`, ~7000 lines, `fi-*`/`upload-*`/`scanwick-*` class names) for the dashboards/upload/landing chrome. shadcn/ui components generated via the `shadcn` CLI.
- Charts: `recharts`. Icons: `lucide-react`. Forms: `react-hook-form` + `zod`. HTTP: `axios`.
- `vite.config.ts`: `tanstackRouter` plugin must run before `@vitejs/plugin-react`; `"@"` aliases to `./src`; `server.allowedHosts: [".trycloudflare.com"]` for dev tunneling.
- `tsconfig`: strict, `noUnusedLocals`/`noUnusedParameters`/`noFallthroughCasesInSwitch` on.
- **`frontend/README.md` is still the generic Vite template README** — no project-specific instructions live there. This doc is the real reference.

### Environment variables

`.env.example`:
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_AUTH_API_BASE_URL=http://localhost:8000
```
Read in `src/lib/env.ts`. In dev, missing values fall back to the localhost defaults above. In a **production build** (`import.meta.env.PROD`), a missing/blank value throws at startup instead of silently defaulting — deliberate fail-fast so a misconfigured deploy doesn't silently point at the wrong API.

### Routing

File-based, under `src/routes/`. Generated tree: `src/routeTree.gen.ts` (auto-generated by the `tanstackRouter` Vite plugin on dev-server-start/build — never hand-edit it, it regenerates from the route files).

- **`__root.tsx`** — runs `ensureAuthBootstrapped()` (memoized) on every route so even public pages get a resolved auth state. Also owns the **Google OAuth callback**: the backend redirects to a bare URL fragment (`#access_token=...`), so this parses `window.location.hash`, stores tokens, fetches `/me`, and navigates to `/upload` — there's no dedicated `/auth/callback` route for this.
- **`_app.tsx`** — the only route that actually gates on auth (`beforeLoad: requireAuth`); wraps `/upload`, `/dashboard`, `/commerce-intelligence`, `/account`, `/notifications`, `/reports`.
- **`_auth.*.tsx`** (login/register/otp/reset/getcode) — `_auth` is a bare naming *prefix*, not a shared layout file; each screen individually calls `requireGuest` in its own `beforeLoad` to bounce already-authenticated users to `/upload`.
- **`accept-invite.tsx`** — deliberately unguarded; branches on auth state internally since both a new and an existing user can land here.
- Public routes: `/`, `/about`, `/blog`, `/blog/$slug`, `/contact`, `/privacy`, `/terms`, `/playground`, `/accept-invite`.

### API client & auth state

`src/lib/api-client.ts` — two axios instances: `apiClient` → `{VITE_API_BASE_URL}` (`/api/v1/*`), `authClient` → `{VITE_AUTH_API_BASE_URL}/api/auth`. Request interceptor attaches `Authorization: Bearer`. Response interceptor: on 401, refreshes the access token once (via a **shared in-flight promise** so concurrent 401s don't race — the backend rotates/deletes the refresh token on every use, so parallel independent refresh calls would log the user out) and retries the original request; on refresh failure, clears tokens and marks unauthenticated.

`src/lib/auth-store.ts` — **plain module-level state + pub/sub**, not React Context or a state library: `{status: "loading"|"authenticated"|"unauthenticated", user}`, subscribed to via `useSyncExternalStore` in `src/hooks/use-auth.ts`.

`src/lib/auth-tokens.ts`: access token lives **in memory only** (cleared on page reload, by design — never written to any JS-readable persistent storage); refresh token lives in a `SameSite=Strict` cookie (`scanwick_refresh_token`, 7-day max-age matching the backend default). Cross-tab logout: a `scanwick_logout_event` localStorage write fires a `storage` event in *other* tabs so they clear their in-memory token immediately instead of limping along on a dead refresh cookie.

`src/lib/auth-bootstrap.ts::ensureAuthBootstrapped()` can't just rely on the interceptor's 401→refresh flow, because FastAPI's `HTTPBearer` returns **403**, not 401, when no `Authorization` header is present at all — so it explicitly checks for the refresh cookie and calls `/me` itself on first load.

### Auth UI flow

Register → OTP verify (`POST /verify-otp`, purpose `"verification"`) → lands on `/account?tab=billing&upgrade=<plan>` if a paid plan was pre-selected on the landing page, else `/upload`. Login → if the response has no tokens, the account has TOTP 2FA enabled, so the UI switches to a second OTP screen and calls `/2fa/verify-login` with the password re-sent alongside the code (a correct TOTP code alone must never be sufficient on its own). A 403 on login means "not yet verified" and redirects to `/otp`. Google OAuth is a full-page redirect to the backend (`window.location.href = {authBaseUrl}/api/auth/google`), completed by `__root.tsx`'s fragment parser described above. 2FA setup/disable, password change, session/login-history management live in the account settings billing tab (`src/features/account/billing/security-*`), not the login flow.

### Feature folders

`src/features/`:

| Folder | Purpose |
|---|---|
| `upload/` | File upload → detect → data-quality-report → (optional) mapping-review → dashboard redirect. See [Upload / mapping UI flow](#upload--mapping-ui-flow). |
| `dashboard/` | The **bank** ("Finance Intelligence") dashboard — 9 sections: financial-summary, income-stability, avg-monthly-balance, cashflow, fraud-risk, loan-readiness, 90-day-forecast, lender-brief, health-playbook. |
| `commerce-intelligence/` | The **ecommerce** dashboard — reduced to a single section (`commerce-dashboard`) after the depth-feature removal; `sections.ts` documents exactly what was cut. |
| `account/` | Settings hub: billing/plan tab, team roles tab, contextual markers tab, workspace settings tab. |
| `reconciliation/` | The cash-gap/data-exclusion report linked from dashboard stat tiles ("↳ reconciliation"). |
| `notifications/` | Alerts/recommendations/team-activity feed. **Currently hardcoded mock data**, not wired to a real backend endpoint. |
| `landing/` | Marketing home page + the shared `chrome.tsx` (header/footer + `useScanwickChrome` theme hook, used app-wide). |
| `blog/` | Static blog listing + post detail. |
| `reports/` | Report library / scheduling / export history UI. **Uses mock data** (`mock-data.ts`), not a real API — don't assume it's live. |
| `intelligence/` | Shared UI kit used by every dashboard-style page — see [Shared components](#shared-components). |
| `contact/`, `legal/`, `errors/`, `playground/` | Static/utility pages. |

### Upload / mapping UI flow

Walking `src/features/upload/index.tsx` (`UploadPage`) end to end:

1. Pick a format tab (PDF / CSV / Mono). CSV shows an **Analyzer type** picker (`AnalyzerType = "finance" | "commerce"`, the frontend's naming — mapped to the backend's `"bank" | "ecommerce"` via `analyzerTypeToBackend`/`backendToAnalyzerType`).
2. On file selection, client-side validates extension/size (10MB max), then for CSVs calls `POST /upload/detect` first: if confidence ≥ 0.4, the *detected* vertical overrides whatever tab the user had selected (so the dashboard they land on afterward matches what was actually uploaded, not a stale tab choice) — a low-confidence or failed detection silently falls back to the manual selection.
3. Dispatches the real upload (`POST /bank/upload/pdf` or `POST /upload/csv`).
4. If the CSV response is `status: "needs_mapping"`, renders `MappingReviewPage` and pauses — the user confirms/corrects column mappings against a hardcoded canonical-field list per vertical (`CANONICAL_FIELDS.ecommerce`/`.bank` in `components/mapping-review.tsx`, **manually kept in sync** with the backend's `column_mapping.py::CANONICAL_SYNONYMS** — if you add a canonical field on the backend, mirror it here too), plus any free-text value questions. On confirm, calls `POST /mapping/confirm` and resumes.
5. Otherwise (or after mapping confirm) polls `GET /upload/{id}/quality-report` every 2s (120s timeout) until ready, then shows `DataQualityReportPage` (pass/fail/warning checks, disabled-feature callouts, mapping summary).
6. "Proceed" navigates to `analyzerTypeToDashboardRoute[analyzerType]` — using the *effective* (possibly auto-detected) analyzer type, not necessarily the tab the user originally clicked.

The Mono panel takes a raw `mono_account_id` text input and calls `POST /bank/upload/mono` directly — the real Mono Connect widget isn't integrated yet, and this path is synchronous with no polling (no durable `Upload` row, per an explicit in-code comment referencing `docs/INTEGRATION_PLAN.md` Phase 3).

### Plan/billing UI

`src/features/account/billing/payments-api.ts` — React Query hooks: `useSubscription`, `useBillingHistory`, `useStartCheckout` (full-page redirect to the provider's hosted checkout), `useVerifyPayment`, `usePlanPermissions` (fetches the backend's `/plans/permissions` matrix, `staleTime: 1 hour` — it's the same for every user), `getFeatureAccess(matrix, key, tier)`, `useCancelSubscription`.

**Locked-feature pattern**, used identically in `dashboard/index.tsx` and `commerce-intelligence/index.tsx`: for the active section, `getFeatureAccess(...)` decides between a full-page `PlanUpgradeLockedPage` (level `none`, links to `/account?tab=billing`), an inline `LimitedAccessBanner` above still-visible truncated content (level `limited`, shows the backend-provided `detail` string), or normal rendering (`full`). Sidebar nav items show a small lock icon for `none`-level sections but stay clickable (clicking reveals the locked-page state rather than being disabled outright).

### Shared components

`src/features/intelligence/components/`:
- **`shared.tsx`** — the common visual vocabulary for every dashboard: `PageHead`, `Card`, `StatTile`, `Legend`, `BarList`, `ItemList`, `ProgressBar`, `LockedOverlay`, `LockedPageState`, `LimitedAccessBanner`, `PlanUpgradeLockedPage`, `Badge`/`TrendBadge`, `RepAvatar`, a generic column/row-driven **`Table`**, `QuotaBullet`, `LikelihoodDot`.
- **`sidebar.tsx`** (`IntelligenceSidebar`) and **`topbar.tsx`** (`IntelligenceTopbar`) — both `Dashboard` (bank) and `CommerceIntelligence` (ecommerce) compose identically from these plus their own `sections.ts` and `pages/*.tsx`.

`src/features/upload/components/topbar.tsx` (`AppTopbar`) is a separate, simpler topbar reused by Upload and Account — not part of the `intelligence/` kit.

### Theming

**Two theming mechanisms exist; only one is actually wired up** — worth knowing before you go looking for the "real" one:
- **`useScanwickChrome()`** (`src/features/landing/chrome.tsx`) — the live one. `localStorage["scanwick-theme"]`, values `"dark" | "light"` only (no `"system"`), applied as a `.theme-light` override class on a `scanwick-page` wrapper div (dark is the unmarked default). Used by every real page.
- **`ThemeProvider`/`useTheme`** (`src/context/theme-provider.tsx`) — a more conventional shadcn-style context supporting `system` mode, cookie-persisted (`vite-ui-theme`), toggling classes on `<html>`. **Never mounted** anywhere (not in `main.tsx` or `__root.tsx`) — it and its consumers (`src/components/theme-toggle.tsx`, `sonner.tsx`'s `useTheme()` call) are effectively dead code today. Don't wire new features to this one without first mounting the provider.

### Frontend testing & linting

**No automated tests exist on the frontend** — no `*.test.*`/`*.spec.*` files, no test runner configured, no `test` script. Linting is ESLint (flat config, `npm run lint`) with Prettier configured for formatting (`prettier-plugin-tailwindcss` for class sorting) but no `format`/`format:check` script wired up in `package.json` — the root `pnpm format` script (`prettier --write "src/**/*.{ts,tsx,css,md}"`) covers this instead.

---

## Cross-cutting conventions

A few patterns show up repeatedly across both codebases — recognizing them will save time reading unfamiliar code:

- **`(error, value)` tuple returns** — both `rbac.check_role` (backend) and `entitlements.check_feature_access` return `(error_or_None, value_or_None)` rather than raising, so a route can decide exactly how to shape its response around a denial (e.g. redact fields for `LIMITED` access instead of a flat 403). Frontend code (`getFeatureAccess`) mirrors this same shape.
- **Historical FX rates, never "today's" rate** — both ingestion paths convert currency using the rate *as of the transaction/order date*, not the rate at ingestion time. If you're adding a new money field, follow this, not a live lookup.
- **Deterministic surrogate IDs** — where a source system doesn't supply a stable natural key (ecommerce orders with no order ID, customers identified only by email), the ingestion code generates a **deterministic** hash/UUID5 rather than a random one, so re-uploading the same file doesn't create duplicates.
- **Storage abstraction, not a filesystem path** — anything file-related (uploads, avatars, exports) goes through `app/services/storage.py`, because the API and Celery worker are independently-deployed services in production with no shared disk. Never hardcode a local path for anything that a Celery task also needs to read.
- **Idempotency keys for money-adjacent side effects** — webhook-driven billing state changes are keyed on `PaymentTransaction.provider_reference` so a redelivered webhook (or a webhook racing a manual `/verify` call) can't double-apply a charge.
- **Two-vertical model is load-bearing, not incidental** — `Vertical.ecommerce`/`Vertical.bank`, `EcommerceRole`/`BankRole`, and the frontend's parallel `dashboard`/`commerce-intelligence` folders all assume exactly two verticals. If a third vertical is ever reintroduced, expect to touch RBAC, plan_permissions, column_mapping, dataset_detection, and the frontend upload flow's `AnalyzerType` union — not just add a new route file.

---

## Known gaps & things that look wired but aren't

Flagging these explicitly so you don't lose time assuming they're either broken-and-need-fixing or fully-functional when they're neither:

- **`frontend/README.md`** is the unmodified Vite template — no real setup instructions live there (use this doc instead).
- **No `.env.example` committed in `backend/`** — the [Configuration](#configuration) table above is the closest equivalent.
- **`src/context/theme-provider.tsx`** (`ThemeProvider`/`useTheme`) is unmounted, dead code — see [Theming](#theming).
- **`src/features/notifications/index.tsx`** renders hardcoded mock notification data, not a real feed.
- **`src/features/reports/mock-data.ts`** backs the entire Reports feature with static mock data, not a real API.
- **No automated frontend tests exist** at all.
- **`ingest_mono_account_task`** (`app/services/mono_ingestion.py`) is a registered Celery task that nothing actually calls — `routes/bank.py`'s `/upload/mono` handler invokes the plain async function directly instead. Mono ingestion runs synchronously in-request today, not as a background job.
- **The legacy `/api/analyze` route and `app/utils/analyzer.py`** are intentionally still live (a deliberate "leave it alone" decision made during the Section 4 cleanup, not an oversight) — don't delete without checking history/asking first.

---

## History: what got removed

Earlier in this project's life, a **third vertical — "sales"** (a CRM pipeline analyzer: deals, stage transitions, win-probability forecasting, postmortem reports, rep leaderboards) existed end to end, alongside several **non-core depth features** on the two surviving verticals:
- Ecommerce: RFM segmentation, churn prediction, Holt-Winters revenue forecasting, inventory forecasting, SKU matrix, ad-kill-switch, AI commerce playbook, dead-stock/profit-leak detection, return forensics, an Olist-dataset adapter.
- Bank: customer segmentation, revenue patterns.

All of it — backend routes/services/models/migrations/tests, and the corresponding frontend `sales-intelligence` module + ecommerce/bank sub-pages — was **deleted in full** (not disabled/hidden) per an explicit "don't leave dormant runtime code in place" scope decision. If you find a reference to `SalesRole`, `Deal`, `DealDataSource`, `sales_router`, `ecommerce_rfm`, `bank_customer_segmentation`, or similar in an old doc, comment, or git history — it's gone, not just undocumented. `issues/DEVELOPER_SCOPE_VERIFIED_IMPLEMENTATION_GUIDE.md` (Section 4) and `issues/FIX_PACK_ISSUES.md` in this repo have the full rationale and step-by-step record of that removal, plus a handful of small, unrelated correctness/security fixes (production secret-key guard, shorter access-token TTL, DB connection pooling, moving the Gemini API key out of the URL query string, Celery task timeouts) done in the same pass.

---

## Where else to look

- `docs/SYSTEM_DOCUMENTATION.md` and `backend/docs/SYSTEM_DOCUMENTATION.md` — historical, append-only build logs from the original build-out. Useful for understanding *why* something was built a certain way at a point in time; **not** a reliable source for current state (both predate RBAC, billing, reconciliation, and the Section 4 removal — large parts are now wrong if read as "what exists today").
- `docs/INTEGRATION_PLAN.md` — forward-looking integration phases (e.g. the real Mono Connect widget is still Phase 3/not done — see [Known gaps](#known-gaps--things-that-look-wired-but-arent)).
- `docs/BUG_AUDIT.md`, `docs/ACTIVE_RESOLUTION_DOCUMENTS.md`, `issues/AUDIT_ISSUES.md`, `issues/FIX_PACK_ISSUES.md`, `issues/DEVELOPER_SCOPE_VERIFIED_IMPLEMENTATION_GUIDE.md` — point-in-time audits and their resolutions; each documents a specific defect/scope decision and its fix, with dates. Good for "why does this code look weird" archaeology.
- `testing/` — manual QA logs (not automated tests) per vertical.
- `backend/Shakir_Build_Prompts.md` / `backend/Shoaib_Build_Prompts.md` — the two original developers' build-task logs.
