"""
=== FILE: backend/ingestion/fingerprint.py ===

SHA-256 fingerprint generation and Redis-backed deduplication.

Redis key schema  : ingestion:fingerprint:{fingerprint}
TTL               : 30 days (2_592_000 seconds)
Failure behaviour : log + allow ingestion to proceed (fail-open)
"""

from __future__ import annotations

import hashlib
from typing import Any

from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

logger = get_logger("ingestion.fingerprint")

# ── Constants ─────────────────────────────────────────────────────────────────
_REDIS_KEY_PREFIX = "ingestion:fingerprint:"
_TTL_SECONDS = 2_592_000  # 30 days


# ── Core functions ─────────────────────────────────────────────────────────────

def generate_fingerprint(text: str) -> str:
    """
    Generate a SHA-256 fingerprint for the given text.

    Processing:
      - Lowercase the text
      - Strip leading/trailing whitespace
      - Encode as UTF-8
      - Return lowercase hex digest (64 characters)

    Args:
        text: Normalised document text.

    Returns:
        64-character lowercase SHA-256 hex string.
    """
    canonical = text.lower().strip()
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    logger.debug(f"Fingerprint generated: {digest[:12]}…")
    return digest


def is_duplicate(fingerprint: str, redis_client: Any) -> bool:
    """
    Check whether a fingerprint already exists in Redis.

    Supports both synchronous and asynchronous Redis clients.
    On any Redis error, logs a warning and returns False (fail-open).

    Args:
        fingerprint: SHA-256 hex digest from generate_fingerprint().
        redis_client: A redis.Redis or redis.asyncio.Redis client.

    Returns:
        True if the key exists (duplicate), False otherwise.
    """
    if redis_client is None:
        log_warning("No Redis client supplied — skipping duplicate check.")
        return False

    key = f"{_REDIS_KEY_PREFIX}{fingerprint}"
    try:
        result = redis_client.exists(key)
        # redis-py returns int; redis.asyncio returns a coroutine — handle both
        if hasattr(result, "__await__"):
            import asyncio
            exists = asyncio.get_event_loop().run_until_complete(result)
        else:
            exists = result

        if exists:
            log_info("Duplicate fingerprint detected.", context={"key": key})
            return True
        return False
    except Exception as exc:
        log_error(
            "Redis exists() call failed — permitting ingestion to proceed.",
            exc=exc,
            context={"fingerprint": fingerprint},
        )
        return False


def register_fingerprint(fingerprint: str, redis_client: Any) -> None:
    """
    Register a fingerprint in Redis with a 30-day TTL.

    On any Redis error, logs a warning but does NOT raise (fail-open).

    Args:
        fingerprint: SHA-256 hex digest.
        redis_client: A redis.Redis or redis.asyncio.Redis client.
    """
    if redis_client is None:
        log_warning("No Redis client supplied — skipping fingerprint registration.")
        return

    key = f"{_REDIS_KEY_PREFIX}{fingerprint}"
    try:
        result = redis_client.set(key, "1", ex=_TTL_SECONDS)
        if hasattr(result, "__await__"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(result)
        log_info(
            "Fingerprint registered in Redis.",
            context={"key": key, "ttl_days": 30},
        )
    except Exception as exc:
        log_error(
            "Redis set() call failed — fingerprint not registered.",
            exc=exc,
            context={"fingerprint": fingerprint},
        )


# ── Async variants ─────────────────────────────────────────────────────────────

async def is_duplicate_async(fingerprint: str, redis_client: Any) -> bool:
    """
    Async version of is_duplicate() for use with redis.asyncio clients.

    Args:
        fingerprint: SHA-256 hex digest.
        redis_client: redis.asyncio.Redis client.

    Returns:
        True if duplicate, False otherwise.
    """
    if redis_client is None:
        log_warning("No Redis client supplied — skipping async duplicate check.")
        return False

    key = f"{_REDIS_KEY_PREFIX}{fingerprint}"
    try:
        exists = await redis_client.exists(key)
        if exists:
            log_info("Duplicate fingerprint detected (async).", context={"key": key})
            return True
        return False
    except Exception as exc:
        log_error(
            "Async Redis exists() failed — permitting ingestion.",
            exc=exc,
            context={"fingerprint": fingerprint},
        )
        return False


async def register_fingerprint_async(fingerprint: str, redis_client: Any) -> None:
    """
    Async version of register_fingerprint() for use with redis.asyncio clients.

    Args:
        fingerprint: SHA-256 hex digest.
        redis_client: redis.asyncio.Redis client.
    """
    if redis_client is None:
        log_warning("No Redis client supplied — skipping async fingerprint registration.")
        return

    key = f"{_REDIS_KEY_PREFIX}{fingerprint}"
    try:
        await redis_client.set(key, "1", ex=_TTL_SECONDS)
        log_info(
            "Fingerprint registered in Redis (async).",
            context={"key": key, "ttl_days": 30},
        )
    except Exception as exc:
        log_error(
            "Async Redis set() failed — fingerprint not registered.",
            exc=exc,
            context={"fingerprint": fingerprint},
        )


class Fingerprint:
    """Compatibility wrapper exposing the legacy fingerprint API."""

    calculate = staticmethod(generate_fingerprint)

    @staticmethod
    async def check_and_register(fingerprint: str, job_id: str | None = None, redis_client: Any = None) -> bool:
        """Return True when the fingerprint already existed in Redis."""
        if job_id is not None and redis_client is None:
            # Legacy route passes job_id as the second positional argument.
            redis_client = None

        is_dup = await is_duplicate_async(fingerprint, redis_client)
        if not is_dup:
            await register_fingerprint_async(fingerprint, redis_client)
        return is_dup


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : generate_fingerprint()        → IngestionOutput.fingerprint
#            is_duplicate_async()          → IngestionOutput.is_duplicate
#            register_fingerprint_async()  → stores key in Redis (30 days)
# Consumed : ingestion/__init__.py  run_ingestion()
