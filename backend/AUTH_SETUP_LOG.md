# Auth Setup Log (Local + Cloud)

Date: 2026-04-16
Project: Scanwick backend auth migration and setup

## 1. Summary

This document records the auth-related migration and setup completed for the backend, including:

- FastAPI to Flask app bootstrap changes
- Auth route/runtime fixes
- Python dependency updates
- Local PostgreSQL setup and troubleshooting
- Railway PostgreSQL cloud setup
- Postman testing notes
- Terminal commands used

## 2. Code Changes Applied

### 2.1 Backend App Entrypoint

File: `app/main.py`

Changes made:

- Replaced FastAPI app initialization with Flask app initialization
- Set Flask secret key from environment variable
- Added Flask-CORS configuration
- Registered auth blueprint via `register_auth(app)`
- Kept health endpoint as Flask route

Current behavior:

- App runs as Flask on `http://127.0.0.1:5000`
- Auth blueprint is mounted and active

### 2.2 Auth Routes Module

File: `app/routes/auth.py`

Changes made:

- Added missing import:
  - `import psycopg2.extras`

Reason:

- `_db_read()` and `_db_write()` use `psycopg2.extras.RealDictCursor`
- Without the import, register/login routes produced:
  - `AttributeError: module 'psycopg2' has no attribute 'extras'`

### 2.3 Python Dependencies

File: `pyproject.toml`

Changes made:

- Replaced FastAPI stack with Flask stack
- Added required runtime libraries for current auth implementation
- Added missing PostgreSQL driver dependency

Relevant dependency state after updates:

- `flask`
- `flask-cors`
- `authlib`
- `bcrypt`
- `resend`
- `psycopg2-binary`
- `python-dotenv`

### 2.4 Environment Configuration

File: `.env`

Changes made:

- Switched `DATABASE_URL` from local Postgres to Railway Postgres URL
- Added SSL query parameter for cloud DB connection:
  - `?sslmode=require`

Important:

- Secrets are intentionally not duplicated in this document
- Rotate database credentials if they were exposed in logs or chat

## 3. Database Setup

### 3.1 Local PostgreSQL (initial setup)

Initial setup was done on local machine to validate auth flow quickly.

Completed:

- PostgreSQL installed and service enabled
- Local DB/user created
- Initial local auth tables created

### 3.2 Cloud PostgreSQL on Railway (current target)

Railway DB URL was configured in `.env`.

Schema created on cloud DB for current auth code:

```sql
CREATE TABLE IF NOT EXISTS accounts (
  id SERIAL PRIMARY KEY,
  email VARCHAR(254) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL DEFAULT '',
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  otp TEXT,
  otp_expires TIMESTAMPTZ,
  google_id TEXT,
  payment_type TEXT DEFAULT 'free',
  payment_expires_at TIMESTAMPTZ,
  research_plan TEXT,
  research_access_expires TIMESTAMPTZ,
  payment_ref TEXT
);

CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
CREATE INDEX IF NOT EXISTS idx_accounts_otp ON accounts(otp);
```

Verification completed:

- Cloud DB connectivity successful
- `accounts` table exists
- Indexes exist

## 4. Key Runtime Issues Found and Fixed

### Issue A: CSRF check failed in register

Cause:

- Token/cookie mismatch or missing session continuity
- Postman body initially sent as `form-data` instead of `raw JSON`

Fix:

- Use `GET /api/csrf-token` first
- Use same cookie session for subsequent POST
- Send `X-CSRF-Token` header with token value
- Send register body as raw JSON

### Issue B: 500 `psycopg2.extras` attribute error

Cause:

- Missing import in `auth.py`

Fix:

- Added `import psycopg2.extras`

### Issue C: 500 `relation "accounts" does not exist`

Cause:

- Current auth code queries `accounts` table
- Table absent in DB

Fix:

- Created `accounts` table and indexes

