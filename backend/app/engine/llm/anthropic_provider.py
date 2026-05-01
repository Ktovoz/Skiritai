"""Anthropic Claude LLM provider (optional dependency)."""
from __future__ import annotations

import os

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def build(self, model: str | None = None):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "langchain-anthropic is required for Anthropic provider. "
                "Install with: pip install langchain-anthropic"
            )
        return ChatAnthropic(
            model=model or os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"),
            api_key=self.api_key,
            temperature=0.2,
            max_tokens=4096,
        )

    @classmethod
    def from_env(cls) -> AnthropicProvider:
        return cls(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))
