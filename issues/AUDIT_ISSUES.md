# Scanwick — Full System Audit: Issue Catalog

**Generated:** 2026-07-30
**Scope:** Full backend (FastAPI) + frontend (React/TS) codebase, read-only static audit.
**Method:** Four parallel deep-dive audits — (A) Backend Auth/RBAC/Team/Entitlements, (B) Backend Payments/Bank/Ecommerce/Webhooks, (C) Backend Uploads/Ingestion/Celery/Storage, (D) Frontend forms & flows.

> This is a first pass. A second file (external audit findings) is expected next; the two will be merged into a combined, de-duplicated backlog before fixing begins. Do not start fixing yet unless told otherwise.

## How to read this document

Each issue has:
- **ID** — stable reference tag for cross-linking during merge/triage (e.g. `AUTH-01`)
- **Category** — `security` | `input-validation` | `business-logic/flow` | `data-integrity` | `ux` | `other`
- **Severity** — `critical` | `high` | `medium` | `low`
- **Location** — file path(s) and line number(s)
- **Description** — what's wrong, why it matters, and the concrete trigger/scenario

## Severity summary

| Severity | Count |
|---|---|
| Critical | 5 |
| High | 8 |
| Medium | 22 |
| Low | 17 |

---

## 1. Authentication, Sessions, 2FA, Team & Entitlements (backend)

### AUTH-01 — Account pre-hijacking via unverified "shadow" accounts
- **Category:** security | **Severity:** critical
- **Location:** `backend/app/routes/auth.py:204-234` (`register`), `:816-824` (`google_callback`)
- **Description:** Registering with someone else's email creates an unverified `User` row with an attacker-chosen password. If the real owner later (a) re-registers with the same email, or (b) signs in via Google with that email, the existing row is reused/verified but **the attacker's password hash is never rotated or cleared**. The attacker retains silent, persistent login access. Victim has no obvious way to detect this; `/change-password` requires the current (attacker's) password, so only `/forgot-password` recovers it.

### AUTH-02 — TOTP 2FA can be fully bypassed via the email-OTP login endpoints
- **Category:** security / business-logic-flow | **Severity:** critical
- **Location:** `backend/app/routes/auth.py:239-285` (`verify_otp_route`), `:288-314` (`resend_otp_route`)
- **Description:** `/login` correctly blocks and requires `/2fa/verify-login` when `user.totp_enabled`. But `resend_otp_route`/`verify_otp_route` (the parallel email-OTP path) never check `totp_enabled` at all — anyone who knows the password and can read one email to the account can log in and get tokens, completely skipping 2FA.

### AUTH-03 — JWT signing secret defaults to a hardcoded public value with no startup enforcement
- **Category:** security | **Severity:** critical
- **Location:** `backend/app/config.py:16-19`, `backend/app/main.py:104-115`, `backend/app/dependencies.py:27,54`
- **Description:** `secret_key` defaults to `"change-me-in-production"` if `SECRET_KEY` env var is unset. Unlike `fernet_key`, there is no startup guard refusing to boot with this default when `dev_mode=False`. If ever deployed unset, anyone can forge JWTs for any user and fully impersonate any account.

### AUTH-04 — No password strength/length requirements enforced server-side
- **Category:** input-validation / security | **Severity:** high
- **Location:** `backend/app/schemas/auth.py:7-11, 62-64, 110-112` (register/reset/change password schemas)
- **Description:** All password fields are bare `str` with no `min_length`/complexity constraints, and no additional server-side check exists in the route handlers. A 1-character password is accepted. (See also **FE-09**, **FE-10** — matching client-side gaps.)

### AUTH-05 — No account-level brute-force protection on `/login` or `/2fa/verify-login`
- **Category:** security | **Severity:** high
- **Location:** `backend/app/routes/auth.py:319-347` (`login`), `:350-375` (`verify_2fa_login`)
- **Description:** Only a blanket per-IP rate limit exists (trivially defeated by rotating IPs). The email-OTP path has its own per-account lockout (`_OTP_MAX_ATTEMPTS`), but password login and TOTP-code verification — the two places brute force matters most — have no equivalent per-account throttle.

### AUTH-06 — Email matching is case-sensitive and inconsistent across flows, enabling duplicate accounts
- **Category:** data-integrity / security | **Severity:** medium
- **Location:** `backend/app/routes/auth.py:206,321,352,637,681` (no `.lower()`); `:802` (`google_callback` does normalize); `backend/app/services/team_management.py:182,293,310`
- **Description:** Password-flow lookups/inserts never normalize email case, while Google OAuth does. `"User@Example.com"` and `"user@example.com"` can become two distinct accounts; team-invite matching has the same gap.

### AUTH-07 — Team-invite token passed as a URL path segment instead of a request body field
- **Category:** security | **Severity:** medium
- **Location:** `backend/app/routes/team.py:117` (`POST /invite/{token}/accept`)
- **Description:** The invite token is a bearer credential but travels in the URL path, making it far more likely to be captured in access logs, proxy logs, and browser history than a POST body field would be.

### AUTH-08 — Team-invite link (with token) unconditionally printed to stdout, including production
- **Category:** security / sensitive-data-logging | **Severity:** medium
- **Location:** `backend/app/utils/email.py:120-121`
- **Description:** Unlike every other email function in this file (which gates debug printing behind `dev_mode`), `send_team_invite_email` prints the full accept link — including the 7-day-valid invite token — unconditionally. Anyone with log access can hijack pending invites.

### AUTH-09 — Destructive account/data-deletion endpoints require no re-authentication
- **Category:** security / business-logic | **Severity:** medium
- **Location:** `backend/app/routes/privacy.py:117-124` (`delete_data`), `backend/app/routes/auth.py:602-614` (`request_account_deletion`)
- **Description:** Permanent, irreversible data wipe requires only a valid bearer access token — no password re-entry, no confirmation step. A leaked/stolen token is sufficient for irreversible destruction.

### AUTH-10 — `merchant_id` is deterministically computable from a small integer `user_id`
- **Category:** security (architectural) | **Severity:** medium
- **Location:** `backend/app/services/merchant_provisioning.py:21,104-116`
- **Description:** `merchant_id = uuid5(hardcoded_namespace, str(user_id))`. Since `user_id` is a small sequential public integer and the namespace is committed in source, any user's `merchant_id` is computable by anyone. Not currently directly exploitable (routes also filter by caller's own `user_id` via RBAC), but removes any "unguessable ID" safety net — every current/future merchant-scoped endpoint must remember to pair `merchant_id` with the caller's identity, or it becomes a full cross-tenant IDOR. See **PAY-01**, **PAY-02** where exactly this class of gap already occurred elsewhere.

