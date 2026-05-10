"""Retry logic for LLM calls with exponential backoff."""
from __future__ import annotations

import asyncio
import os
from typing import Any

from app.logger import logger

# Default configuration (overridable via env vars)
DEFAULT_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
DEFAULT_BASE_DELAY = float(os.getenv("LLM_RETRY_BASE_DELAY", "2.0"))
DEFAULT_MAX_DELAY = float(os.getenv("LLM_RETRY_MAX_DELAY", "60.0"))

# Exceptions considered transient and worth retrying
_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


def _is_rate_limited(exc: Exception) -> bool:
    """Check if the exception indicates a rate-limit or service-overload error."""
    msg = str(exc).lower()
    # OpenAI-style rate limit
    if "429" in msg or "rate_limit" in msg or "rate limit" in msg:
        return True
    # Anthropic-style overload
    if "overloaded" in msg or "capacity" in msg:
        return True
    # Generic server error
    if "503" in msg or "server error" in msg:
        return True
    return False


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is worth retrying."""
    if isinstance(exc, _RETRYABLE_EXCEPTIONS):
        return True
    if _is_rate_limited(exc):
        return True
    # Check for common LangChain/LangGraph wrapped exceptions
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause and _is_retryable(cause):
        return True
    return False


def _calculate_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Calculate delay with exponential backoff and jitter."""
    import random
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter: random between 50%-100% of calculated delay
    jitter = delay * (0.5 + random.random() * 0.5)
    return jitter


async def retry_async(
    coro_factory: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    operation_name: str = "LLM call",
) -> Any:
    """Execute an async callable with retry logic.

    Args:
        coro_factory: A callable that returns an awaitable (e.g., lambda: agent.astream(...))
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay between retries
        operation_name: Human-readable name for logging

    Returns:
        The result of the coroutine

    Raises:
        The last exception if all retries are exhausted
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc

            if attempt >= max_retries or not _is_retryable(exc):
                raise

            delay = _calculate_delay(attempt, base_delay, max_delay)
            logger.warning(
                f"[Retry] {operation_name} failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"{exc}. Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    raise last_exc  # type: ignore[misc]
