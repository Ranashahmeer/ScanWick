from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

# Dev-only default Fernet key — a real, valid key so encryption works out of
# the box locally with zero setup. Public (it's committed in source), so it
# must never be used outside dev_mode=True. See Settings.fernet_key and the
# startup check in app/main.py that refuses to boot with this value when
# dev_mode is False.
DEFAULT_FERNET_KEY = "nwOWRlHiJJ2SscyrRrmOi9cQzrlSOqcscJ12Kgg4DCg="


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./app.db"
    local_database_url: str = "sqlite+aiosqlite:///./app.db"
    # Reads from SECRET_KEY or FLASK_SECRET_KEY — whichever is present in .env
    secret_key: str = Field(
        default="change-me-in-production",
        validation_alias=AliasChoices("SECRET_KEY", "FLASK_SECRET_KEY"),
    )
    algorithm: str = "HS256"
    # FP-A4: shortened from 30 -> 15. Refresh token TTL (7 days) is
    # unaffected and remains the long-lived credential.
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    use_remote_db_in_dev: bool = False
    dev_mode: bool = Field(default=False, validation_alias=AliasChoices("DEV_MODE", "dev_mode"))
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    frontend_url: str = "http://localhost:5173"
    resend_api_key: str = ""
    resend_from_email: str = ""
    bcrypt_rounds: int = Field(default=12, validation_alias=AliasChoices("BCRYPT_ROUNDS", "bcrypt_rounds"))
    gemini_api_key: str = Field(default="", validation_alias=AliasChoices("GEMINI_API_KEY", "gemini_api_key"))
    gemini_model: str = Field(
        default="gemini-2.5-flash", validation_alias=AliasChoices("GEMINI_MODEL", "gemini_model")
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("CELERY_BROKER_URL", "celery_broker_url"),
    )
    # Deliberately a different logical Redis DB than the broker (/1, not /0)
    # so task messages and result data don't share a keyspace.
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        validation_alias=AliasChoices("CELERY_RESULT_BACKEND", "celery_result_backend"),
    )
    # Local-dev convenience: runs ingestion tasks synchronously in-process
    # instead of publishing to Redis/needing a separate Celery worker
    # running at all. Only ever takes effect when dev_mode is also True
    # (see celery_app.py) — production always uses the real queue
    # regardless of this value, no matter how it's set.
    celery_task_always_eager: bool = Field(
        default=True,
        validation_alias=AliasChoices("CELERY_TASK_ALWAYS_EAGER", "celery_task_always_eager"),
    )
    # "local" (filesystem, served from this app) or "s3" (real S3 in prod, or
    # MinIO in dev by pointing s3_endpoint_url at the MinIO endpoint)
    storage_backend: str = Field(
        default="local", validation_alias=AliasChoices("STORAGE_BACKEND", "storage_backend")
    )
    local_storage_dir: str = Field(
        default="./uploads", validation_alias=AliasChoices("LOCAL_STORAGE_DIR", "local_storage_dir")
    )
    backend_base_url: str = Field(
        default="http://localhost:8000", validation_alias=AliasChoices("BACKEND_BASE_URL", "backend_base_url")
    )
    s3_bucket: str = Field(default="scanwick-uploads", validation_alias=AliasChoices("S3_BUCKET", "s3_bucket"))
    s3_region: str = Field(default="us-east-1", validation_alias=AliasChoices("S3_REGION", "s3_region"))
    # Leave blank for real AWS S3; set to a MinIO endpoint (e.g. http://localhost:9000) in dev
    s3_endpoint_url: str = Field(
        default="", validation_alias=AliasChoices("S3_ENDPOINT_URL", "s3_endpoint_url")
    )
    s3_access_key_id: str = Field(
        default="", validation_alias=AliasChoices("S3_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID")
    )
    s3_secret_access_key: str = Field(
        default="", validation_alias=AliasChoices("S3_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY")
    )
    s3_presigned_url_expiry_seconds: int = Field(
        default=3600, validation_alias=AliasChoices("S3_PRESIGNED_URL_EXPIRY_SECONDS", "s3_presigned_url_expiry_seconds")
    )
    # Dev-only default — a real, valid Fernet key so encryption works out of
    # the box locally. MUST be overridden via FERNET_KEY in any shared or
    # production environment, since this value is public (it's in source).
    # Enforced at startup: app/main.py refuses to boot if dev_mode=False and
    # this is still the default value (or unset).
    fernet_key: str = Field(
        default=DEFAULT_FERNET_KEY,
        validation_alias=AliasChoices("FERNET_KEY", "fernet_key"),
    )
    # Mono open banking (Nigeria/Ghana/Kenya) — free startup tier, per spec.
    mono_secret_key: str = Field(default="", validation_alias=AliasChoices("MONO_SECRET_KEY", "mono_secret_key"))

    # Subscription billing — Paystack is the primary provider; Flutterwave is
    # a second, fallback provider `payments.initiate_checkout` automatically
    # retries through if Paystack's API call fails (see app/services/payments.py).
    # Neither key is ever sent to the frontend: both providers use a hosted
    # checkout redirect, so the browser only ever needs the resulting URL.
    paystack_secret_key: str = Field(
        default="", validation_alias=AliasChoices("PAYSTACK_SECRET_KEY", "paystack_secret_key")
    )
    # Paystack "Plan" code for each recurring paid subscription, created
    # once in the Paystack dashboard/API — outside this app's scope.
    paystack_basic_plan_code: str = Field(
        default="", validation_alias=AliasChoices("PAYSTACK_BASIC_PLAN_CODE", "paystack_basic_plan_code")
    )
    paystack_premium_plan_code: str = Field(
        default="", validation_alias=AliasChoices("PAYSTACK_PREMIUM_PLAN_CODE", "paystack_premium_plan_code")
    )
    flutterwave_secret_key: str = Field(
        default="", validation_alias=AliasChoices("FLUTTERWAVE_SECRET_KEY", "flutterwave_secret_key")
    )
    # Flutterwave "payment plan" numeric ID for each recurring paid plan.
    flutterwave_basic_plan_id: str = Field(
        default="", validation_alias=AliasChoices("FLUTTERWAVE_BASIC_PLAN_ID", "flutterwave_basic_plan_id")
    )
    flutterwave_premium_plan_id: str = Field(
        default="", validation_alias=AliasChoices("FLUTTERWAVE_PREMIUM_PLAN_ID", "flutterwave_premium_plan_id")
    )
    # Flutterwave has no HMAC webhook signing — you set an arbitrary secret
    # string in their dashboard and they echo it back verbatim in every
    # webhook call's `verif-hash` header; verification is a direct compare.
    # FLW_WEBHOOK_HASH is the primary/expected env var name; the longer
    # names are accepted too so either convention works.
    flutterwave_webhook_secret_hash: str = Field(
        default="",
        validation_alias=AliasChoices(
            "FLW_WEBHOOK_HASH", "FLUTTERWAVE_WEBHOOK_SECRET_HASH", "flutterwave_webhook_secret_hash"
        ),
    )
    # Monthly price per paid tier — fixed in USD, this is the actual source
    # of truth for what each tier costs. The amount actually charged is
    # computed at checkout time as this USD price converted to NGN kobo at
    # the live rate (see app/services/fx_rates.py) — Paystack/Flutterwave
    # settle in NGN here, not USD, so every checkout re-derives the NGN
    # amount rather than charging a stale hardcoded figure. The Free tier
    # needs no price at all (never checked out).
    basic_plan_price_usd: float = Field(
        default=8.99, validation_alias=AliasChoices("BASIC_PLAN_PRICE_USD", "basic_plan_price_usd")
    )
    premium_plan_price_usd: float = Field(
        default=16.99, validation_alias=AliasChoices("PREMIUM_PLAN_PRICE_USD", "premium_plan_price_usd")
    )
    # Emergency-only fallback USD->NGN rate, used solely if the live rate
    # has never been synced yet AND an on-demand live fetch also fails right
    # at checkout time (see fx_rates.get_current_usd_ngn_rate) — keeps
    # checkout working through a real FX-provider outage instead of hard
    # failing, at the cost of a possibly-stale rate. Update occasionally;
    # this is deliberately never the normal code path.
    fallback_usd_ngn_rate: float = Field(
        default=1500.0, validation_alias=AliasChoices("FALLBACK_USD_NGN_RATE", "fallback_usd_ngn_rate")
    )

    model_config = {
        "extra": "ignore",
        "env_file": ".env",
    }


settings = Settings()