### AUTH-11 — Unsanitized user name fields interpolated unescaped into HTML emails
- **Category:** input-validation / security | **Severity:** medium
- **Location:** `backend/app/schemas/auth.py:8-9` (no constraints on `first_name`/`last_name`); `backend/app/utils/email.py:54,69,125`
- **Description:** `first_name`/`last_name`/`inviter_name` flow unescaped into raw f-string HTML email templates. A user can set their name to an HTML/script payload, which is most damaging in the team-invite case: the payload is emailed to a different, trusting recipient inside an official-looking transactional email.

### AUTH-12 — `InviteRequest.email` has no email format/length validation
- **Category:** input-validation | **Severity:** low-medium
- **Location:** `backend/app/routes/team.py:32`
- **Description:** Unlike every other email field in the codebase (`EmailStr`), this one is a bare `str`. Malformed values fail late at the email provider instead of a clean 422 at the API boundary.

### AUTH-13 — `accept_invite` can raise an unhandled `IntegrityError`
- **Category:** data-integrity | **Severity:** low-medium
- **Location:** `backend/app/services/team_management.py:171-224` (`create_invite`), `:260-328` (`accept_invite`)
- **Description:** `create_invite` only dedupes against other pending invites, not existing active roles for the same vertical/merchant. Re-inviting an already-active member and having them accept violates a unique constraint on commit with no try/except, unlike the equivalent race handled in `merchant_provisioning.ensure_merchant_provisioned`. Surfaces as an unhandled 500.

### AUTH-14 — `forgot_password` deliberately discloses account existence
- **Category:** security | **Severity:** low (acknowledged tradeoff)
- **Location:** `backend/app/routes/auth.py:628-667`
- **Description:** Docstring explicitly documents this as a conscious enumeration tradeoff. Listed for completeness — a real email-enumeration vector regardless of intent.

### AUTH-15 — Non-constant-time OTP code comparison
- **Category:** security | **Severity:** low
- **Location:** `backend/app/utils/otp.py:50` (`if record.code != code`)
- **Description:** String `!=` is not timing-safe. Minor risk given existing rate limits; `secrets.compare_digest` is the correct primitive.

