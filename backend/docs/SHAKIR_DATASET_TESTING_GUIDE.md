# Dataset Testing Guide — Ecommerce, Sales, Bank

A stepwise guide for manually testing real datasets against the Scanwick backend
across all three verticals. Written for someone unfamiliar with the codebase —
every command is copy-pasteable.

---

## ⚠️ Important gap to know about before you start

**There is no HTTP endpoint to upload a file yet.** `POST /api/v1/upload/csv` is
referenced by the spec and by `GET /api/v1/upload/{upload_id}/quality-report`'s own
existence, but it was never built — confirmed directly in the code
(`app/services/upload_staging.py`'s own docstring: *"there's still no `POST
/api/v1/upload/csv` endpoint... this expects the CSV already staged locally under
this convention"*).

This isn't something this guide works around silently — it's a real product gap.
**Until that endpoint exists, the only way to actually run a dataset through
ingestion is the manual staging method in Step 4 below** (place the file on disk
under a specific filename, then call the ingestion function directly in a Python
shell). This is a legitimate way to exercise every downstream endpoint and verify
real data end-to-end — it just isn't what a real user would eventually click through
in a UI.

If/when `POST /api/v1/upload/csv` gets built, Step 4 will be replaced by a single
`curl -F file=@yourfile.csv` call. Everything from Step 5 onward (testing the actual
analytics endpoints) doesn't change.

---

## Prerequisites

- Python 3.11 + the project's virtualenv set up (`backend/venv`)
- The datasets you want to test, as CSV files (or a PDF for a bank statement)
- A terminal, and `curl` (or Postman/Insomnia if you prefer — every example below is
  a `curl` command you can adapt)

---

## Step 1 — Start the server

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Leave this running in its own terminal. Confirm it's up:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Swagger UI (browsable list of every endpoint) is at `http://localhost:8000/docs`.

The dev database is a SQLite file at `backend/app.db`. Everything below assumes
you're running against that file — **do not point this at a shared/production
database.**

---

## Step 2 — Register and get an access token

Open a **second terminal** for all the `curl`/Python commands below (keep the server
running in the first one).

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Shakir", "last_name": "Test", "email": "shakir@example.com", "password": "TestPassword123!"}'
```

This sends a verification OTP. **In dev mode (no Resend API key configured, which is
the default), the OTP is never actually emailed — it's printed to the server's
console output instead.** Look at your first terminal (where `uvicorn` is running)
for a line like:

```
[email] Verification OTP for shakir@example.com: 482913
```

Use that 6-digit code here:

```bash
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "shakir@example.com", "otp": "482913", "purpose": "verification"}'
```

This returns:

```json
{"access_token": "eyJ...", "refresh_token": "...", "token_type": "bearer"}
```

**Save the `access_token`.** Every request from here on needs it:

```bash
export TOKEN="eyJ..."   # paste your real access_token
```

Confirm it works:

```bash
curl http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
```

You should see your user profile, including your numeric `id` (almost always `1` if
this is the first account you've registered in a fresh `app.db`). **Note this `id`
down — you'll need it in Step 3.**

---

## Step 3 — Grant yourself access (RBAC roles)

Every analytics endpoint (Ecommerce/Sales/Bank) now enforces real role-based access
control. A freshly registered user has **zero roles** and will get a `403 FORBIDDEN`
on every single analytics endpoint until you grant yourself one. There's no
self-service way to do this yet (no admin UI) — it's a direct database insert.

Pick a **merchant ID** to test with — any UUID works, it just needs to be the *same*
UUID you use consistently for ingestion and for every endpoint call afterward. For
this guide we'll use:

```
11111111-1111-1111-1111-111111111111
```

Run this Python script (adjust `USER_ID` if your `/api/auth/me` showed something
other than `1`). **Use this exact script, not a raw SQL `INSERT`** — SQLAlchemy
stores UUID columns as 32-character hex with no dashes in SQLite, while a
hand-written `INSERT` using the dashed string form (`"1111...1111"`) will silently
insert a row that the app's own queries can never match, leaving you stuck on `403`
with no error to explain why. Going through the ORM (as below) always uses the
right format:

```bash
cd backend
source venv/bin/activate
python3 << 'EOF'
import asyncio
import uuid
from app.database import async_session
from app.models.user_merchant_roles import UserMerchantRole, Vertical

