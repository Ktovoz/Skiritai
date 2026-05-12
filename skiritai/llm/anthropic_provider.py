"""Anthropic Claude LLM provider (optional dependency)."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .base import LLMProvider

if TYPE_CHECKING:
    from ._config import LLMConfig


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def build(self, model: str | None = None):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "langchain-anthropic is required for Anthropic provider. "
                "Install with: pip install skiritai[anthropic]"
            )
        kwargs: dict = {
            "model": model or self._model or os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"),
            "api_key": self.api_key,
            "temperature": self._temperature if self._temperature is not None else 0.2,
            "max_tokens": self._max_tokens if self._max_tokens is not None else 4096,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return ChatAnthropic(**kwargs)

    @classmethod
    def from_env(cls) -> AnthropicProvider:
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        )

    @classmethod
    def from_config(cls, config: LLMConfig) -> AnthropicProvider:
        """Create from internal LLMConfig. Used by create_llm()."""
        return cls(
            api_key=config.api_key or "",
            base_url=config.base_url,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))