### AUTH-16 — `is_current` session flag is a positional heuristic, not tied to the actual request's session
- **Category:** business-logic/flow | **Severity:** low
- **Location:** `backend/app/routes/auth.py:544-562` (`list_sessions`)
- **Description:** `is_current=(index == 0)` just picks the most-recent token row rather than matching the token presented in the current request. Can mislabel which "device" is active, risking accidental revocation of the wrong session.

### AUTH-17 — No length/format constraints on free-text profile fields
- **Category:** input-validation | **Severity:** low
- **Location:** `backend/app/schemas/auth.py:99-107` (`UpdateProfileRequest`)
- **Description:** `company`, `industry`, `primary_currency`, `language`, `timezone` etc. are unconstrained optional strings — no max length, no ISO-4217/locale format checks.

### AUTH-18 — No security response headers configured
- **Category:** other | **Severity:** low
- **Location:** `backend/app/main.py` (only `CORSMiddleware` registered)
- **Description:** No `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, or `Content-Security-Policy`. Missing defense-in-depth layer, notable given **AUTH-11**'s injection surface.

---

## 2. Payments, Banking, Ecommerce, Webhooks, Reconciliation (backend)

### PAY-01 — Cross-tenant IDOR: Mono bank-account ingestion never verifies account ownership
- **Category:** security (IDOR) | **Severity:** critical
- **Location:** `backend/app/routes/bank.py:592-629` (`upload_bank_mono`), `backend/app/services/mono_ingestion.py:52-83`
- **Description:** `POST /api/v1/bank/upload/mono` only checks the caller has a role on their own `merchant_id` — it never verifies the client-supplied `mono_account_id` actually belongs to that merchant/user via a real Mono Connect link. No table anywhere associates `mono_account_id` with a merchant. Any authenticated user (self-signup grants this role automatically) can supply any guessed/leaked `mono_account_id` and have that stranger's full bank statement, real account number, and institution ingested into their own dashboard.

### PAY-02 — Authorization check runs *after* a database write on every account-scoped bank endpoint
- **Category:** security / flow-ordering | **Severity:** high
- **Location:** `backend/app/routes/bank.py:163-227` (`_load_account_and_transactions`), used by all routes at `:261-463`
- **Description:** Every bank dashboard/diagnostic/predictive route loads the account and runs (and **commits**) `detect_own_account_transfers` mutations against it *before* `check_role` is called and can reject. An attacker who knows/guesses another merchant's `account_id` can trigger a write against that merchant's data even though the eventual response is a 403 — "authorize before you act" is violated.

### PAY-03 — Flutterwave webhook "verification" is a static string compare, not bound to the payload
- **Category:** security | **Severity:** medium (high if secret ever leaks)
- **Location:** `backend/app/routes/webhooks.py:36-48`, `backend/app/services/payments.py:378-384,438-456`
- **Description:** Unlike Paystack's proper HMAC-SHA512-over-body signature, Flutterwave verification is `hmac.compare_digest(header, static_secret)` — unrelated to the request body. If that one static secret ever leaks, an attacker can forge **any** `charge.completed` webhook body to fraudulently mark any pending transaction as paid (e.g. free plan upgrade), since `_handle_flutterwave_event` never calls back to Flutterwave to confirm the charge actually happened (contrast with `GET /verify/{reference}`, which does).

### PAY-04 — TOCTOU race in bank/ecommerce ingestion dedup — no DB constraint backs it
- **Category:** data-integrity / race-condition | **Severity:** medium
- **Location:** `backend/app/services/bank_ingestion.py:393-457`, `backend/app/services/ecommerce_ingestion.py:341-467`
- **Description:** Dedup is done via one `SELECT` of existing rows read into memory, then per-row in-memory checks before a single commit. Neither `bank_transactions` nor `orders` has a unique DB constraint on the natural key. Two concurrent ingestion runs (double-submit, client retry, redelivered Celery task) both read the same "not yet existing" snapshot and both insert — silently double-counting revenue/cashflow.

### PAY-05 — Bank transaction dedup key is too coarse and silently drops legitimate transactions with no visible warning
- **Category:** data-integrity | **Severity:** medium
- **Location:** `backend/app/services/bank_ingestion.py:403-429`, `:317-373` (`compute_bank_quality_report`)
- **Description:** Dedup key is `(date, amount, description)` only — two genuinely distinct same-day, same-amount, same-narration transactions collide and the second is silently dropped. `duplicates_skipped` is computed but never surfaced in the quality-report `warnings`, so the merchant has no way to know real transactions were discarded.

### PAY-06 — Ecommerce ingestion aborts the *entire* file on one malformed `quantity` cell
- **Category:** business-logic/flow / input-validation | **Severity:** medium
- **Location:** `backend/app/services/ecommerce_ingestion.py:256` (bare `int(...)`), within `extract_canonical_rows`
- **Description:** Every other canonical field uses graceful coercion + per-row rejection; `quantity` uses a bare `int()` with no try/except. One bad cell in a 10,000-row file raises uncaught, propagates to the Celery task's outer `except Exception`, and fails the **whole** upload with zero rows ingested, instead of just rejecting that row.

### PAY-07 — No sanity/sign checks on ingested financial amounts
- **Category:** input-validation | **Severity:** medium
- **Location:** `backend/app/services/ecommerce_ingestion.py:257-267,312-316`
- **Description:** `gross_revenue`, `discount_amount`, `refund_amount`, `unit_price`, `unit_cogs`, `quantity` have no non-negative/bound checks — only `None`-checks. A negative `gross_revenue` (data error or hostile export) flows straight into the dashboard's revenue figures with no reconciliation warning.

### PAY-08 — No replay protection (timestamp/nonce) on either payment webhook
- **Category:** security | **Severity:** low
- **Location:** `backend/app/routes/webhooks.py:19-48`
- **Description:** Impact mitigated by idempotent `apply_successful_charge`, but still a defense-in-depth gap — compounds **PAY-03** since a leaked Flutterwave webhook request could be replayed indefinitely.

### PAY-09 — No idempotency guard on `POST /api/v1/payments/checkout`
- **Category:** business-logic/flow | **Severity:** low
- **Location:** `backend/app/routes/payments.py:62-83`, `backend/app/services/payments.py:96-143`
- **Description:** No check for an existing pending transaction before starting another; double-click/retry can create multiple pending checkout sessions, producing a confusing `/history` list.

### PAY-10 — PDF parsing happens before the page-count/size guard
- **Category:** input-validation | **Severity:** low
- **Location:** `backend/app/services/bank_pdf_ingestion.py:36-56`
- **Description:** `fitz.open()` fully parses the PDF before `page_count > _MAX_PDF_PAGES` is checked. Mitigated by the 15MB upload cap and Celery isolation, but a pathological small-but-complex PDF could still consume parser resources before rejection.

### PAY-11 — Flutterwave failed/declined charges never transition transaction state
- **Category:** business-logic/flow | **Severity:** low
- **Location:** `backend/app/services/payments.py:438-456`
- **Description:** Only `charge.completed`/`successful` and `subscription.cancelled` are handled; a failed/declined Flutterwave charge falls into an `else: logger.info(...)` no-op, leaving the transaction `pending` indefinitely unless the user happens to hit `/verify/{reference}` manually.

---

## 3. Uploads, Ingestion, Column Mapping, Celery, Storage (backend)

### UP-01 — Uploaded/staged files are served completely unauthenticated
- **Category:** security (broken access control) | **Severity:** high
- **Location:** `backend/app/main.py:95-96` (static mount, no auth), `backend/app/services/storage.py:65-66` (non-expiring local URL vs. presigned S3 URL), `backend/app/services/upload_staging.py:16-33`
- **Description:** In local-storage mode (the default), any file — raw staged CSVs included — is retrievable by anyone who has/guesses/leaks the URL. The `upload_id` is returned directly to the browser (referrer headers, browser history, logs). Bank statements and e-commerce exports containing PII/account numbers sit at these URLs with zero access control. Compounds **UP-03** (orphaned files never expire).

### UP-02 — `analyze.py` file-type check is bypassable via Content-Type spoofing
- **Category:** security / input-validation | **Severity:** medium (currently dead code — router not mounted in `main.py`, but live source that could be re-enabled any time)
- **Location:** `backend/app/routes/analyze.py:93-99,108-121`
- **Description:** The check is an OR-gate, not AND: setting `Content-Type: application/octet-stream` bypasses the extension check entirely, since that content-type is in the allowed list. Arbitrary file content gets persisted to storage *before* any CSV-parse attempt, and raw parse exceptions leak to the client (line 118-121). This is exactly the vulnerability class already fixed in `uploads.py` ("Audit #17" per its own comments) but never applied here.

### UP-03 — Orphaned staged files/`Upload` rows for abandoned column-mapping confirmations
- **Category:** data-integrity / resource-leak | **Severity:** medium
- **Location:** `backend/app/routes/uploads.py:386-399`, `backend/app/services/upload_staging.py:83-93`, `backend/app/celery_app.py` (no cleanup job)
- **Description:** Files staged for `needs_mapping` uploads are only deleted from inside the ingestion task's `finally` block, which never runs if the user abandons the mapping-review screen. No cleanup/expiry job exists anywhere. Combined with **UP-01**: unauthenticated-accessible sensitive data with no TTL, forever.

### UP-04 — Duplicate-ingestion race condition — no DB constraint backs application-level dedup
- **Category:** data-integrity / race-condition | **Severity:** medium
- **Location:** `backend/app/services/bank_ingestion.py:396-429`, `backend/app/services/ecommerce_ingestion.py:341-374` — same underlying issue as **PAY-04**, confirmed independently by this audit pass
- **Description:** No `UniqueConstraint` on the natural keys in `bank_transactions`/`orders`. Concurrent uploads, double-submits, or Celery task redelivery after a worker restart (no task idempotency key) can both commit, silently double-counting revenue/cashflow.

### UP-05 — No Celery task timeout and no row-count cap
- **Category:** business-logic/flow / resource-limits | **Severity:** medium
- **Location:** `backend/app/celery_app.py` (no `task_time_limit`/`task_soft_time_limit`), `backend/app/services/bank_ingestion.py:169`, `backend/app/services/ecommerce_ingestion.py:365`
- **Description:** Only a 10MB byte cap exists on uploads — no row-count cap and no Celery-level time limit. A 10MB file with millions of short rows can occupy a worker indefinitely, degrading ingestion throughput for every other merchant sharing the pool.

### UP-06 — File-size check happens after the full upload body is received
- **Category:** input-validation | **Severity:** low-medium
- **Location:** `backend/app/routes/uploads.py:311-316,133-138`, `backend/app/routes/analyze.py:101-106`
- **Description:** `raw = await file.read()` happens before the `len(raw) > _MAX_BYTES` check — no early rejection via `Content-Length` or streaming cap. Server fully receives/disk-spools an oversized body before the limit is ever consulted.

### UP-07 — Sample rows from uploaded CSVs (potentially PII/financial data) sent to a third-party LLM
- **Category:** data-integrity / data-privacy | **Severity:** low
- **Location:** `backend/app/services/dataset_detection.py:106-112`, reachable via `POST /api/v1/upload/detect`
- **Description:** When header-heuristic confidence is below 0.75, the first 3 full data rows (not just headers) are sent to an external Gemini API call for classification — potentially including real account numbers, narrations, balances, or customer emails, with no redaction. Worth confirming this is covered by the product's privacy posture / DPA.

---

## 4. Frontend — Forms, Flows, UX (React/TypeScript)

### FE-01 — Every failed API call can show two conflicting error messages
- **Category:** ux / business-logic-flow | **Severity:** high
- **Location:** `frontend/src/lib/api-client.ts:79`, `frontend/src/lib/handle-server-error.ts:4-31`
- **Description:** The global axios interceptor fires a toast for *every* error, but most calling components also render their own error UI in `catch`/`onError`. A single failed request (bad login, failed 2FA, failed password change, failed invite) can show a generic global toast stacked with a specific local message simultaneously — confirmed reproducible on a simple bad-login attempt.

### FE-02 — `autoComplete="off"` hardcoded on every field, including passwords
- **Category:** input-validation / ux | **Severity:** medium
- **Location:** `frontend/src/components/FormField.tsx:29`
- **Description:** No `current-password`/`new-password`/`email`/`username` autocomplete hints anywhere. Breaks browser/password-manager autofill and "save password" prompts across login, register, reset-password, accept-invite, and OTP flows — actively discourages generated/strong password use.

### FE-03 — Shared `CardLayout` submit button never disables / shows no loading state; OTP form has no double-submit guard at all
- **Category:** business-logic/flow | **Severity:** medium-high
- **Location:** `frontend/src/features/auth/reset-password/components/CardLayout.tsx:24`, used by reset-password and `frontend/src/features/auth/otp/index.tsx:51-90`
- **Description:** No `disabled` prop wired to the submit button for forgot-password/reset-password/OTP flows (unlike login/register, which correctly disable via `AuthFooter`). `OtpCard.onSubmit` additionally has no submitting-guard at all — rapid double-click/double-Enter fires concurrent `/verify-otp` calls.

### FE-04 — Workspace Settings page is entirely non-functional (no persistence, no API call)
- **Category:** business-logic/flow | **Severity:** high
- **Location:** `frontend/src/features/account/workspace-settings.tsx:1-164`
- **Description:** Every control (currency, exchange-rate source, Ad-Kill Switch mode, thresholds, notification toggles, etc.) is local `useState` only — no save button, no backend call anywhere in the file, despite copy explicitly claiming these settings "affect Net Margin, Profit Leak..." and "recalculate all channel metrics." Changes vanish on navigation/refresh; users are misled into thinking they configured real business logic.

### FE-05 — Contextual Markers are never persisted to the backend
- **Category:** business-logic/flow | **Severity:** high
- **Location:** `frontend/src/features/account/contextual-markers.tsx:26-133`
- **Description:** `addMarker`/`deleteMarker` only mutate local state; the UI claims tagged periods are flagged `is_anomalous` and excluded from model training platform-wide — this is false; nothing reaches the backend and markers reset on reload.

### FE-06 — Notification Center is fully mocked; "Mark all read" is a local no-op
- **Category:** business-logic/flow | **Severity:** medium
- **Location:** `frontend/src/features/notifications/index.tsx:42-156`
- **Description:** Hardcoded initial notifications array; no fetch, no API call for read-state. Nothing persists across reload or devices.

### FE-07 — "Create Report" and "Scheduled Reports" are entirely client-side mocks
- **Category:** business-logic/flow | **Severity:** medium-high
- **Location:** `frontend/src/features/reports/pages/create-report.tsx:57-74`, `frontend/src/features/reports/pages/scheduled-reports.tsx:54-63,99`
- **Description:** No network call in either file — a user who schedules a report and closes the tab loses everything, believing a real recurring email report was configured. Additionally, the "Recipients" field (line 99) has zero email-format validation, only a `.trim()` presence check.

### FE-08 — Landing-page "Leave a review" form is completely non-functional
- **Category:** business-logic/flow | **Severity:** medium
- **Location:** `frontend/src/features/landing/index.tsx:599-636`
- **Description:** No `onSubmit`/`onClick` handler anywhere; inputs are fully uncontrolled. Public marketing page explicitly promises the review "is visible to everyone" — clicking Submit does nothing.

### FE-09 — Password-change form has no minimum-length/strength check
- **Category:** input-validation | **Severity:** medium
- **Location:** `frontend/src/features/account/billing/security-tab.tsx:49-57`
- **Description:** Only checks non-empty and match — no length/strength requirement, unlike registration's `.min(8, ...)`. Combines with backend gap **AUTH-04** to allow 1-character passwords end-to-end.

### FE-10 — Registration form has no "confirm password" field
- **Category:** input-validation / ux | **Severity:** low-medium
- **Location:** `frontend/src/features/auth/register/index.tsx:40-53,178-191`
- **Description:** Unlike reset-password and accept-invite (both of which require confirmation), a typo during signup is undetectable client-side and only surfaces when the user can't log in later.

### FE-11 — File upload validates only the filename extension, not content/MIME type
- **Category:** input-validation | **Severity:** low-medium
- **Location:** `frontend/src/features/upload/index.tsx:326-328`
- **Description:** `acceptFile` checks `file.name.toLowerCase().endsWith(acceptExtension)` only. Any file can be renamed to pass. Defense-in-depth gap only (backend must be the real gate — see **UP-02** for where that gate is actually broken).

### FE-12 — Team-invite and Account-profile forms lack basic field validation
- **Category:** input-validation | **Severity:** low
- **Location:** `frontend/src/features/account/team-permissions.tsx:121-127`, `frontend/src/features/account/billing/account-tab.tsx:89-129`
- **Description:** Invite form checks only non-empty email, no format validation despite an available `type="email"` input. Profile fields (name, company, industry, currency, language, timezone) have no `required`/max-length/format constraints; empty first/last name can be submitted.

### FE-13 — Reset-password mismatch check isn't tied to the field (inconsistent with Accept-Invite)
- **Category:** ux / input-validation | **Severity:** low
- **Location:** `frontend/src/features/auth/reset-password/index.tsx:160-172`
- **Description:** Manual comparison + generic page-level alert, instead of zod `.refine()` bound to the field (as accept-invite correctly does). No inline invalid state on the confirm-password input itself.

### FE-14 — Refresh token stored in a non-`httpOnly` cookie
- **Category:** security (informational, documented tradeoff) | **Severity:** low
- **Location:** `frontend/src/lib/auth-tokens.ts:1-11,43-48`, `frontend/src/lib/cookies.ts:26-38`
- **Description:** `SameSite=Strict` + `Secure` but not `httpOnly` (backend returns it in the response body rather than setting the cookie itself). Any future XSS anywhere in the app could exfiltrate the refresh token via `document.cookie`.

### FE-15 — Password-reset token travels in the URL query string
- **Category:** security (informational) | **Severity:** low
- **Location:** `frontend/src/routes/_auth.reset.tsx:6-18`
- **Description:** Standard pattern for email-link reset flows, not itself a bug, but URL-embedded tokens can leak via browser history/proxy logs/`Referer` headers. No active leak vector found in this codebase.

### FE-16 — 2FA-enable code field doesn't enforce digits-only client-side
- **Category:** input-validation | **Severity:** low
- **Location:** `frontend/src/features/account/billing/security-tab.tsx:127-131`
- **Description:** Only checks `code.length !== 6`, not numeric-only, inconsistent with the `REGEXP_ONLY_DIGITS`-constrained `InputOTP` used elsewhere in the app's 2FA/OTP flows.

---

## Cross-cutting patterns worth fixing structurally (not one-off bugs)

1. **RBAC-after-action ordering bug repeats** (`PAY-02`) — worth a codebase-wide grep for "load resource, then check_role" ordering rather than fixing bank.py alone.
2. **Ingestion dedup relies entirely on application logic, no DB constraints** (`PAY-04`, `PAY-05`, `UP-04`) — same root cause hit from three different audit angles; fix once at the schema level (unique constraint / upsert) rather than patching each ingestion path.
3. **"Feature looks real but never calls the backend" pattern repeats across the frontend** (`FE-04`, `FE-05`, `FE-06`, `FE-07`, `FE-08`) — five separate screens present fully-wired UI with persuasive copy but no network call. Worth a deliberate pass to inventory which features are actually wired end-to-end vs. UI-only before shipping further work on top of them.
4. **Password strength is unenforced at every layer that touches it** (`AUTH-04`, `FE-09`, `FE-10`) — a single shared validation utility (frontend + backend) would close all three at once.
5. **Global + local error handling both fire on every request** (`FE-01`) — needs a single ownership decision (either the interceptor OR local handlers show UI, not both).

---

## Verified clean (checked explicitly, no issue found — for reviewer confidence, not to be re-audited)

- Paystack webhook signature verification: proper HMAC-SHA512 + timing-safe compare.
- `payments.py` `verify_and_apply`: correctly checks transaction ownership before acting; idempotent via unique `provider_reference`.
- Fernet encryption key has a hard startup guard against the public default in production.
- No SQL injection risk anywhere reviewed (all parameterized ORM/Core queries).
- Storage path traversal (`storage.py:_resolve`) and upload filename traversal (`analyze.py`) are both correctly guarded.
- `uploads.py`/`mapping.py` CSV/PDF endpoints: content-type spoofing already fixed (filename extension is sole gate); IDOR-safe (merchant_id always derived from the resource, never client-resupplied).
- No `eval`/`exec`/`pickle` usage anywhere in either backend or frontend.
- No `dangerouslySetInnerHTML`/`innerHTML`/hardcoded secrets found in the frontend.
- Upload flow race-condition handling (generation tokens + `AbortController`) is well-designed.
- Login/Register/Accept-invite correctly guard against double-submission.

---

## Next steps

1. Waiting on a second, externally-sourced issues file from the user.
2. Once received: cross-reference against the IDs above, de-duplicate, merge into one combined backlog (reusing these IDs where the same issue was independently found, adding new IDs where it wasn't).
3. Triage combined list by severity, agree on fix order, then begin implementation — starting with the `critical` items (`AUTH-01`, `AUTH-02`, `AUTH-03`, `PAY-01`) since those are outright auth-bypass/account-takeover/cross-tenant-data-exposure paths.