USER_ID = 1
MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

# One row per vertical you want to test. Roles available per vertical:
#   ecommerce: owner | admin | manager | viewer
#   sales:     sales_owner | sales_manager | sales_rep | sales_viewer
#   bank:      bank_owner | bank_admin | loan_officer | bank_viewer
# Use the most permissive role ("owner"-equivalent) to test everything freely.
roles_to_grant = [
    (Vertical.ecommerce, "owner"),
    (Vertical.sales, "sales_owner"),
    (Vertical.bank, "bank_owner"),
]

async def main():
    async with async_session() as db:
        for vertical, role in roles_to_grant:
            db.add(UserMerchantRole(id=uuid.uuid4(), user_id=USER_ID, merchant_id=MERCHANT_ID, vertical=vertical, role=role))
        await db.commit()
    print("Roles granted for merchant_id =", MERCHANT_ID)

asyncio.run(main())
EOF
```

If you re-run this, you'll get a "UNIQUE constraint failed" error — that's expected
(one role per user/merchant/vertical). Delete the old rows first if you need to
change a role:

```bash
python3 -c "
import asyncio
from sqlalchemy import delete
from app.database import async_session
from app.models.user_merchant_roles import UserMerchantRole

async def main():
    async with async_session() as db:
        await db.execute(delete(UserMerchantRole).where(UserMerchantRole.user_id == 1))
        await db.commit()

asyncio.run(main())
"
```

---

## Step 4 — Stage and ingest your datasets

Each vertical needs a slightly different column format. The bank ingestion is
fuzzy-matched (it looks for columns containing keywords like "date", "credit/debit",
"balance", "narration" — it doesn't need exact headers). Ecommerce and Sales expect
the literal export format from a specific source platform.

### 4a. Column formats expected

**Ecommerce** — `source = "shopify_csv"` columns:
`Name, Created at, Total, Currency, Discount Amount, Refunded Amount, Shipping,
Source Name, Lineitem sku, Lineitem quantity, Lineitem price` (optionally
`Lineitem cogs`, `Lineitem return cost`, `Email`)

— or `source = "woocommerce_csv"` columns:
`order_id, order_date, order_total, order_currency, cart_discount, refunded_total,
order_shipping, payment_method, item_sku, item_quantity, item_cost` (optionally
`item_cost_price`, `item_return_cost`, `billing_email`)

**Sales** — pick the `source` matching your CRM export:
- `salesforce_csv`: `Opportunity ID, Opportunity Name, Amount, Opportunity Currency,
  Stage, Created Date, Close Date, Competitor, Lead Source, Discount %, Last
  Modified Date, Loss Reason`
- `hubspot_csv`: `Record ID, Deal Name, Amount, Deal Currency Code, Deal Stage,
  Create Date, Close Date, Original Traffic Source, Last Activity Date, Is Closed
  Won, Is Closed`
- `pipedrive_csv`: `ID, Title, Value, Currency, Stage, Add Time, Expected close
  date, Status, Won time, Lost time, Lost reason, Source channel, Stage change time`
- `zoho_csv`: `Deal Id, Deal Name, Amount, Currency, Stage, Created Time, Closing
  Date, Lead Source, Modified Time`

**Bank** — `source = "generic_csv"` works for any reasonably-named export; the
parser looks for columns matching: a date, a credit/debit or amount indicator, a
running balance, and a narration/description/payee column. If your bank statement
is a **PDF** instead of CSV, use the PDF ingestion path (4d below) — it OCRs the
document expecting roughly `DATE  NARRATION  DEBIT  CREDIT  BALANCE` per line.

### 4b. Stage the file

Ingestion reads files from a fixed local path, named by a UUID you choose yourself.
For each dataset, generate a fresh UUID and copy your file there:

```bash
mkdir -p /tmp/scanwick_uploads

