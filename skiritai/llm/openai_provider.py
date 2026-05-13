"""OpenAI-compatible LLM provider."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from langchain_openai import ChatOpenAI

from .base import LLMProvider

if TYPE_CHECKING:
    from ._config import LLMConfig


class OpenAIProvider(LLMProvider):
    name = "openai"

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

    def build(self, model: str | None = None) -> ChatOpenAI:
        kwargs: dict = {
            "model": model or self._model or os.getenv("LLM_MODEL", "gpt-4o"),
            "api_key": self.api_key,
            "temperature": self._temperature if self._temperature is not None else 0.2,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        if self._max_tokens is not None:
            kwargs["max_tokens"] = self._max_tokens
        return ChatOpenAI(**kwargs)

    @classmethod
    def from_env(cls) -> OpenAIProvider:
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=os.getenv("LLM_MODEL"),
        )

    @classmethod
    def from_config(cls, config: LLMConfig) -> OpenAIProvider:
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
        return bool(os.getenv("OPENAI_API_KEY"))
