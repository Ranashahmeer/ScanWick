"""Shared Redis helper.

Several fixes from the auth/security bug audit need a piece of state that's
visible across worker processes/replicas (a distributed lock, an OAuth CSRF
state store, a per-account OTP lockout counter, a per-IP rate limiter). All
of them reuse this one client rather than each opening its own connection
with its own connection string — and all of them reuse `celery_broker_url`
(see `app/celery_app.py` / `app/config.py`) as the connection URL, since a
Redis instance is already a required piece of this deployment's
infrastructure for Celery.

Deliberately env-var driven only (`CELERY_BROKER_URL`, which every existing
deployment topology for this app already has to set) — nothing here assumes
a specific cloud provider or hosting platform.

Falls back to a per-process in-memory store when Redis is unreachable,
logging a warning once. That fallback exists purely so local development
and the test suite work without a live Redis server — it is NOT safe across
multiple processes or replicas (locks/rate-limits/counters won't be shared),
so any real multi-replica deployment must point `CELERY_BROKER_URL` at a
reachable Redis instance.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Optional

import redis as redis_lib

from app.config import settings

logger = logging.getLogger("app.redis_client")

_RETRY_COOLDOWN_SECONDS = 5.0

# Atomic compare-and-delete, so a lock is only released by whoever holds the
# token that acquired it (avoids releasing a lock some other holder now owns
# after the original owner's TTL already expired).
_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class _InMemoryFallback:
    """Minimal in-process stand-in for the subset of Redis operations this
    module needs. Thread-safe; TTLs are enforced lazily on access."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, tuple[str, Optional[float]]] = {}
        self._counters: dict[str, tuple[int, Optional[float]]] = {}

    @staticmethod
    def _expired(expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.monotonic() >= expires_at

    def set_nx(self, key: str, value: str, ttl_seconds: float) -> bool:
        with self._lock:
            existing = self._values.get(key)
            if existing is not None and not self._expired(existing[1]):
                return False
            self._values[key] = (value, time.monotonic() + ttl_seconds)
            return True

    def compare_and_delete(self, key: str, value: str) -> bool:
        with self._lock:
            existing = self._values.get(key)
            if existing is not None and not self._expired(existing[1]) and existing[0] == value:
                del self._values[key]
                return True
            return False

    def set_value(self, key: str, value: str, ttl_seconds: float) -> None:
        with self._lock:
            self._values[key] = (value, time.monotonic() + ttl_seconds)

    def get_value(self, key: str) -> Optional[str]:
        with self._lock:
            existing = self._values.get(key)
            if existing is None or self._expired(existing[1]):
                self._values.pop(key, None)
                return None
            return existing[0]

    def pop_value(self, key: str) -> Optional[str]:
        with self._lock:
            existing = self._values.get(key)
            if existing is None:
                return None
            del self._values[key]
            if self._expired(existing[1]):
                return None
            return existing[0]

    def delete_value(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)
            self._counters.pop(key, None)

    def incr_with_ttl(self, key: str, ttl_seconds: float) -> int:
        with self._lock:
            existing = self._counters.get(key)
            if existing is None or self._expired(existing[1]):
                count = 1
                self._counters[key] = (count, time.monotonic() + ttl_seconds)
            else:
                count = existing[0] + 1
                self._counters[key] = (count, existing[1])
            return count

    def get_counter(self, key: str) -> int:
        with self._lock:
            existing = self._counters.get(key)
            if existing is None or self._expired(existing[1]):
                self._counters.pop(key, None)
                return 0
            return existing[0]


class RedisClient:
    """Facade over a real Redis connection with an in-memory fallback.
    Every method degrades to the in-process store if Redis is unreachable,
    so callers never need their own fallback logic."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._client: Optional["redis_lib.Redis"] = None
        self._last_connect_attempt = 0.0
        self._warned = False
        self._fallback = _InMemoryFallback()
        self._release_script = None

    def _redis_url(self) -> str:
        return settings.celery_broker_url

    def _connect(self) -> Optional["redis_lib.Redis"]:
        if self._client is not None:
            return self._client
        now = time.monotonic()
        with self._lock:
            if self._client is not None:
                return self._client
            if now - self._last_connect_attempt < _RETRY_COOLDOWN_SECONDS:
                return None
            self._last_connect_attempt = now
            try:
                candidate = redis_lib.Redis.from_url(
                    self._redis_url(), socket_connect_timeout=1, socket_timeout=1
                )
                candidate.ping()
                self._client = candidate
                self._release_script = candidate.register_script(_RELEASE_LOCK_SCRIPT)
                self._warned = False
                return self._client
            except Exception as exc:  # noqa: BLE001 - any failure means "use the fallback"
                if not self._warned:
                    logger.warning(
                        "Redis unreachable at %s (%s) — falling back to an in-process "
                        "store for locks/rate-limits/OTP state. This fallback is NOT "
                        "safe across multiple processes or replicas; point "
                        "CELERY_BROKER_URL at a reachable Redis instance before "
                        "running more than one backend process.",
                        self._redis_url(),
                        exc,
                    )
                    self._warned = True
                return None

    # ── Locking (SET NX PX / atomic compare-and-delete release) ────────────

    def acquire_lock(self, key: str, ttl_seconds: float) -> Optional[str]:
        """Attempts to acquire a lock, returning an opaque token to pass to
        `release_lock` on success, or None if the lock is already held."""
        token = uuid.uuid4().hex
        client = self._connect()
        if client is not None:
            try:
                acquired = client.set(key, token, nx=True, px=int(ttl_seconds * 1000))
                return token if acquired else None
            except Exception:  # noqa: BLE001
                self._client = None  # force a reconnect attempt next time
        acquired = self._fallback.set_nx(key, token, ttl_seconds)
        return token if acquired else None

    def release_lock(self, key: str, token: str) -> None:
        client = self._connect()
        if client is not None:
            try:
                self._release_script(keys=[key], args=[token])
                return
            except Exception:  # noqa: BLE001
                self._client = None
        self._fallback.compare_and_delete(key, token)

    # ── Simple key/value with TTL (OAuth CSRF state, etc.) ──────────────────

    def set_value(self, key: str, value: str, ttl_seconds: float) -> None:
        client = self._connect()
        if client is not None:
            try:
                client.set(key, value, ex=max(1, int(ttl_seconds)))
                return
            except Exception:  # noqa: BLE001
                self._client = None
        self._fallback.set_value(key, value, ttl_seconds)

    def get_value(self, key: str) -> Optional[str]:
        client = self._connect()
        if client is not None:
            try:
                raw = client.get(key)
                return raw.decode() if isinstance(raw, bytes) else raw
            except Exception:  # noqa: BLE001
                self._client = None
        return self._fallback.get_value(key)

    def pop_value(self, key: str) -> Optional[str]:
        """Atomic get-and-delete — used for single-use tokens like OAuth state."""
        client = self._connect()
        if client is not None:
            try:
                raw = client.getdel(key)
                return raw.decode() if isinstance(raw, bytes) else raw
            except Exception:  # noqa: BLE001
                self._client = None
        return self._fallback.pop_value(key)

    def delete_value(self, key: str) -> None:
        client = self._connect()
        if client is not None:
            try:
                client.delete(key)
                return
            except Exception:  # noqa: BLE001
                self._client = None
        self._fallback.delete_value(key)

    # ── Counters with TTL (rate limiting, OTP-attempt lockout) ──────────────

    def incr_with_ttl(self, key: str, ttl_seconds: float) -> int:
        """Increments `key`, setting its expiry only the first time it's
        created (so the window is fixed from first-increment, not renewed
        on every call)."""
        client = self._connect()
        if client is not None:
            try:
                with client.pipeline() as pipe:
                    pipe.incr(key)
                    count = pipe.execute()[0]
                if count == 1:
                    client.expire(key, max(1, int(ttl_seconds)))
                return count
            except Exception:  # noqa: BLE001
                self._client = None
        return self._fallback.incr_with_ttl(key, ttl_seconds)

    def get_counter(self, key: str) -> int:
        client = self._connect()
        if client is not None:
            try:
                raw = client.get(key)
                return int(raw) if raw is not None else 0
            except Exception:  # noqa: BLE001
                self._client = None
        return self._fallback.get_counter(key)


redis_client = RedisClient()