# Example for an ecommerce CSV — repeat with a new UUID for each dataset
UPLOAD_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
echo "Ecommerce upload_id: $UPLOAD_ID"
cp /path/to/your/shopify_orders.csv "/tmp/scanwick_uploads/${UPLOAD_ID}.csv"
```

**Write down each `upload_id` you generate** — you'll need it to check the quality
report afterward.

### 4c. Run ingestion (CSV — ecommerce, sales, bank)

With the server still running in the other terminal, open a **separate** Python
shell in the `backend` directory and call the ingestion function directly. These are
the exact same functions Celery would normally run in the background — calling them
directly just runs them synchronously in your shell instead, with no Celery worker
or Redis required:

```bash
cd backend
source venv/bin/activate
python3
```

```python
MERCHANT_ID = "11111111-1111-1111-1111-111111111111"

# --- Ecommerce ---
from app.services.ecommerce_ingestion import ingest_ecommerce_csv
result = ingest_ecommerce_csv(upload_id="PASTE_YOUR_UPLOAD_ID", merchant_id=MERCHANT_ID, source="shopify_csv")
print(result)

# --- Sales ---
from app.services.sales_ingestion import ingest_sales_csv
result = ingest_sales_csv(upload_id="PASTE_YOUR_UPLOAD_ID", merchant_id=MERCHANT_ID, source="salesforce_csv")
print(result)

# --- Bank (CSV) ---
from app.services.bank_ingestion import ingest_bank_csv
result = ingest_bank_csv(upload_id="PASTE_YOUR_UPLOAD_ID", user_id=MERCHANT_ID, bank_name="Test Bank")
print(result)
```

Each call returns a dict summarizing what it did (rows parsed/rejected) — the same
data you can also read back via the quality-report endpoint in Step 4e. Run each
ingestion you need, one at a time, in this same Python shell.

### 4d. Run ingestion (bank PDF)

Same idea, but with the PDF staged at `/tmp/scanwick_uploads/{upload_id}.pdf`:

```python
from app.services.bank_pdf_ingestion import ingest_bank_pdf
result = ingest_bank_pdf(upload_id="PASTE_YOUR_UPLOAD_ID", user_id=MERCHANT_ID, bank_name="Test Bank")
print(result)
```

### 4e. Check the ingestion result

For every `upload_id` you ran, confirm it actually parsed correctly:

```bash
curl "http://localhost:8000/api/v1/upload/PASTE_YOUR_UPLOAD_ID/quality-report" \
  -H "Authorization: Bearer $TOKEN"
```

Check:
- `status` should be `"ready"` (not `"failed"` or stuck on `"processing"`)
- `rows_parsed` matches roughly how many data rows your CSV actually had
- `rows_rejected` — investigate if this is high relative to `rows_parsed`
- `warnings` — read these; they call out things like missing columns or
  unparseable rows
- `date_range_start`/`date_range_end`/`days_of_history` — sanity-check against
  what you know about the real dataset's date span

**If `status` is `"failed"` or rows_parsed is 0**, your CSV's column headers likely
don't match what the parser expects (4a above) — check the actual header row in
your file against the expected list.

---

## Step 5 — Test every Ecommerce endpoint

Base: `http://localhost:8000/api/v1/ecommerce`. All require
`-H "Authorization: Bearer $TOKEN"` and `?merchant_id=11111111-1111-1111-1111-111111111111`
(some also accept `&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`).

