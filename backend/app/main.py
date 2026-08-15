from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import DEFAULT_FERNET_KEY, settings
from app.database import engine
from app.models import Base
from app.routes.analyze import router as analyze_router
from app.routes.auth import router as auth_router
from app.routes.bank import router as bank_router
from app.routes.ecommerce import router as ecommerce_router
from app.routes.internal import router as internal_router
from app.routes.mapping import router as mapping_router
from app.routes.notifications import router as notifications_router
from app.routes.payments import router as payments_router
from app.routes.plans import router as plans_router
from app.routes.privacy import router as privacy_router
from app.routes.reconciliation import router as reconciliation_router
from app.routes.team import router as team_router
from app.routes.uploads import router as uploads_router
from app.routes.webhooks import router as webhooks_router
from app.services.redis_client import redis_client

load_dotenv()

app = FastAPI(title="Scanwick API")

# ── CORS ──────────────────────────────────────────────────────────────────────
_allow_origins = ["https://scanwick.com", "https://www.scanwick.com"]
# quick-tunnel origin regex is dev_mode-gated and only matches trycloudflare.com
# — used for temporarily sharing a local dev instance (e.g. client testing)
# via `cloudflared tunnel --url`, whose subdomain is random per run so a
# fixed origin can't be listed above. Never active outside dev_mode.
_allow_origin_regex = None
if settings.dev_mode:
    # Include both localhost and 127.0.0.1 — browsers treat them as different
    # origins, and Vite may be opened on either depending on --host / the URL bar.
    _allow_origins += [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    _allow_origin_regex = r"https://.*\.trycloudflare\.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiter (Redis-backed, per-IP: 10 requests / 60s on /api/auth/*) ─────
# Backed by the same shared Redis client as the OAuth-state/OTP-lockout/
# provisioning-lock fixes (app/services/redis_client.py) rather than an
# in-process dict, so the limit is enforced correctly across multiple
# backend replicas, not just within a single process.
_RATE_LIMIT = 10
_RATE_WINDOW = 60  # seconds


@app.middleware("http")
async def rate_limit_auth(request: Request, call_next):
    if not request.url.path.startswith("/api/auth/"):
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    count = redis_client.incr_with_ttl(f"ratelimit:auth:{ip}", _RATE_WINDOW)
    if count > _RATE_LIMIT:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Please wait a moment and try again."},
        )

    return await call_next(request)


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(bank_router)
app.include_router(ecommerce_router)
app.include_router(internal_router)
app.include_router(mapping_router)
app.include_router(notifications_router)
app.include_router(payments_router)
app.include_router(plans_router)
app.include_router(privacy_router)
app.include_router(reconciliation_router)
app.include_router(team_router)
app.include_router(uploads_router)
app.include_router(webhooks_router)

# Local file storage backend serves uploaded files from here; the S3 backend
# returns presigned URLs directly and doesn't need this mount.
if settings.storage_backend == "local":
    app.mount("/static/uploads", StaticFiles(directory=settings.local_storage_dir), name="uploads")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    # Refuse to boot outside dev with the public, committed-in-source default
    # Fernet key — see app/config.py's DEFAULT_FERNET_KEY and
    # app/services/encryption.py, which only warns (doesn't fail) when
    # dev_mode is True, since local dev must keep working with zero setup.
    if not settings.dev_mode and settings.fernet_key == DEFAULT_FERNET_KEY:
        raise RuntimeError(
            "FERNET_KEY is unset (or still the public dev-only default) while "
            "dev_mode=False. Refusing to start — encrypted fields would not "
            "actually be confidential. Set a real FERNET_KEY before deploying."
        )

    # FP-A2: same reasoning as the Fernet guard above, for the JWT signing
    # key. Unlike Fernet, there was previously no check at all here — a
    # missing/misspelled SECRET_KEY in the deploy environment silently fell
    # back to the public, committed-in-source default, and every JWT
    # (including access tokens) would validate against a key anyone reading
    # the source already has. Also enforces a minimum length so a short,
    # low-entropy value set by mistake can't slip through either.
    if not settings.dev_mode and (settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32):
        raise RuntimeError(
            "SECRET_KEY is unset (or still the public default / too short) while "
            "dev_mode=False. Refusing to start — JWTs would be forgeable by "
            "anyone who has read the source. Set a real SECRET_KEY (32+ chars) "
            "before deploying."
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