### Issue D: Flask server not starting (`Address already in use`)

Cause:

- Existing process already bound to port 5000

Fix:

- Identified and killed old listener processes
- Restarted Flask server

## 5. Postman Request Requirements (Auth)

For protected POST endpoints (register/login/verify-otp/etc):

Required headers:

- `Content-Type: application/json`
- `Origin: http://localhost:5000` (or valid allowed origin)
- `X-CSRF-Token: <value from /api/csrf-token>`

Required session behavior:

- Keep cookies enabled in Postman
- Reuse same session between CSRF fetch and protected POST requests

Register request body (example):

```json
{
  "email": "user@example.com",
  "password": "StrongPass1"
}
```

## 6. Terminal Commands Executed

The following commands (or equivalent forms) were run during setup.

### 6.1 Local PostgreSQL install/service

```bash
sudo apt update && sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql --no-pager
```

### 6.2 Local DB/user creation and fixes

```bash
sudo -u postgres psql << EOF
CREATE USER bizscope WITH PASSWORD '***';
CREATE DATABASE bizscope_db OWNER bizscope;
GRANT ALL PRIVILEGES ON DATABASE bizscope_db TO bizscope;
EOF
```

Collation refresh + DB creation follow-up:

```bash
sudo -u postgres psql << EOF
ALTER DATABASE postgres REFRESH COLLATION VERSION;
ALTER DATABASE template1 REFRESH COLLATION VERSION;
CREATE DATABASE bizscope_db OWNER bizscope;
EOF
```

Grants:

```bash
sudo -u postgres psql bizscope_db -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bizscope; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bizscope;"
```

### 6.3 Poetry environment/dependencies

```bash
poetry --version
poetry install
poetry lock && poetry install
poetry env info --path
poetry run python -c "import flask,authlib,bcrypt,psycopg2; print('deps-ok')"
poetry run flask --app app.main routes
```

### 6.4 App syntax checks

```bash
python -m py_compile app/routes/auth.py
python -m py_compile app/main.py
```

### 6.5 Flask process/port management

```bash
lsof -iTCP:5000 -sTCP:LISTEN -n -P
kill <pid1> <pid2>
poetry -C /home/shoaibahmed/scanwick/scanwick/backend run flask --app app.main run --debug
```

### 6.6 Cloud DB schema init (Railway)

Executed via Python using `DATABASE_URL` from `.env`:

```bash
poetry run python - <<'PY'
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env')
with psycopg2.connect(os.environ['DATABASE_URL']) as conn:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
          id SERIAL PRIMARY KEY,
          email VARCHAR(254) UNIQUE NOT NULL,
          password_hash TEXT NOT NULL DEFAULT '',
          verified BOOLEAN NOT NULL DEFAULT FALSE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          otp TEXT,
          otp_expires TIMESTAMPTZ,
          google_id TEXT,
          payment_type TEXT DEFAULT 'free',
          payment_expires_at TIMESTAMPTZ,
          research_plan TEXT,
          research_access_expires TIMESTAMPTZ,
          payment_ref TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
        CREATE INDEX IF NOT EXISTS idx_accounts_otp ON accounts(otp);
        """)
    conn.commit()
print('railway schema initialized')
PY
```

Connectivity verification:

```bash
poetry run python - <<'PY'
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env')
with psycopg2.connect(os.environ['DATABASE_URL']) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM accounts;')
        print(cur.fetchone()[0])
PY
```

## 7. Current Status

- Flask backend bootstrapped and route map available
- Cloud PostgreSQL on Railway connected
- Required `accounts` schema present
- Register endpoint validated successfully after fixes

## 8. Recommended Next Steps

- Replace placeholder values for:
  - `RESEND_API_KEY`
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
- Verify sender domain in Resend (or use a valid test sender)
- Rotate Railway DB password if exposed
- Add migration tooling (Alembic or SQL migration scripts) to avoid manual schema drift
