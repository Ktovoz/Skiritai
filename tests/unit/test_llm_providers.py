"""Unit tests for LLM provider abstraction — registry, providers, auto-detection."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# 1. Provider Registry Tests
# ============================================================

class TestProviderRegistry:
    """Test get_provider() resolution logic and register_provider()."""

    def test_get_provider_by_explicit_name(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            provider = get_provider(name="openai")
            assert provider.name == "openai"
            assert isinstance(provider.api_key, str)

    def test_get_provider_by_env_var(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider = get_provider()
            assert provider.name == "openai"

    def test_explicit_name_overrides_env_var(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-openai",
            "ANTHROPIC_API_KEY": "sk-ant",
        }, clear=True):
            provider = get_provider(name="anthropic")
            assert provider.name == "anthropic"

    def test_unknown_provider_raises(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                get_provider(name="nonexistent")

    def test_missing_api_key_raises(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="not configured"):
                get_provider(name="openai")

    def test_auto_detect_first_available(self):
        from skiritai.llm.registry import get_provider

        # Only OpenAI is configured
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider = get_provider()
            assert provider.name == "openai"

    def test_auto_detect_anthropic_when_openai_missing(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test",
        }, clear=True):
            provider = get_provider()
            assert provider.name == "anthropic"

    def test_auto_detect_prefers_openai_over_anthropic(self):
        from skiritai.llm.registry import get_provider

        # Both configured — OpenAI comes first in registry
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-oai",
            "ANTHROPIC_API_KEY": "sk-ant",
        }, clear=True):
            provider = get_provider()
            assert provider.name == "openai"

    def test_no_provider_available_raises(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No LLM provider available"):
                get_provider()

    def test_register_provider_adds_to_registry(self):
        from skiritai.llm.base import LLMProvider
        from skiritai.llm.registry import register_provider, get_provider

        class FakeProvider(LLMProvider):
            name = "fake"

            def build(self, model=None):
                return MagicMock()

            @classmethod
            def from_env(cls):
                return cls()

            @classmethod
            def is_available(cls):
                return True

        register_provider("fake", FakeProvider)
        try:
            with patch.dict(os.environ, {"LLM_PROVIDER": "fake"}, clear=True):
                provider = get_provider()
                assert provider.name == "fake"
        finally:
            # Cleanup: remove from registry
            import skiritai.llm.registry as reg
            reg._PROVIDERS.pop("fake", None)

    def test_register_provider_normalizes_name_to_lowercase(self):
        from skiritai.llm.base import LLMProvider
        from skiritai.llm.registry import register_provider

        class MixedCaseProvider(LLMProvider):
            name = "MixedCase"

            def build(self, model=None):
                return MagicMock()

            @classmethod
            def from_env(cls):
                return cls()

            @classmethod
            def is_available(cls):
                return True

        register_provider("MixedCASE", MixedCaseProvider)
        try:
            import skiritai.llm.registry as reg
            assert "mixedcase" in reg._PROVIDERS
        finally:
            import skiritai.llm.registry as reg
            reg._PROVIDERS.pop("mixedcase", None)

    def test_empty_string_provider_name_goes_to_auto_detect(self):
        from skiritai.llm.registry import get_provider

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "",
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider = get_provider()
            # Empty string is falsy, falls through to auto-detect
            assert provider.name == "openai"


# ============================================================
# 2. OpenAIProvider Tests
# ============================================================

class TestOpenAIProvider:
    """Test OpenAIProvider instantiation, env loading, and model building."""

    def test_from_env_reads_api_key(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-abc123"}, clear=True):
            provider = OpenAIProvider.from_env()
            assert provider.api_key == "sk-abc123"

    def test_from_env_reads_base_url(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://custom.api.com/v1",
        }, clear=True):
            provider = OpenAIProvider.from_env()
            assert provider.base_url == "https://custom.api.com/v1"

    def test_from_env_base_url_none_when_not_set(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            provider = OpenAIProvider.from_env()
            assert provider.base_url is None

    def test_is_available_true_with_key(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            assert OpenAIProvider.is_available() is True

    def test_is_available_false_without_key(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {}, clear=True):
            assert OpenAIProvider.is_available() is False

    def test_build_uses_default_model(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {}, clear=True):
            provider = OpenAIProvider(api_key="sk-test")
            with patch("skiritai.llm.openai_provider.ChatOpenAI") as mock_chat:
                provider.build()
                call_kwargs = mock_chat.call_args.kwargs
                assert call_kwargs["api_key"] == "sk-test"
                assert call_kwargs["model"] == "gpt-4o"
                assert call_kwargs["temperature"] == 0.2

    def test_build_uses_custom_model(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-test")
        with patch("skiritai.llm.openai_provider.ChatOpenAI") as mock_chat:
            provider.build(model="gpt-4o-mini")
            assert mock_chat.call_args.kwargs["model"] == "gpt-4o-mini"

    def test_build_uses_env_model(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {"LLM_MODEL": "gpt-4-turbo"}, clear=True):
            provider = OpenAIProvider(api_key="sk-test")
            with patch("skiritai.llm.openai_provider.ChatOpenAI") as mock_chat:
                provider.build()
                assert mock_chat.call_args.kwargs["model"] == "gpt-4-turbo"

    def test_build_explicit_model_overrides_env(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        with patch.dict(os.environ, {"LLM_MODEL": "gpt-4-turbo"}, clear=True):
            provider = OpenAIProvider(api_key="sk-test")
            with patch("skiritai.llm.openai_provider.ChatOpenAI") as mock_chat:
                provider.build(model="custom-model")
                assert mock_chat.call_args.kwargs["model"] == "custom-model"

    def test_name_is_openai(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        assert OpenAIProvider.name == "openai"


# ============================================================
# 3. AnthropicProvider Tests
# ============================================================

class TestAnthropicProvider:
    """Test AnthropicProvider instantiation, env loading, and model building."""

    def test_from_env_reads_api_key(self):
        from skiritai.llm.anthropic_provider import AnthropicProvider

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-abc"}, clear=True):
            provider = AnthropicProvider.from_env()
            assert provider.api_key == "sk-ant-abc"

    def test_is_available_true_with_key(self):
        from skiritai.llm.anthropic_provider import AnthropicProvider

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
            assert AnthropicProvider.is_available() is True

    def test_is_available_false_without_key(self):
        from skiritai.llm.anthropic_provider import AnthropicProvider

        with patch.dict(os.environ, {}, clear=True):
            assert AnthropicProvider.is_available() is False

    def test_build_uses_default_model(self):
        from skiritai.llm import anthropic_provider as mod

        with patch.dict(os.environ, {}, clear=True):
            mock_chat = MagicMock()
            # mock langchain_anthropic module since it may not be installed
            with patch.dict(sys.modules, {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat)}):
                provider = mod.AnthropicProvider(api_key="sk-ant-test")
                provider.build()
                call_kwargs = mock_chat.call_args.kwargs
                assert call_kwargs["api_key"] == "sk-ant-test"
                assert call_kwargs["temperature"] == 0.2
                assert call_kwargs["max_tokens"] == 4096

    def test_build_uses_custom_model(self):
        from skiritai.llm import anthropic_provider as mod

        mock_chat = MagicMock()
        with patch.dict(sys.modules, {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat)}):
            provider = mod.AnthropicProvider(api_key="sk-ant-test")
            provider.build(model="claude-opus-4-6")
            assert mock_chat.call_args.kwargs["model"] == "claude-opus-4-6"

    def test_build_with_missing_dependency_raises(self):
        from skiritai.llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(api_key="sk-ant-test")
        # langchain-anthropic is not installed, import fails naturally
        with pytest.raises(ImportError, match="langchain-anthropic"):
            provider.build()

    def test_name_is_anthropic(self):
        from skiritai.llm.anthropic_provider import AnthropicProvider

        assert AnthropicProvider.name == "anthropic"


# ============================================================
# 4. Integration: Full Provider Resolution Flow
# ============================================================

class TestProviderIntegration:
    """Test end-to-end provider resolution with real env conditions."""

    def test_openai_provider_roundtrip(self):
        from skiritai.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-xyz", base_url="https://api.x.com")
        assert provider.api_key == "sk-xyz"
        assert provider.base_url == "https://api.x.com"
        assert provider.name == "openai"

        # build() returns a ChatOpenAI instance (mocked)
        with patch("skiritai.llm.openai_provider.ChatOpenAI") as mock:
            provider.build(model="test-model")
            mock.assert_called_once()

    def test_registry_includes_both_providers(self):
        import skiritai.llm.registry as reg

        provider_names = list(reg._PROVIDERS.keys())
        assert "openai" in provider_names
        assert "anthropic" in provider_names


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
