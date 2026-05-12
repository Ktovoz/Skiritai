"""Unit tests for llm_retry — retry logic with exponential backoff."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# ============================================================
# 1. _is_rate_limited Tests
# ============================================================

class TestIsRateLimited:
    """Test _is_rate_limited() detects rate-limit / server errors."""

    def test_openai_429(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("Error code: 429 — Rate limit exceeded")
        assert _is_rate_limited(exc) is True

    def test_openai_rate_limit_underscore(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("rate_limit exceeded for organization")
        assert _is_rate_limited(exc) is True

    def test_openai_rate_limit_space(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("Rate limit hit")
        assert _is_rate_limited(exc) is True

    def test_anthropic_overloaded(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("Anthropic API is overloaded")
        assert _is_rate_limited(exc) is True

    def test_anthropic_capacity(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("Capacity exceeded")
        assert _is_rate_limited(exc) is True

    def test_503_server_error(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("503 server error")
        assert _is_rate_limited(exc) is True

    def test_503_code(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("Service unavailable: 503")
        assert _is_rate_limited(exc) is True

    def test_server_error_text(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("Internal server error")
        assert _is_rate_limited(exc) is True

    def test_normal_exception_is_not_rate_limited(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = ValueError("Invalid input")
        assert _is_rate_limited(exc) is False

    def test_unrelated_http_400(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("Bad request: 400")
        assert _is_rate_limited(exc) is False

    def test_case_insensitive(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("RATE LIMIT HIT")
        assert _is_rate_limited(exc) is True

    def test_empty_message(self):
        from skiritai.core.llm_retry import _is_rate_limited
        exc = Exception("")
        assert _is_rate_limited(exc) is False


# ============================================================
# 2. _is_retryable Tests
# ============================================================

class TestIsRetryable:
    """Test _is_retryable() classification of exceptions."""

    def test_connection_error(self):
        from skiritai.core.llm_retry import _is_retryable
        assert _is_retryable(ConnectionError("refused")) is True

    def test_timeout_error(self):
        from skiritai.core.llm_retry import _is_retryable
        assert _is_retryable(TimeoutError("timed out")) is True

    def test_async_timeout_error(self):
        from skiritai.core.llm_retry import _is_retryable
        assert _is_retryable(asyncio.TimeoutError()) is True

    def test_rate_limit_is_retryable(self):
        from skiritai.core.llm_retry import _is_retryable
        exc = Exception("429 rate limit exceeded")
        assert _is_retryable(exc) is True

    def test_value_error_not_retryable(self):
        from skiritai.core.llm_retry import _is_retryable
        assert _is_retryable(ValueError("bad input")) is False

    def test_type_error_not_retryable(self):
        from skiritai.core.llm_retry import _is_retryable
        assert _is_retryable(TypeError("wrong type")) is False

    def test_chained_cause_is_retryable(self):
        from skiritai.core.llm_retry import _is_retryable
        inner = ConnectionError("refused")
        outer = RuntimeError("wrapped error")
        outer.__cause__ = inner
        assert _is_retryable(outer) is True

    def test_chained_context_is_retryable(self):
        from skiritai.core.llm_retry import _is_retryable
        inner = TimeoutError("timed out")
        outer = RuntimeError("wrapped error")
        outer.__context__ = inner
        assert _is_retryable(outer) is True

    def test_non_retryable_cause(self):
        from skiritai.core.llm_retry import _is_retryable
        inner = ValueError("bad")
        outer = RuntimeError("wrapped error")
        outer.__cause__ = inner
        assert _is_retryable(outer) is False

    def test_deeply_nested_retryable(self):
        from skiritai.core.llm_retry import _is_retryable
        inner = ConnectionError("refused")
        mid = RuntimeError("mid")
        mid.__cause__ = inner
        outer = Exception("outer")
        outer.__cause__ = mid
        assert _is_retryable(outer) is True


# ============================================================
# 3. _calculate_delay Tests
# ============================================================

class TestCalculateDelay:
    """Test _calculate_delay() exponential backoff with jitter."""

    def test_attempt_0_minimum(self):
        from skiritai.core.llm_retry import _calculate_delay
        # With jitter (50%-100%), delay should be between 0.5*base and base
        base = 2.0
        for _ in range(100):
            delay = _calculate_delay(0, base, 60.0)
            assert 0.5 * base <= delay <= base

    def test_attempt_1_doubles(self):
        from skiritai.core.llm_retry import _calculate_delay
        base = 2.0
        for _ in range(100):
            delay = _calculate_delay(1, base, 60.0)
            assert base <= delay <= 2 * base

    def test_attempt_2_quadruples(self):
        from skiritai.core.llm_retry import _calculate_delay
        base = 2.0
        for _ in range(100):
            delay = _calculate_delay(2, base, 60.0)
            assert 2 * base <= delay <= 4 * base

    def test_capped_at_max_delay(self):
        from skiritai.core.llm_retry import _calculate_delay
        max_delay = 5.0
        for attempt in range(10):
            delay = _calculate_delay(attempt, 2.0, max_delay)
            assert delay <= max_delay

    def test_jitter_produces_variety(self):
        from skiritai.core.llm_retry import _calculate_delay
        delays = {_calculate_delay(2, 2.0, 60.0) for _ in range(50)}
        # With jitter, we should get more than one unique value
        assert len(delays) > 1

    def test_always_positive(self):
        from skiritai.core.llm_retry import _calculate_delay
        for attempt in range(10):
            delay = _calculate_delay(attempt, 2.0, 60.0)
            assert delay > 0

    def test_base_delay_1(self):
        from skiritai.core.llm_retry import _calculate_delay
        for _ in range(50):
            delay = _calculate_delay(0, 1.0, 60.0)
            assert 0.5 <= delay <= 1.0


# ============================================================
# 4. retry_async Tests
# ============================================================

class TestRetryAsync:
    """Test retry_async() execution with retries."""

    async def test_success_on_first_try(self):
        from skiritai.core.llm_retry import retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_async(factory, max_retries=3, base_delay=0.01, max_delay=0.1)
        assert result == "ok"
        assert call_count == 1

    async def test_success_after_retry(self):
        from skiritai.core.llm_retry import retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("refused")
            return "ok"

        result = await retry_async(factory, max_retries=3, base_delay=0.01, max_delay=0.1)
        assert result == "ok"
        assert call_count == 3

    async def test_exhausts_retries_raises(self):
        from skiritai.core.llm_retry import retry_async

        async def factory():
            raise ConnectionError("always fails")

        with pytest.raises(ConnectionError, match="always fails"):
            await retry_async(factory, max_retries=2, base_delay=0.01, max_delay=0.1)

    async def test_non_retryable_raises_immediately(self):
        from skiritai.core.llm_retry import retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            await retry_async(factory, max_retries=3, base_delay=0.01, max_delay=0.1)

        # Should not retry for non-retryable errors
        assert call_count == 1

    async def test_rate_limit_retried(self):
        from skiritai.core.llm_retry import retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 rate limit exceeded")
            return "recovered"

        result = await retry_async(factory, max_retries=2, base_delay=0.01, max_delay=0.1)
        assert result == "recovered"
        assert call_count == 2

    async def test_timeout_retried(self):
        from skiritai.core.llm_retry import retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError()
            return "done"

        result = await retry_async(factory, max_retries=2, base_delay=0.01, max_delay=0.1)
        assert result == "done"

    async def test_max_retries_zero_no_retry(self):
        from skiritai.core.llm_retry import retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError):
            await retry_async(factory, max_retries=0, base_delay=0.01, max_delay=0.1)
        assert call_count == 1

    async def test_max_retries_zero_success(self):
        from skiritai.core.llm_retry import retry_async

        async def factory():
            return "immediate"

        result = await retry_async(factory, max_retries=0, base_delay=0.01, max_delay=0.1)
        assert result == "immediate"


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