| Endpoint | What to check |
|---|---|
| `GET /dashboard/summary` | `total_orders`, `gross_revenue` roughly match your dataset's real totals |
| `GET /dashboard/revenue` | `gap_breakdown` values sum to `gross_revenue - net_revenue` |
| `GET /diagnostic/profit-leaks` | If your CSV had no COGS data, expect `meta.disabled_features` naming `profit_leak_detector` (not an error) |
| `GET /diagnostic/dead-stock` | SKUs with no sales in 60+ days appear here, if your data has any |
| `GET /diagnostic/return-forensics` | Only meaningful if your dataset has returns |
| `GET /dashboard/sku-matrix` | One row per SKU with revenue/margin |
| `GET /predictive/inventory-forecast` | Needs `sku_inventory` data (current stock) — likely empty/disabled unless you've separately seeded that table |
| `GET /predictive/rfm-segments` | Needs ≥1 order with a resolvable `customer_email`; check `clusters_produced` in the response |
| `GET /predictive/churn-risk` | Needs repeat customers with enough order history |
| `GET /ai/playbook` | Calls Gemini — needs `GEMINI_API_KEY` set in `.env`, or it'll return an empty `recommendations` list (not an error) |
| `POST /predictive/ad-kill-switch/configure` | Body: `{"mode": "auto", "threshold_days": 5}` |
| `POST /predictive/ad-kill-switch/pause` | Body: `{"campaign": "test_campaign"}` |

Example:

```bash
curl "http://localhost:8000/api/v1/ecommerce/dashboard/summary?merchant_id=11111111-1111-1111-1111-111111111111" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 6 — Test every Sales endpoint

Base: `http://localhost:8000/api/v1/sales`. Same auth header, `?merchant_id=...`.

| Endpoint | What to check |
|---|---|
| `GET /diagnostic/data-quality-cost` | `missing_loss_reason_pct`, `missing_stage_history_count` against what you'd expect from your CRM export's completeness |
| `GET /dashboard/pipeline-overview` | `totals.total_pipeline_value`/`total_deal_count` match your open deals |
| `GET /dashboard/rep-leaderboard` | One row per rep, ranked by won value |
| `GET /diagnostic/stage-velocity` | Needs real stage-transition history; if your CRM export has none, expect `data: null` + `disabled_features` naming `stage_velocity` |
| `GET /diagnostic/stagnation-alerts` | Open deals with no activity in 14+ days |
| `GET /predictive/forecast` | `forecast_total`; `confidence_rating` will be `"low"` unless you have 30+ historical closed deals |
| `GET /predictive/rep-trajectory` | Needs deals won in the last 180 days to produce real rows |
| `GET /predictive/slippage` | Same disabled condition as stage-velocity |
| `GET /predictive/win-dna` | Needs ≥20 closed-won deals — below that, expect the exact message `"Win DNA requires 20 closed-won deals. You currently have N."` |
| `GET /reports/quarter-postmortem` | Will say `"report_generated": false` unless you've manually run the post-mortem generation (it's normally Celery-beat-scheduled, monthly) — this is expected, not a bug |
| `GET /ai/playbook` | Same Gemini caveat as ecommerce |
| `POST /deals/{deal_id}/capture-loss-reason` | Only works on a deal whose `status` is `lost`; body: `{"loss_reason": "price"}` (other valid values: `competitor`, `timing`, `no_decision`, `product_fit`, `other`) |

---

## Step 7 — Test every Bank endpoint

