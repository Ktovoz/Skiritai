"""Internal LLM configuration data structure.

This module is NOT part of the public API. It serves as an intermediate
representation used by ``create_llm()`` to merge configuration from
multiple sources (env vars, config files, explicit args).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Internal config struct — NOT part of public API."""

    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
