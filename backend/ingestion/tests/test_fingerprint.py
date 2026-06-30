"""
=== FILE: backend/ingestion/tests/test_fingerprint.py ===
Tests for fingerprint.py
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.ingestion.fingerprint import (
    generate_fingerprint,
    is_duplicate,
    register_fingerprint,
    is_duplicate_async,
    register_fingerprint_async,
)


class TestGenerateFingerprint:
    def test_returns_64_char_hex(self):
        fp = generate_fingerprint("Hello world")
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_deterministic(self):
        text = "The user shall log in with their email."
        assert generate_fingerprint(text) == generate_fingerprint(text)

    def test_different_texts_different_fingerprints(self):
        assert generate_fingerprint("abc") != generate_fingerprint("xyz")

    def test_case_insensitive(self):
        """Fingerprint is computed on lowercase text."""
        assert generate_fingerprint("HELLO") == generate_fingerprint("hello")

    def test_strips_whitespace(self):
        """Leading/trailing whitespace stripped before hashing."""
        assert generate_fingerprint("  text  ") == generate_fingerprint("text")

    def test_empty_string(self):
        fp = generate_fingerprint("")
        assert len(fp) == 64

    def test_unicode_text(self):
        fp = generate_fingerprint("こんにちは世界")
        assert len(fp) == 64


class TestIsDuplicate:
    def test_no_redis_client_returns_false(self):
        assert is_duplicate("abc123", None) is False

    def test_existing_key_returns_true(self):
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1

        result = is_duplicate("abc123", mock_redis)
        assert result is True

    def test_missing_key_returns_false(self):
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0

        result = is_duplicate("abc123", mock_redis)
        assert result is False

    def test_redis_exception_returns_false(self):
        """Redis failure is fail-open — must not raise."""
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = ConnectionError("Redis down")

        result = is_duplicate("abc123", mock_redis)
        assert result is False


class TestRegisterFingerprint:
    def test_no_redis_client_does_not_raise(self):
        register_fingerprint("abc123", None)  # must not raise

    def test_calls_set_with_correct_key(self):
        mock_redis = MagicMock()
        mock_redis.set.return_value = True

        register_fingerprint("deadbeef", mock_redis)

        call_args = mock_redis.set.call_args
        assert "ingestion:fingerprint:deadbeef" in call_args[0][0]
        # TTL should be 30 days
        assert call_args[1].get("ex") == 2_592_000 or 2_592_000 in call_args[0]

    def test_redis_exception_does_not_raise(self):
        """Redis failure during registration is fail-open."""
        mock_redis = MagicMock()
        mock_redis.set.side_effect = ConnectionError("Redis down")

        register_fingerprint("abc", mock_redis)  # must not raise


class TestIsDuplicateAsync:
    @pytest.mark.asyncio
    async def test_no_redis_returns_false(self):
        assert await is_duplicate_async("fp", None) is False

    @pytest.mark.asyncio
    async def test_existing_key_returns_true(self):
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)

        result = await is_duplicate_async("fp123", mock_redis)
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_key_returns_false(self):
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        result = await is_duplicate_async("fp123", mock_redis)
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error_returns_false(self):
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(side_effect=ConnectionError("Redis down"))

        result = await is_duplicate_async("fp123", mock_redis)
        assert result is False


class TestRegisterFingerprintAsync:
    @pytest.mark.asyncio
    async def test_no_redis_does_not_raise(self):
        await register_fingerprint_async("fp", None)

    @pytest.mark.asyncio
    async def test_calls_set_with_ttl(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)

        await register_fingerprint_async("deadbeef", mock_redis)

        mock_redis.set.assert_awaited_once()
        call_args = mock_redis.set.call_args
        assert "ingestion:fingerprint:deadbeef" in call_args[0][0]
        assert call_args[1].get("ex") == 2_592_000

    @pytest.mark.asyncio
    async def test_redis_error_does_not_raise(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))

        await register_fingerprint_async("fp", mock_redis)  # must not raise