Base: `http://localhost:8000/api/v1/bank`. **Uses `account_id`, not `merchant_id`** —
get a real account ID first:

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('app.db')
print(conn.execute(\"SELECT id, bank_name FROM accounts\").fetchall())
"
```

Copy one of the printed account IDs and use it below.

| Endpoint | What to check |
|---|---|
| `GET /dashboard/summary` | `top_payees_by_outflow`/`top_income_sources` look sane against your real statement |
| `GET /diagnostic/income-stability` | Needs ≥3 months of data — below that, expect `disabled_features` naming `income_stability` |
| `GET /diagnostic/abm` | Same 3-month minimum |
| `GET /diagnostic/cashflow-analysis` | `cash_buffer_months`, `business_vs_personal` split |
| `GET /diagnostic/customer-segmentation` | Counterparties grouped by payee name |
| `GET /diagnostic/revenue-patterns` | Needs enough months of data for seasonality; check `seasonality_confidence` |
| `GET /predictive/fraud-risk` | `flags` array — if you granted yourself `bank_owner`/`bank_admin`, you'll see full detail (`transaction_id`, `amount`); if you test as `loan_officer`/`bank_viewer` instead, every flag should have those fields stripped (see Step 8) |
| `GET /predictive/loan-readiness` | `loan_readiness_score`, `creditworthiness_tier`, `disabled_components` for whichever sub-scores lack enough data |
| `GET /predictive/cashflow-forecast` | `daily_forecast` projected balances |
| `GET /ai/lender-brief` | All 6 sections present (`business_overview`, `income_stability`, `cash_flow_analysis`, `loan_readiness_assessment`, `risk_flags`, `lender_recommendation`) + `key_metrics` + `data_source_footnote`; `lender_recommendation` will be empty without `GEMINI_API_KEY` |
| `GET /ai/financial-health-playbook` | Same Gemini caveat |

Example:

```bash
curl "http://localhost:8000/api/v1/bank/dashboard/summary?account_id=PASTE_REAL_ACCOUNT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 8 — RBAC negative testing (optional but recommended)

To actually prove role restrictions work, repeat the role-granting step (Step 3)
with a **second** registered user given a *lower*-privilege role, then confirm they
get denied where expected:

- An `ecommerce: viewer` should get `403` on `POST /predictive/ad-kill-switch/configure`.
- A `sales: sales_rep` should get `403` on `GET /dashboard/rep-leaderboard`, and on
  `GET /predictive/rep-trajectory` should only ever see their **own** row in
  `data.reps` (never another rep's), even if other reps have deals in the same
  dataset. To test this meaningfully, the `sales_rep` role needs a `rep_id` set —
  add `, rep_id` to the INSERT in Step 3 with a real UUID matching a `rep_id` value
  present in your ingested deals.
- A `bank: loan_officer` should see `predictive/fraud-risk`'s `flags` with
  `transaction_id`/`amount`/`description` stripped out — only `flag_type`,
  `severity`, and a couple of aggregate fields should remain per flag.

Every denial returns the standard envelope:
```json
{"success": false, "error": {"code": "FORBIDDEN", "message": "..."}}
```

---

## Step 9 — Edge cases worth specifically trying

- **A dataset with very little history** (under a month, or under 20-30 records) —
  confirm every predictive endpoint that has a stated minimum returns a clean
  `disabled_features` entry or an explicit message, never a 500 error or a
  fabricated-looking number.
- **A dataset with an extreme outlier** (one transaction/order/deal far larger than
  everything else) — confirm it gets flagged as anomalous (`is_anomalous = true` in
  the DB) and excluded from aggregate calculations, not silently included.
- **An empty merchant** (a `merchant_id`/`account_id` with zero ingested data at
  all) — every endpoint should return a clean zeroed/empty response, not an error.

---

## Troubleshooting

- **Every request returns 403 `FORBIDDEN`** → you skipped Step 3, or used the wrong
  `merchant_id`/`account_id` (it must exactly match what you granted yourself a role
  for).
- **401 Unauthorized** → your `$TOKEN` expired or wasn't exported correctly in this
  terminal session — re-run the `export TOKEN=...` line.
- **Ingestion silently does nothing / `quality-report` 404s** → the `upload_id` you
  queried doesn't match the one you actually ran ingestion with — check you copied
  it correctly.
- **AI endpoints (`/ai/*`) return empty recommendations** → expected without a real
  `GEMINI_API_KEY` configured in `.env`; this is documented fallback behavior, not a
  bug.
- **Server console floods with SQL logs** → that's `DEV_MODE`'s SQLAlchemy `echo`
  setting; harmless, just noisy. The OTP line is in there too — search for
  `[email]`.
