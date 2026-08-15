# Frontend ↔ Backend Integration Plan

Status snapshot when this was written: 2026-07-16, on `dev-backend`.

## Progress log

Chronological record of what's actually been done, updated as each step completes. This is the source of truth for "where are we" — check here before re-running a step.

### 2026-07-16 — Phase 0: repo cleanup + branch setup

- **Commit `023f55a`** (on `dev-backend`): untracked `backend/Python/` (~181MB embedded Python runtime) and `backend/app.db` (~81MB dev SQLite file) via `git rm -r --cached`. Added both to `.gitignore`. Files remain on disk; only removed from git tracking going forward. History still contains them (not rewritten — that's a separate, undecided call per §1).
- Created branch **`integration/frontend-backend`** from `dev-backend`.
- **Commit `f162ddd`**: merged `dev-frontend` into `integration/frontend-backend`. Exactly one conflict as predicted — `pnpm-lock.yaml` — resolved by deleting it and regenerating with `pnpm install --lockfile-only` (pnpm 10.33.0, workspace-aware, 3 projects resolved cleanly).
- **Discovered mid-merge and not in the original plan**: `frontend/.env` was tracked in git (coming in from `dev-frontend`), despite root `.gitignore` already listing `.env` — the rule pre-dated the file so it never took effect. Contents were harmless (`VITE_API_BASE_URL=http://localhost:9092/api/v1`, `VITE_AUTH_API_BASE_URL=http://localhost:9092` — no secrets), but tracking it is the same class of problem as the backend binaries. Also found `frontend/.tanstack/tmp/` tracked — a generated TanStack Router build-cache directory.
- **Commit `3655015`**: untracked `frontend/.env` and `frontend/.tanstack/tmp/`. Added `frontend/.tanstack/` to `.gitignore`. Removed `.env.example` from the ignore list (it was ignored before, which meant Phase 1's planned `.env.example` template would never actually get committed — example files with placeholder values are meant to be checked in). Created `frontend/.env.example` pointing at `http://localhost:8000` — this matches the backend's own default (`backend/app/config.py`'s `backend_base_url` and the CORS allowlist in `main.py`), **not** the `9092` value found in the removed `.env`. That port mismatch is unexplained — flag it if local dev breaks pointing at 8000; someone may have been intentionally running the backend on a custom port.
- Net result: `integration/frontend-backend` now has the full frontend UI, the full backend API, clean git status, and a regenerated lockfile. Nothing has touched `main` or `dev-backend`'s remote.

**Not yet done**: Phase 1 onward (API client wiring) — still mock data on the frontend, no real requests hitting the backend yet.

### 2026-07-16 — confirmed: `staging` branch is unused

Confirmed with the team: `origin/staging` isn't wired to any deploy pipeline yet. §8.3 stands as written — PR straight from `integration/frontend-backend` into `main` once Phases 1–8 are verified, no detour through `staging`.

### 2026-07-16 — Phase 1: API client infrastructure

No component/feature wiring yet — this is only the shared plumbing, per §4 Phase 1.

- **Step 1.1** — `frontend/src/lib/env.ts`: reads `VITE_API_BASE_URL` / `VITE_AUTH_API_BASE_URL` via `import.meta.env`, with the same localhost defaults as `.env.example`. Added an `ImportMetaEnv` augmentation in `frontend/src/vite-env.d.ts` so these keys are typed instead of falling back to `any`.
- **Step 1.4** — `frontend/src/lib/auth-tokens.ts`: access token kept in a module-level variable only (memory, cleared on reload — never written to any persistent storage). Refresh token persisted via a cookie (`scanwick_refresh_token`, 7-day max-age matching the backend's `refresh_token_expire_days` default) since the backend issues it in the JSON body rather than setting an httpOnly cookie itself — this is the least-bad option available without a backend change, not a fully XSS-proof one; noted plainly in the file's comment. Extended `frontend/src/lib/cookies.ts`'s `setCookie` with optional `sameSite`/`secure` params (backward compatible — existing theme-provider caller is unaffected) and used `SameSite=Strict` for the refresh cookie specifically.
- **Step 1.2** — `frontend/src/lib/api-client.ts`: two axios instances — `apiClient` (baseURL = `VITE_API_BASE_URL`, i.e. `/api/v1/*` for sales/ecommerce/bank/reconciliation/uploads/analyze) and `authClient` (baseURL = `VITE_AUTH_API_BASE_URL` + `/api/auth`, since auth routes live directly under the API root, not under `/api/v1`). Both attach `Authorization: Bearer <access token>` via a request interceptor and, on a 401, attempt exactly one silent refresh (via a plain `axios.post` outside the intercepted client, to avoid recursing if the refresh itself fails) before retrying the original request once. All other errors route through the existing `handle-server-error.ts` → `sonner` toast.
- **Step 1.3** — `frontend/src/main.tsx`: `QueryClientProvider` already existed; added `staleTime: 60s` and `retry: 1` for queries, `retry: false` for mutations, as sane defaults.
- **Verification**: ran `npx tsc -b --noEmit` in `frontend/`. Zero errors in any file touched this phase. The only errors reported are pre-existing unused-variable warnings in `dev-frontend`'s stub auth pages (`login/index.tsx`, `register/index.tsx`, `reset-password/index.tsx`, `AlertBox.tsx`, `FormField.tsx`) — untouched by this phase, will be resolved naturally in Phase 2 when those stubs get wired to real submit handlers.

**Not yet done**: Phase 2 (auth wiring) — the auth pages still have stub `onSubmit` handlers with a `// On submit logic` comment and no real network calls.

### 2026-07-17 — Phase 2: Auth wiring

Bug found and fixed before starting feature work — **commit `f935c51`**: the Phase 1 interceptor only kept the refreshed access token in memory and never persisted the backend's rotated refresh token, so the cookie held an already-consumed token after the first refresh. It also didn't dedupe concurrent 401s, so several parallel requests failing at once (e.g. a dashboard's parallel queries) would each call `/refresh` independently and the backend's refresh-token rotation would cause all but the first to fail, wrongly logging the user out. Fixed by funneling all refreshes through one shared in-flight promise (`refreshAccessToken()`, exported from `api-client.ts`) that persists both returned tokens.

Two product decisions were needed before wiring could proceed (asked and answered, see below), plus one structural discovery mid-work:

- **Registration email verification** had no screen at all wired to it — decided: reuse the OTP-code screen (previously part of the password-reset feature) for registration verification instead.
- **Password reset** decided: match the backend's actual mechanism (emailed link + token) and drop the 4-digit code screen the frontend had built for it — the backend never had an OTP-code endpoint for password reset in the first place.
- **Structural discovery**: `/_app.tsx` (Header/Footer layout) wasn't actually the parent of any real page — `dashboard`, `upload`, `account`, `commerce-intelligence`, `sales-intelligence`, `notifications` were all parented directly to the root route (only `/reports` nested correctly). Every "logged in" page was rendering with no header/nav/footer, and there was nowhere to gate them behind auth. Decided: fix now, as part of this phase.

Work done, commit by commit:

- **`7825923`** — Moved those six route directories into `routes/_app/` (`git mv`, preserving history) and regenerated `frontend/src/routeTree.gen.ts` via `npx vite build` (the TanStack Router vite plugin owns that file; hand-editing it isn't safe). Added the session/auth infrastructure: `lib/auth-store.ts` (external store, no new dependency — Zustand isn't installed, so this uses `useSyncExternalStore` directly), `hooks/use-auth.ts`, `lib/auth-bootstrap.ts` (on load: refresh from the cookie if present, then `GET /me`, memoized so every route's `beforeLoad` can await it once), and `lib/auth-guards.ts` (`requireGuest` / `requireAuth`). Wired `requireAuth` into `/_app`'s `beforeLoad` and `requireGuest` into `/_auth/getcode`.
- **`436fd5c`** — Register now calls `POST /api/auth/register` and navigates to `/otp?email=...` on success. Moved the OTP screen out of the reset-password feature into its own `features/auth/otp/`, wired to `POST /api/auth/verify-otp` (`purpose=verification`) and `POST /api/auth/resend-otp`; on success it stores the issued tokens (verification also logs the user in server-side) and navigates to `/dashboard`. `CardLayout` gained an optional `onFooterLinkClick` so "Resend" can trigger a call instead of always being a nav link. `requireGuest` added to `/_auth/register` and `/_auth/otp` (the latter also validates an `email` search param).
- **`362af96`** — Fixed a real bug: login's `<form>` never had `onSubmit={form.handleSubmit(onSubmit)}` wired at all — clicking submit just reloaded the page. Wired to `POST /api/auth/login`: success stores tokens + navigates to `redirectTo` (from a new `redirect` search param on `/login`) or `/dashboard`; a 403 (unverified account) redirects to `/otp` instead of showing a dead-end error; 401 shows "Invalid email or password." Header's "Log out" menu item had no handler — added `lib/auth-actions.ts`'s `logout()` (clears local state first, then best-effort revokes the refresh token server-side) and wired it. `AuthFooter`'s Google button was a no-op stub — wired to redirect to `GET /api/auth/google`.
- **`1e1e23d`** — `EmailCard` now calls `POST /api/auth/forgot-password`; `ResetCard` takes a `token` prop (from `/reset`'s `?token=` search param) and calls `POST /api/auth/reset-password`. Also fixed a mismatch found in the same area: the backend was emailing a reset link to `/reset-password?token=...` but the actual frontend route is `/reset` — every real password-reset email would have 404'd. Fixed in `backend/app/routes/auth.py`.
- **`37922f8`** — Google OAuth's callback redirects to `${frontend_url}/#access_token=...&refresh_token=...` — a URL fragment on whatever page the browser lands on, not a dedicated route — so it's handled once in `routes/__root.tsx` on mount: parses the hash, strips it immediately (never lingers in the visible URL/history), stores tokens, fetches `/me`, navigates to `/dashboard`.

**Verification**: `npx tsc -b --noEmit` and `npx vite build` both clean after every commit. Remaining typecheck errors are the same three pre-existing unused-import warnings in `AlertBox.tsx`/`FormField.tsx` from `dev-frontend` — untouched by this work, unrelated to auth.

**Not yet done**: Phase 3 onward (uploads/analyze, and the three verticals) — no non-auth endpoint is wired to real data yet; dashboards still render from `mock-data.tsx`. Also not done: actually running the app end-to-end in a browser against a live backend (this phase was verified via typecheck/build only, not a manual click-through) — worth doing before calling Phase 2 fully done.

### 2026-07-17 — Phase 3: Uploads + Analyze — turned into real backend feature work

This phase went well beyond "wire an existing endpoint" — the endpoints didn't exist. Two rounds of stop-and-ask happened before writing code; both are load-bearing decisions, not implementation details.

**Discovery**: `POST /api/analyze` (the only working upload endpoint) is a stateless, disconnected feature — no `Upload` row, no `account_id`/`merchant_id`, no relationship to the dashboards. The real vertical dashboards (bank/ecommerce/sales) read from already-populated tables (`Account`/`BankTransaction`, `Order`, `Deal`) keyed by a caller-supplied `merchant_id`/`account_id` — bank.py's own code literally comments it as `"Placeholder until real auth/RBAC derives this from the session."` Four ingestion *services* clearly built for this (`bank_pdf_ingestion.py`, `mono_ingestion.py`, `ecommerce_olist_adapter.py`, `sales_ingestion.py`) existed but were **never called from any route** — only from tests. `upload_staging.py`'s own docstring confirmed the gap: *"there's still no `POST /api/v1/upload/csv` endpoint... Replace once that upload endpoint exists."*

**Decision 1 (asked, answered "build the missing routes now")**: build real HTTP endpoints around the existing, already-tested ingestion services rather than wiring the frontend to the disconnected `/api/analyze`, or deferring with a hardcoded `account_id`.

**Decision 2 (asked mid-implementation, answered "auto-provision on registration")**: every one of these routes needs a `merchant_id`, and nothing anywhere — not registration, not Google login, no onboarding step — ever created a `UserMerchantRole` row for a new user. Every account was permanently locked out of all three verticals. Decided: auto-provision one `merchant_id` + owner-tier `UserMerchantRole` rows (ecommerce/sales/bank) the moment an account activates, rather than adding a manual UUID field to the UI or deferring the whole phase.

**Backend work, commit by commit** (all on `integration/frontend-backend`):
- **`223b95c`** — untracked 11 leftover `.pyc` files under `backend/app/` (same class of issue as Phase 0's cleanup — predate the `__pycache__/` gitignore rule).
- **`51a1a54`** — regenerated `poetry.lock`: `poetry install` was failing outright (lock was missing statsmodels/scikit-learn/scipy/openpyxl etc. that `pyproject.toml` already declared and code already imports). Needed to run the test suite at all; flagged as its own commit since it's a real dependency-version change unrelated to the ingestion work.
- **`006c99e`** — `POST /api/v1/upload/csv`: stages the file at the existing `/tmp/scanwick_uploads/` convention, creates the `Upload` row (`status=processing`), dispatches the matching already-built Celery task (`ingest_ecommerce_csv` / `ingest_sales_csv` / `ingest_bank_csv`) — no changes to the ingestion services themselves. RBAC-gated with new upload-specific role sets, tighter than each vertical's read roles. Also fixed a real security gap in the same file: `GET /api/v1/upload/{upload_id}/quality-report` had **no auth at all** — any caller who guessed a UUID could read another merchant's data-quality report. Added the same `check_any_role` pattern `reconciliation.py` already uses.
- **`bf91167`** — `POST /api/v1/bank/upload/pdf` (stages + dispatches `ingest_bank_pdf`, since OCR is slow) and `POST /api/v1/bank/upload/mono` (synchronous — Mono is a live API call, not a file; guards on `mono_secret_key` being configured, translates `MonoAPIError` to 502). Documented plainly that the Mono path can't produce a durable `Upload`/quality-report row today (`ingest_mono_account` has no real UUID to key one on) — not silently swallowed.
- **`55a0db0`** — `POST /api/v1/ecommerce/upload/olist`: Olist's three-table CSV export (orders/items/payments) doesn't fit the single-file `upload/csv` path, so this takes three files and calls `ingest_olist_dataset` directly (no Celery task exists for this adapter); writes its own `Upload` row afterwards for quality-report parity, since that service doesn't touch the `uploads` table itself.
- **`84d7a8a`** — `ensure_merchant_provisioned()` (idempotent): creates the merchant_id + three `UserMerchantRole` rows the first time it runs for a user. Hooked into email-verification completion and the Google OAuth callback (the two paths that actually activate an account), and also into `GET /api/auth/me` so it backfills `merchant_id` for any account that predates this change. `UserOut` gained a `merchant_id` field.
- All four backend commits include tests (new route tests + `ensure_merchant_provisioned` unit tests); full suite run after each: **624 passed, 2 skipped** (skips are pre-existing, unrelated). Excluded from every run, confirmed pre-existing and environment-only (no Tesseract binary, no local Olist dataset files, no live Redis — not caused by this work): `test_bank_pdf_ingestion.py`, `test_bank_pdf_ingestion_task.py`, `test_ecommerce_olist_adapter.py::test_ingest_real_olist_files_smoke_test`, `test_ping_task.py`.

**Frontend work — commit `7dc0101`**:
- `features/upload/uploads-api.ts` (new): thin client for the three upload endpoints, a poller for the two staged/Celery-backed paths (bank PDF/CSV, ecommerce/sales CSV) against their quality-report endpoint, and `normalizeQualityReport()` mapping either quality-report shape (generic vs bank-specific) into what the existing DQR UI components expect.
- `features/upload/index.tsx`: `acceptFile` now actually uploads and polls instead of running a timed fake-progress animation (the old `ProcessingPanel` faked "Parsing → Validating → Normalizing → Running analysis" on a `setInterval`, disconnected from anything real). `merchant_id` comes from the session (`auth-store.ts`'s new field, backed by the `/me` change).
- `features/upload/components/data-quality-report.tsx`: previously derived its entire "clean/warning/failed" state from **substrings in the filename** (`"_warn.pdf"`, `"_fail.pdf"` — a demo convention) and fabricated row counts from a hash of the filename. Now takes the real normalized report and displays real `rows_parsed`/`rows_rejected`/`date_range`/`warnings`/`disabled_features`.
- Mono: no real Connect widget (third-party JS SDK) is integrated anywhere in this codebase, and there's no public/client key configured for one. Rather than fake a successful connection (as the mock did — a hardcoded "Lumio Living • ****4821"), the Mono panel now takes a manual Mono account-id text input and calls the real, working backend endpoint. Clearly labeled in the UI and in code comments as a stand-in for the real widget, not the final UX.

**Verification**: `npx tsc -b --noEmit` and `npx vite build` clean (same 3 pre-existing unrelated warnings as every prior phase).

**Not yet done**:
- Manual browser click-through against a live backend + Celery worker + Redis — none of those are running in this environment this session, so the full upload → poll → dashboard flow has only been verified via automated tests (backend) and typecheck/build (frontend), not observed end-to-end. Worth doing before calling this phase fully done.
- Real Mono Connect widget integration (needs a Mono publishable key + their JS SDK — currently just `mono_secret_key` server-side).
- Sales/ecommerce CSV uploads only support `generic_csv` as the source from the UI today — there's no per-platform picker (Shopify/HubSpot/Salesforce/etc.) even though the backend supports those `OrderDataSource`/`DealDataSource` values.
- Phase 4/5/6 (sales/ecommerce/bank dashboard, diagnostic, predictive, AI endpoints) — still on mock data.

### 2026-07-18 — Phase 4: Sales vertical wiring

Unlike Phase 3, `sales.py`'s 11 GET endpoints + capture-loss-reason POST already existed, fully built and tested — this phase was real wiring, not backend feature work. No backend files changed at all this phase.

**What was there before**: every page in `features/sales-intelligence/` (15 of them) was 100% mock — `Grep` for `useQuery|axios|apiClient` across the whole feature came back empty. All data came from a single `mock-data.ts`.

**Decision needed (asked, answered "strip to real data only")**: comparing the real response shapes (researched via an Explore agent covering the whole route file + service functions) against what the mock pages rendered surfaced a broad gap — most pages had widgets with no backing data *at all*, not just unwired ones. Concepts like quota targets, month-over-month trend, customer concentration, discount-per-rep tracking, competitor mentions, and per-deal win-likelihood scoring don't exist anywhere in the schema — there was nothing to wire them to. Decided: every widget shows only what the backend actually returns; widgets/pages with no real data source are removed, not left showing stale mock numbers next to real ones.

**Commit `13ea05b`** — everything in one commit (the pieces are too interdependent to split meaningfully: `index.tsx`/`sections.ts` don't work without all pages wired at once):
- `sales-api.ts` (new): typed react-query hooks for all 11 GET endpoints + the capture-loss-reason mutation. `merchant_id` comes from the session (the field added in Phase 3).
- **Removed entirely** (deleted, not hidden): `win-loss-patterns.tsx`, `discount-erosion.tsx`, `competitor-intelligence.tsx`, `hygiene-sentinel.tsx`, and `mock-data.ts`. No backend computation exists for any of what these rendered.
- **Trimmed to real data**: Pipeline Dashboard lost "period over period," the monthly closed-won trend chart, quota attainment, and the revenue-concentration banner (kept: pipeline-by-stage, rep-leaderboard, real totals). Confidence Forecast lost the fabricated monthly time-series chart with CI bands and the "pipeline coverage 2.6×" card (kept: per-deal forecasts, real confidence rating/explanation/factors). Win DNA lost the per-deal win-likelihood table — the real endpoint gives an aggregate profile (top channels/reps, avg deal value/age), not per-deal scoring. Rep Trajectory's "Prior 60-day" column was actually wrong against the real API (the real second window is a prior *30*-day window, not 60) — fixed to match. Stage Velocity / Stagnation Alerts / Slippage Alerts tables dropped deal-name/rep/value columns the backend doesn't return (those endpoints only give `deal_id`, no joined-back name/owner/value) — display `deal_id` truncated instead. Quarter Post-Mortem lost almost everything (forecast-vs-actual, slippage cost, AI summary paragraph) — the real endpoint only returns whether a report was generated plus a PDF link/dates; the rich analysis lives inside the PDF itself, not exposed as JSON.
- **Loss Capture rebuilt from scratch**: previously a static, non-functional preview (hardcoded deal, chips with no `onClick`, buttons with no handler) of what an in-app/email notification would look like. Now a real form calling the real endpoint. No deal-listing endpoint exists yet, so it takes a `deal_id` directly (manual input, clearly labeled) rather than browsing a list — same "manual input as an honest stand-in" pattern as Phase 3's Mono account-id field.
- Locked/disabled states (Stage Velocity, Slippage, Win DNA) now come from the real response (`data === null` + `meta.disabled_features`, or Win DNA's own `.disabled` flag) instead of a hardcoded `locked={false}` prop that never reflected anything real.

**Verification**: `npx tsc -b --noEmit` and `npx vite build` clean (same 3 pre-existing unrelated warnings). No backend changes, so no pytest run.

**Not yet done**: manual browser click-through (same caveat as every prior phase — no live backend/Celery running this session). Phase 5/6 (ecommerce, bank) — still on mock data.

### 2026-07-18 — Phase 5: Commerce (ecommerce) vertical wiring

Same pattern as Phase 4 — `ecommerce.py`'s endpoints already existed fully built/tested, so this was wiring, not new backend work, except for the ad-kill-switch action UI (see below). No backend files changed this phase.

**Structural difference from Sales worth noting**: this feature had almost no real per-section UI to begin with — only `commerce-dashboard.tsx` had bespoke layout. The other 12 sidebar sections all rendered through a single generic `commerce-detail.tsx` template: a hardcoded lookup table of fake numbers under four generic labels ("At risk" / "Estimated impact" / "Active signals" / "Recommended actions") that didn't meaningfully vary per section, a fixed 3-row table (same 3 fake products for every section, not section-specific), and a non-functional "Review action" button. So this phase involved more from-scratch page-building than Phase 4's replace-the-mock-values work.

**Commit `1d10c41`** — one commit, same reasoning as Phase 4 (interdependent pieces):
- `ecommerce-api.ts` (new): typed react-query hooks for `dashboard/summary`, `dashboard/revenue`, `diagnostic/profit-leaks`, `diagnostic/dead-stock`, `diagnostic/return-forensics`, `predictive/inventory-forecast`, `predictive/rfm-segments`, `predictive/churn-risk`, `ai/playbook`, plus mutations for both ad-kill-switch POST endpoints.
- **Removed entirely** (deleted `commerce-detail.tsx` and 4 of its 12 sections): `retention-engine`, `discount-impact`, `channel-performance`, `cohort-retention-grid`. No discount-campaign, channel-aggregation, or cohort-retention computation exists anywhere in the ecommerce schema — same "strip to real data only" policy as Phase 4.
- **Dashboard trimmed to real data**: removed the SKU-matrix box (purely decorative, zero real rendering logic to begin with), the discount-impact BarList, the revenue-contribution treemap (labeled with fabricated product names — `product_name` is `null` in *every* backend response across this whole vertical; only `sku` codes are real), and the channel-performance table (no channel-aggregation endpoint exists). Kept/added: real gross/net revenue + change%, monthly trend chart, and a gap breakdown (returns/discounts/shipping/processing/ad_spend).
- **Added a section that didn't exist**: Dead Stock. `GET /diagnostic/dead-stock` was already fully built server-side with zero frontend representation — added `dead-stock.tsx`, matching the original Phase 5 plan (§4) which named it explicitly.
- **Built from scratch, not just rewired**: Profit Leak Detection, Unit Margin Attribution (same underlying `diagnostic/profit-leaks` data, viewed two ways — SKU list vs. per-SKU cost-driver breakdown), Return Forensics, Inventory Forecast, RFM Segmentation, Churn Prediction, AI Commerce Playbook — each now has its own bespoke layout instead of the generic template. Locked/disabled states (profit-leaks, sku-matrix's underlying COGS-coverage gate, churn's `insufficient_data`) come from real `meta.disabled_features`/response flags.
- **Ad-Kill Switch had no UI at all** beyond the generic template — no configure form, no pause button, nothing wired to either POST endpoint. Built a real one: a mode/threshold configure form and a manual campaign-pause form, both calling the real endpoints. No GET endpoint exists to list current campaign spend/performance (confirmed via the backend's own docstrings — no campaign-performance table exists), so there's no "what to pause" browser yet — stated plainly in the page description rather than faked.

**Verification**: `npx tsc -b --noEmit` and `npx vite build` clean (same 3 pre-existing unrelated warnings). No backend changes, so no pytest run.

**Not yet done**: manual browser click-through (same caveat as every prior phase). Phase 6 (bank) — still on mock data. A GET endpoint for campaign-level ad performance (to make Ad-Kill Switch's "what to pause" decision real instead of requiring the operator to already know which campaign) would need new backend work — noted, not built.

### 2026-07-18 — Phase 6: Finance (Bank) vertical wiring

Confirmed `features/dashboard/` (routed at `/_app/dashboard/`) is the bank vertical, not a generic app dashboard — its existing pages (income-stability, cashflow-analysis, fraud-risk, avg-monthly-balance) matched `bank.py`'s endpoints 1:1. Zero `useQuery`/axios calls anywhere beforehand, same starting point as every prior vertical.

**Real blocker, fixed first — commit `f28fb82`**: every one of the 11 bank read endpoints requires an `account_id`, and nothing in the backend ever let a caller discover one. `Account.id` was only ever surfaced synchronously from the Mono ingestion response; the PDF/CSV ingestion paths (202 Accepted + Celery) never exposed the resulting account_id anywhere — not the immediate response, not the quality-report endpoint, nothing. Without this, no bank page could function regardless of frontend wiring — not a strip-vs-keep judgment call, just missing plumbing (same category as Phase 3's merchant_id gap). Added `GET /api/v1/bank/accounts?merchant_id=...`, same RBAC pattern as every other route in the file (`check_role` against `Vertical.bank`, `READ_ROLES`). 5 new tests; full suite after: 629 passed, 2 skipped (same pre-existing skips as every prior phase).

**Commit `001dc9f`** (frontend):
- `bank-api.ts` (new): hooks for all 11 read endpoints, keyed by `account_id` not `merchant_id` (bank's own RBAC convention — `Account.user_id` is the merchant scope). `index.tsx` gained an account picker (shown only when a merchant has more than one ingested account), driving every page's `account_id`.
- **Structural win over Sales/Commerce**: `bank.py` already had 6 of 11 sections' worth of fully-built GET endpoints sitting behind `PlaceholderPage` with zero page component at all — `diagnostic/customer-segmentation`, `diagnostic/revenue-patterns`, `predictive/loan-readiness`, `predictive/cashflow-forecast`, `ai/lender-brief`, `ai/financial-health-playbook`. Built all six from scratch (`customer-segmentation.tsx`, `revenue-pattern.tsx`, `loan-readiness.tsx`, `cashflow-forecast.tsx`, `lender-brief.tsx`, `health-playbook.tsx`). Removed the redundant `statement-integrity` section — its only data (`statement_integrity`) already ships as a sub-object of `predictive/fraud-risk` and is shown on the Fraud Risk page; a standalone page would just duplicate it.
- **Strip-to-real, applied to the 5 existing pages**: removed the date-gap warning banner, min/max/average-daily-balance and overdraft-months stat tiles, and every "running balance" daily-series chart (Financial Summary, Avg Monthly Balance) — no endpoint on this vertical exposes daily closing balances as a plain series, only derived aggregates (ABM, the 90-day forecast). Removed Income Stability's rolling-CV trend chart (only one point-in-time `cv_pct` is ever returned, no trend series) and Cashflow Analysis's "linear regression on net cashflow" trend claim and itemized per-loan debt list (no per-payee debt-obligation breakdown exists anywhere in the backend — replaced with the real aggregate `coverage_ratio` from `predictive/loan-readiness`). Fraud Risk's "score breakdown" now shows the real category *weights* instead of fabricated per-category points (the backend only returns the four fixed weights, not computed subscores per category); flag descriptions fall back to a synthesized sentence for `loan_officer`/`bank_viewer` roles, whose `description` field the backend redacts server-side.
- **Reconciliation drawer removed**: it was 100% mock (`reconciliation-data.ts`, deleted), and — checked — neither Sales nor Commerce ever wired the real thing either, despite `GET /api/v1/reconciliation/{analysis_run_id}` existing and every bank endpoint now returning a real `analysis_run_id` in `meta` (new this phase, via `_record_bank_analysis_run`). Not a drop-in swap: the real endpoint returns one aggregate report per analysis run, not the mock's per-`StatTile`-metric breakdown shape — would need a UI redesign, not just wiring. Documented here rather than faked or silently dropped.
- `mock-data.ts`, `reconciliation-data.ts`, and `placeholder.tsx` all deleted — every one of the 11 sections now has a real page.

**Verification**: `npx tsc -b --noEmit` and `npx vite build` both clean (same 3 pre-existing unrelated warnings). Backend change already tested separately (see above).

**Not yet done**: manual browser click-through (same caveat as every prior phase). Reconciliation drawer redesign (real data is available via `analysis_run_id`, just needs a UI that matches the real one-report-per-run shape). Phase 7 (reconciliation vertical proper) and Phase 8 (final cleanup) remain.

### 2026-07-18 — Phase 7: Reconciliation vertical wiring

`GET /api/v1/reconciliation/{analysis_run_id}` had real RBAC (`check_any_role`) and had existed since early on, but zero frontend consumers were wired to it. The one existing component, `ReconciliationReport`, expected a fabricated per-metric shape (`metricLabel`/`metricValue`/`source[]`/`excluded[]`/`totalProcessed`/`netValue`) that never matched what the backend actually returns — one aggregate report per analysis run (`records_analyzed`/`records_excluded`/`exclusion_detail`/`disabled_features`/`contextual_markers_applied`), keyed by an `analysis_run_id` that (checked directly in the service files) every ecommerce and sales compute function has already been returning via `record_analysis_run` since before this integration effort started — only bank was missing it, which Phase 6 already fixed.

**Commit `3b77df3`**:
- `reconciliation-api.ts` (new): `useReconciliationReport(analysisRunId)`.
- Rewrote `ReconciliationReport` to map the real shape onto its existing sub-components (`MetricPreview`, `SourceSummary`, `ExcludedRecordsTable`, `ReconciliationTotals`, `ReconciliationActions`) — those are generic enough to reuse as-is; only the top-level component needed to change what it fed them. `exclusion_detail` is defined in the schema but, confirmed by grep, never actually populated by any caller anywhere in the backend today — the excluded-records table will render empty until some analyzer starts populating it, which is honest (the component already handles an empty list gracefully) rather than papered over.
- Wired a "View reconciliation" action into each vertical's primary dashboard query (sales `pipeline-overview`, ecommerce `dashboard/summary`, bank `dashboard/summary`) — those three hooks now also expose `meta.analysis_run_id`, merged into the returned object as `_analysisRunId` so no other field access on those hooks needed to change.
- **Fixed two now-broken consumers** of the old shape, found by the typecheck immediately after the rewrite: `features/app` — a separate, fully-mock "playground" sandbox (routed at `/playground`) that was never part of this integration effort and isn't one of the four real verticals — had its own reconciliation modal wired to fake data; removed that wiring rather than either fake-fix it or migrate an out-of-scope page to real data. Deleted `features/upload/components/reconciliation-mock.ts` (`buildBalanceReconciliation`) — confirmed genuinely dead code, orphaned since Phase 3's real data-quality-report wiring superseded it but never removed at the time.

**Verification**: `npx tsc -b --noEmit` and `npx vite build` both clean (same 3 pre-existing unrelated warnings). No backend changes this phase, so no pytest run.

**Not yet done**: manual browser click-through (same caveat as every prior phase). Only Phase 8 (final cleanup pass + PR to `main`) remains.

## 0. What's actually in the repo right now

Verified directly (not assumed):

- **Four branches**: `main`, `staging` (both at `fa042a2`, the original clean scaffold), `dev-backend` (24 commits ahead of `main`, backend-only changes), `dev-frontend` (28 commits ahead of `main`, frontend-only changes). Neither dev branch has ever touched the other's directory — `dev-backend` never modified anything under `frontend/`, `dev-frontend` never modified anything under `backend/`.
- **A dry-run merge (`git merge-tree`) of `dev-backend` + `dev-frontend` produces exactly one conflict: `pnpm-lock.yaml`.** Everything else — all 191 changed frontend files, all backend files — merges cleanly. This is good news: the two branches are not on a collision course.
- The frontend on `dev-frontend` is a fully built UI (routes, features for auth/upload/sales-intelligence/commerce-intelligence/reconciliation/account/dashboard) wired to **mock data** (`mock-data.tsx`, `reconciliation-mock-data.ts`). It already has `axios`, `@tanstack/react-query`, and `@tanstack/react-router` in `package.json`, and a `handle-server-error.ts` axios helper — but nothing calls the real API yet.
- The backend on `dev-backend` is a FastAPI app with JWT bearer auth (access + refresh tokens returned in the response body, not cookies), CORS locked to specific origins, and a basic per-IP rate limiter on `/api/auth/*`.
- **Repo hygiene problem on `dev-backend`**: `backend/Python/` (an embedded Python runtime, ~181 MB) and `backend/app.db` (a SQLite file, ~81 MB) are tracked in git. That's 260 MB of binaries/DB data that will get pulled into every future clone and into `main` if merged as-is. This needs a decision before you integrate (see Phase 0).
- **One concrete auth gap found while reading the routes**: `GET /api/v1/upload/{upload_id}/quality-report` in `backend/app/routes/uploads.py` has no `current_user` dependency — it's reachable by anyone who can guess/enumerate a UUID. `reconciliation.py`'s equivalent route does enforce RBAC. Worth fixing during Phase 3, not silently, flagging it explicitly so it isn't missed.

## 1. What to do first — branch strategy

**Don't merge either dev branch into `main` yet, and don't merge `dev-frontend` straight into `dev-backend` either.** Keep both dev branches as-is (they're your "backend complete" / "frontend complete" checkpoints) and do the integration work on a new branch:

```
git checkout -b integration/frontend-backend dev-backend
git merge dev-frontend
```

Expect the one `pnpm-lock.yaml` conflict; resolve it by dropping both sides and regenerating:

```
git checkout --ours pnpm-lock.yaml   # or just rm it
pnpm install
git add pnpm-lock.yaml
git merge --continue
```

Before that merge, clean up the tracked-binary problem on `dev-backend` first (its own small commit, easy to review):

```
git rm -r --cached backend/Python backend/app.db
```

Add to `backend/.gitignore` (or root `.gitignore`):
```
backend/Python/
backend/app.db
```

This stops future bloat. It does **not** shrink history — the 260 MB is still in every existing commit. Whether to rewrite history (`git filter-repo`) to actually remove it is a separate, more disruptive decision (rewrites commit hashes, requires everyone to re-clone/re-base) — flag it to your team rather than doing it unilaterally. For now, "stop tracking it going forward" is the safe, non-destructive move and is enough to unblock integration.

Once `integration/frontend-backend` is green (auth works, one full vertical works end-to-end, security checklist below is clean), open a PR into `main`. Don't merge to `main` before that — `main` should only ever receive working, integrated code, not a mid-integration branch.

## 2. Standing security checklist (apply at every phase, not just once)

- **Token storage**: the backend returns `access_token` + `refresh_token` in the JSON body. Storing the refresh token in `localStorage` is XSS-exposed. Prefer keeping the access token in memory (React state/query cache) and persisting only the refresh token in the most restrictive storage you're willing to build (httpOnly cookie is best but requires a backend change to set it; if staying token-in-body, at minimum don't log tokens and clear them on tab close where possible).
- **CORS**: `allow_origins` in `backend/app/main.py` is a hardcoded list. Every new environment (staging URL, preview deploys) needs to be added there explicitly — don't switch to `allow_origins=["*"]` to make integration "easier."
- **Ownership/RBAC on every ID-keyed route**: anything shaped `/{something_id}/...` (`analysis_run_id`, `deal_id`, `upload_id`) must confirm the backend checks the requesting user actually owns/has a role on that resource before the frontend is wired to it. Known gap: `uploads.py` quality-report route (see §0). Treat this as a per-endpoint checklist item in Phases 3–7, not a one-time fix.
- **Never ship server secrets to the frontend.** Only a public API base URL (`VITE_API_BASE_URL` or similar) belongs in frontend env. `GEMINI_API_KEY`, `MONO_SECRET_KEY`, S3 keys, `FERNET_KEY`, `SECRET_KEY` stay server-side only.
- **Fix the default secrets before any shared environment.** `backend/app/config.py` ships a public default `fernet_key` and `secret_key: "change-me-in-production"` — fine for local dev, must be overridden via real `.env` the moment this touches staging.
- **File uploads**: validate type/size on both the frontend (fast feedback) and backend (source of truth) — never trust the client-side check alone.
- **Error responses**: don't let raw backend exception text reach the UI (stack traces, SQL errors). `handle-server-error.ts` already exists on the frontend — route all API errors through it and keep messages generic for anything 5xx.

## 3. Endpoint groups → frontend features (integration order)

Recommended order: infra first, then auth (everything else needs it), then the thinnest vertical slice (uploads/analyze) to prove the pattern, then the three verticals, then reconciliation, then cleanup.

| Phase | Backend routes | Frontend feature(s) |
|---|---|---|
| 1 | — (infra only) | shared API client, env config |
| 2 | `routes/auth.py` | `features/auth/*`, `routes/_auth.*` |
| 3 | `routes/uploads.py`, `routes/analyze.py` | `features/upload/*` |
| 4 | `routes/sales.py` | `features/sales-intelligence/*` |
| 5 | `routes/ecommerce.py` | `features/commerce-intelligence/*` |
| 6 | `routes/bank.py` | `features/dashboard/*` (confirm mapping when you get there) |
| 7 | `routes/reconciliation.py` | `features/reconciliation` (wherever it's rendered) |
| 8 | cleanup | remove remaining `mock-data.tsx` / `reconciliation-mock-data.ts` |

## 4. Step-by-step tasks with ready-to-use agent prompts

Each step is small on purpose — one endpoint group or one concern at a time, so each can be reviewed/tested before moving on. Paste the prompt as-is (or lightly adjusted) as your next message to the agent.

### Phase 0 — Repo hygiene + branch setup

**Step 0.1 — Stop tracking committed binaries**
> On `dev-backend`, run `git rm -r --cached backend/Python backend/app.db`, add `backend/Python/` and `backend/app.db` to `.gitignore`, and commit that as its own commit with message describing the cleanup. Don't touch anything else in this commit.

**Step 0.2 — Create the integration branch and merge**
> Create branch `integration/frontend-backend` from `dev-backend`, then merge `dev-frontend` into it. I expect only `pnpm-lock.yaml` to conflict — resolve it by deleting the file and regenerating with `pnpm install`, then finish the merge. Show me `git status` and a summary of what merged before committing anything further.

### Phase 1 — API client infrastructure (no UI changes yet)

**Step 1.1 — Env config**
> Add `VITE_API_BASE_URL` to a `frontend/.env.example` (default `http://localhost:8000`) and read it via `import.meta.env` in a single config module under `frontend/src/lib/`. Don't hardcode the URL anywhere else.

**Step 1.2 — Axios instance + interceptors**
> Create `frontend/src/lib/api-client.ts`: an axios instance using the base URL from step 1.1, an interceptor that attaches `Authorization: Bearer <access_token>` from wherever we decide to store it, and a response interceptor that routes errors through the existing `handle-server-error.ts`. Don't wire it into any component yet — just the client.

**Step 1.3 — React Query setup**
> Wire up `@tanstack/react-query`'s `QueryClientProvider` at the app root (check `frontend/src/main.tsx` or wherever the router is mounted) if it isn't already. Add sane defaults (retry off for mutations, reasonable staleTime). No feature wiring yet.

**Step 1.4 — Auth token storage decision**
> Implement token storage per the decision in docs/INTEGRATION_PLAN.md §2 (access token in memory/query cache, refresh token in the most restrictive storage we're using). Expose `getAccessToken`/`setTokens`/`clearTokens` helpers that `api-client.ts` (step 1.2) will use.

### Phase 2 — Auth

**Step 2.1 — Register + OTP verify**
> Wire `features/auth/register` and the OTP screen to `POST /api/auth/register`, `POST /api/auth/verify-otp`, `POST /api/auth/resend-otp`. Replace any mock submit handlers. Surface backend validation errors (e.g. duplicate email) in the existing form error UI — don't invent new error UI.

**Step 2.2 — Login + refresh + logout**
> Wire `features/auth/login` to `POST /api/auth/login`, add silent refresh via `POST /api/auth/refresh` (trigger on 401 from the api-client interceptor, retry the original request once), and wire logout to `POST /api/auth/logout` plus clearing local tokens.

**Step 2.3 — Session bootstrap**
> On app load, if a refresh token exists, call `GET /api/auth/me` to restore the session before rendering protected routes. Gate the `_app` route tree on this.

**Step 2.4 — Password reset**
> Wire the reset-password feature to `POST /api/auth/forgot-password` and `POST /api/auth/reset-password`.

**Step 2.5 — Google OAuth**
> Wire the "continue with Google" button to redirect to `GET /api/auth/google`, and handle the callback redirect (`settings.frontend_url` + URL fragment with tokens) on app load — parse and store the tokens, then clear the fragment from the URL.

**Step 2.6 — Security pass on auth**
> Review the Phase 2 auth wiring against docs/INTEGRATION_PLAN.md §2: confirm no token ever gets logged to console, confirm refresh-token storage matches the step 1.4 decision, confirm the OAuth fragment is stripped from the URL/history after parsing (it shouldn't linger in browser history).

### Phase 3 — Uploads + Analyze

**Step 3.1 — File upload**
> Wire `features/upload` to whatever upload endpoint accepts the file (check `routes/uploads.py` and `routes/analyze.py` for the actual upload path — confirm which one accepts multipart file upload vs which just analyzes an existing upload) and to `POST` on `routes/analyze.py`. Validate file type/size client-side before sending, matching whatever the backend accepts.

**Step 3.2 — Quality report + fix the auth gap**
> Wire the quality-report screen to `GET /api/v1/upload/{upload_id}/quality-report`. Before wiring it, add a `current_user` auth dependency (and appropriate ownership check, matching the pattern in `reconciliation.py`) to that backend route — it currently has none. Confirm the frontend sends the bearer token and handles 401/403.

### Phase 4 — Sales vertical

**Step 4.1 — Sales dashboard**
> Wire `features/sales-intelligence` dashboard widgets to `GET /api/v1/sales/dashboard/pipeline-overview` and `.../dashboard/rep-leaderboard`, replacing mock data. One request per widget via react-query, with loading/error states using existing UI components.

**Step 4.2 — Sales diagnostics**
> Wire the diagnostic views to `.../diagnostic/data-quality-cost`, `.../diagnostic/stage-velocity`, `.../diagnostic/stagnation-alerts`.

**Step 4.3 — Sales predictive + AI**
> Wire `.../predictive/forecast`, `.../predictive/rep-trajectory`, `.../predictive/slippage`, `.../predictive/win-dna`, `.../reports/quarter-postmortem`, `.../ai/playbook`.

**Step 4.4 — Deal loss-reason capture**
> Wire the loss-reason UI to `POST /api/v1/sales/deals/{deal_id}/capture-loss-reason`. Confirm the backend checks the deal belongs to the current user's org/merchant before accepting the write.

### Phase 5 — Ecommerce vertical

**Step 5.1 — Dashboard**
> Wire `features/commerce-intelligence` dashboard to `.../ecommerce/dashboard/summary`, `.../dashboard/revenue`, `.../dashboard/sku-matrix`.

**Step 5.2 — Diagnostics**
> Wire `.../diagnostic/profit-leaks`, `.../diagnostic/dead-stock`, `.../diagnostic/return-forensics`.

**Step 5.3 — Predictive + AI**
> Wire `.../predictive/inventory-forecast`, `.../predictive/rfm-segments`, `.../predictive/churn-risk`, `.../ai/playbook`.

**Step 5.4 — Ad kill-switch (state-changing endpoints)**
> Wire `.../predictive/ad-kill-switch/configure` and `.../ad-kill-switch/pause`. These mutate state (pauses real ad spend per the naming) — add an explicit confirm step in the UI before calling, and make sure errors are surfaced clearly rather than silently failing.

### Phase 6 — Bank vertical

**Step 6.1 — Dashboard + diagnostics**
> Confirm which frontend feature maps to bank data (check `features/dashboard` or wherever bank-statement analysis is surfaced), then wire `.../bank/dashboard/summary` and the diagnostic routes (`income-stability`, `abm`, `cashflow-analysis`, `customer-segmentation`, `revenue-patterns`).

**Step 6.2 — Predictive + AI**
> Wire `.../predictive/fraud-risk`, `.../predictive/loan-readiness`, `.../predictive/cashflow-forecast`, `.../ai/lender-brief`, `.../ai/financial-health-playbook`.

### Phase 7 — Reconciliation

**Step 7.1**
> Wire the reconciliation report view to `GET /api/v1/reconciliation/{analysis_run_id}`, replacing `reconciliation-mock-data.ts`. This route already has RBAC (`check_any_role`) — confirm the frontend correctly handles a 403 for a user without the right role, since that's an expected legitimate response here, not just an error to swallow.

### Phase 8 — Final pass

**Step 8.1 — Remove remaining mocks**
> Search the frontend for any remaining imports of `mock-data.tsx` or other mock fixtures and confirm every one has been replaced by a real API call from Phases 2–7. Delete the mock files once nothing references them.

**Step 8.2 — Full security re-pass**
> Re-check docs/INTEGRATION_PLAN.md §2 end to end against the finished integration: token storage, CORS origins for the actual deploy targets, every ID-keyed route's ownership check, no secrets in any frontend bundle (`grep` the built `dist/` output for anything that looks like a server-side key), upload validation, generic error surfaces. Report findings before opening the PR to `main`.

**Step 8.3 — PR to main**
> Open the PR from `integration/frontend-backend` into `main` once 8.1 and 8.2 are clean. Not before.
