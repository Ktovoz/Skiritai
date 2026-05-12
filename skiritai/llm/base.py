"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._config import LLMConfig


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Each provider must implement build() to return a LangChain-compatible
    chat model instance (anything with .invoke() / .ainvoke() / .bind_tools()).
    """

    name: str  # Provider identifier, e.g. "openai", "anthropic"

    @abstractmethod
    def build(self, model: str | None = None) -> Any:
        """Build and return a LangChain chat model instance.

        Args:
            model: Model name override. If None, provider uses its default.

        Returns:
            A LangChain BaseChatModel instance.
        """
        ...

    @classmethod
    @abstractmethod
    def from_env(cls) -> LLMProvider:
        """Create a provider instance from environment variables."""
        ...

    @classmethod
    def from_config(cls, config: LLMConfig) -> LLMProvider:
        """Create from internal LLMConfig. Used by create_llm().

        Default implementation delegates to from_env().
        Subclasses should override for full config support.
        """
        return cls.from_env()

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this provider can be created from current env vars."""
        ...
