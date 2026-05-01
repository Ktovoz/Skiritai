"""OpenAI-compatible LLM provider."""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    def build(self, model: str | None = None) -> ChatOpenAI:
        return ChatOpenAI(
            model=model or os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.2,
        )

    @classmethod
    def from_env(cls) -> OpenAIProvider:
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))
