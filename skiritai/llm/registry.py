"""LLM provider registry with auto-detection."""
from __future__ import annotations

import os

from skiritai.logger import logger
from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .openai_provider import OpenAIProvider

# Registry of provider classes, keyed by name string
_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(name: str | None = None) -> LLMProvider:
    """Get an LLM provider instance.

    Resolution order:
    1. If name is given, use that provider (must exist and be available)
    2. If LLM_PROVIDER env var is set, use that
    3. Auto-detect: first available provider in registry order
    """
    if name is None:
        name = os.getenv("LLM_PROVIDER")

    if name:
        provider_cls = _PROVIDERS.get(name.lower())
        if not provider_cls:
            raise ValueError(
                f"Unknown LLM provider: {name}. "
                f"Available: {list(_PROVIDERS.keys())}"
            )
        if not provider_cls.is_available():
            raise ValueError(
                f"LLM provider '{name}' is not configured. "
                f"Check required environment variables."
            )
        logger.info(f"[LLM] Using provider: {name}")
        return provider_cls.from_env()

    # Auto-detect
    for pname, pcls in _PROVIDERS.items():
        if pcls.is_available():
            logger.info(f"[LLM] Auto-detected provider: {pname}")
            return pcls.from_env()

    raise ValueError(
        "No LLM provider available. Set LLM_PROVIDER and corresponding "
        "API key environment variables."
    )


def register_provider(name: str, provider_cls: type[LLMProvider]) -> None:
    """Register a custom LLM provider."""
    _PROVIDERS[name.lower()] = provider_cls
