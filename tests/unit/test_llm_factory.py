"""Unit tests for LLM factory: create_llm(), load_env(), config file parsing, from_config()."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# 1. LLMConfig Tests
# ============================================================

class TestLLMConfig:
    """Test the internal LLMConfig data structure."""

    def test_default_values(self):
        from skiritai.llm._config import LLMConfig

        cfg = LLMConfig()
        assert cfg.provider is None
        assert cfg.api_key is None
        assert cfg.base_url is None
        assert cfg.model is None
        assert cfg.temperature is None
        assert cfg.max_tokens is None

    def test_custom_values(self):
        from skiritai.llm._config import LLMConfig

        cfg = LLMConfig(
            provider="openai",
            api_key="sk-test",
            base_url="https://api.test.com/v1",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2048,
        )
        assert cfg.provider == "openai"
        assert cfg.api_key == "sk-test"
        assert cfg.base_url == "https://api.test.com/v1"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 2048


# ============================================================
# 2. create_llm() Tests
# ============================================================

class TestCreateLLM:
    """Test the create_llm() factory function."""

    def test_create_from_env_openai(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "LLM_PROVIDER": "openai",
        }, clear=True):
            provider = create_llm()
            assert provider.name == "openai"
            assert provider.api_key == "sk-test"

    def test_create_from_env_anthropic(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "LLM_PROVIDER": "anthropic",
        }, clear=True):
            with patch("skiritai.llm._factory._auto_load_env"):
                provider = create_llm()
            assert provider.name == "anthropic"
            assert provider.api_key == "sk-ant-test"

    def test_create_with_explicit_provider(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider = create_llm(provider="openai", api_key="sk-explicit")
            assert provider.name == "openai"
            assert provider.api_key == "sk-explicit"

    def test_create_with_explicit_model(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider = create_llm(model="gpt-4o-mini")
            assert provider._model == "gpt-4o-mini"

    def test_create_with_base_url(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider = create_llm(base_url="https://custom.api.com/v1")
            assert provider.base_url == "https://custom.api.com/v1"

    def test_create_no_api_key_raises(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {}, clear=True):
            with patch("skiritai.llm._factory._auto_load_env"):
                with pytest.raises(ValueError, match="API key not found"):
                    create_llm()

    def test_create_unknown_provider_raises(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                create_llm(provider="nonexistent", api_key="sk-test")

    def test_create_no_provider_available_raises(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {}, clear=True):
            with patch("skiritai.llm._factory._auto_load_env"):
                with pytest.raises(ValueError, match="No LLM provider available"):
                    create_llm(api_key="sk-test")

    def test_create_explicit_args_override_env(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-env",
            "LLM_MODEL": "gpt-3.5",
        }, clear=True):
            provider = create_llm(api_key="sk-explicit", model="gpt-4o")
            assert provider.api_key == "sk-explicit"
            assert provider._model == "gpt-4o"

    def test_create_auto_detects_provider(self):
        from skiritai.llm._factory import create_llm

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider = create_llm()
            assert provider.name == "openai"

    def test_create_with_temperature_and_max_tokens(self):
        from skiritai.llm._factory import create_llm
        from skiritai.llm._config import LLMConfig

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            # Temperature and max_tokens are set via config file, not direct args
            # So we test from_config on the provider directly
            from skiritai.llm.openai_provider import OpenAIProvider
            cfg = LLMConfig(
                api_key="sk-test",
                temperature=0.7,
                max_tokens=2048,
            )
            provider = OpenAIProvider.from_config(cfg)
            assert provider._temperature == 0.7
            assert provider._max_tokens == 2048


# ============================================================
# 3. Config File Parsing Tests
# ============================================================

class TestConfigFileParsing:
    """Test TOML and YAML config file parsing."""

    def test_parse_toml_config(self):
        from skiritai.llm._factory import _parse_config_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[llm]\nprovider = "openai"\napi_key = "sk-toml"\nmodel = "gpt-4o"\ntemperature = 0.3\n')
            f.flush()
            cfg = _parse_config_file(Path(f.name))

        assert cfg.provider == "openai"
        assert cfg.api_key == "sk-toml"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.3
        os.unlink(f.name)

    def test_parse_yaml_config(self):
        from skiritai.llm._factory import _parse_config_file

        pytest.importorskip("yaml")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("llm:\n  provider: anthropic\n  api_key: sk-yaml\n  model: claude-opus\n")
            f.flush()
            cfg = _parse_config_file(Path(f.name))

        assert cfg.provider == "anthropic"
        assert cfg.api_key == "sk-yaml"
        assert cfg.model == "claude-opus"
        os.unlink(f.name)

    def test_parse_toml_with_env_var_expansion(self):
        from skiritai.llm._factory import _parse_config_file

        with patch.dict(os.environ, {"MY_API_KEY": "sk-from-env"}, clear=True):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
                f.write('[llm]\napi_key = "${MY_API_KEY}"\n')
                f.flush()
                cfg = _parse_config_file(Path(f.name))

        assert cfg.api_key == "sk-from-env"
        os.unlink(f.name)

    def test_parse_unsupported_format_raises(self):
        from skiritai.llm._factory import _parse_config_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            f.flush()
            with pytest.raises(ValueError, match="Unsupported config file format"):
                _parse_config_file(Path(f.name))
        os.unlink(f.name)

    def test_parse_missing_file_raises(self):
        from skiritai.llm._factory import _load_config_file

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            _load_config_file("/nonexistent/skiritai.toml")

    def test_config_file_overrides_env(self):
        from skiritai.llm._factory import create_llm

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[llm]\nprovider = "openai"\napi_key = "sk-from-file"\nmodel = "gpt-from-file"\n')
            f.flush()

            with patch.dict(os.environ, {
                "OPENAI_API_KEY": "sk-from-env",
                "LLM_MODEL": "gpt-from-env",
            }, clear=True):
                provider = create_llm(from_file=f.name)
                assert provider.api_key == "sk-from-file"
                assert provider._model == "gpt-from-file"

        os.unlink(f.name)


# ============================================================
# 4. from_config() Tests
# ============================================================

class TestFromConfig:
    """Test from_config() on provider classes."""

    def test_openai_from_config(self):
        from skiritai.llm._config import LLMConfig
        from skiritai.llm.openai_provider import OpenAIProvider

        cfg = LLMConfig(
            api_key="sk-cfg",
            base_url="https://custom.api.com/v1",
            model="gpt-5",
            temperature=0.5,
            max_tokens=2048,
        )
        provider = OpenAIProvider.from_config(cfg)
        assert provider.api_key == "sk-cfg"
        assert provider.base_url == "https://custom.api.com/v1"
        assert provider._model == "gpt-5"
        assert provider._temperature == 0.5
        assert provider._max_tokens == 2048

    def test_anthropic_from_config(self):
        from skiritai.llm._config import LLMConfig
        from skiritai.llm.anthropic_provider import AnthropicProvider

        cfg = LLMConfig(
            api_key="sk-ant-cfg",
            base_url="https://custom.anthropic.com",
            model="claude-opus",
            temperature=0.7,
            max_tokens=8192,
        )
        provider = AnthropicProvider.from_config(cfg)
        assert provider.api_key == "sk-ant-cfg"
        assert provider.base_url == "https://custom.anthropic.com"
        assert provider._model == "claude-opus"
        assert provider._temperature == 0.7
        assert provider._max_tokens == 8192

    def test_openai_from_config_minimal(self):
        from skiritai.llm._config import LLMConfig
        from skiritai.llm.openai_provider import OpenAIProvider

        cfg = LLMConfig(api_key="sk-min")
        provider = OpenAIProvider.from_config(cfg)
        assert provider.api_key == "sk-min"
        assert provider.base_url is None
        assert provider._model is None

    def test_openai_build_with_config_params(self):
        from skiritai.llm._config import LLMConfig
        from skiritai.llm.openai_provider import OpenAIProvider

        cfg = LLMConfig(api_key="sk-test", model="gpt-5", temperature=0.7, max_tokens=2048)
        provider = OpenAIProvider.from_config(cfg)
        with patch("skiritai.llm.openai_provider.ChatOpenAI") as mock:
            provider.build()
            kwargs = mock.call_args.kwargs
            assert kwargs["model"] == "gpt-5"
            assert kwargs["temperature"] == 0.7
            assert kwargs["max_tokens"] == 2048


# ============================================================
# 5. load_env() Tests
# ============================================================

class TestLoadEnv:
    """Test load_env() function."""

    def test_load_env_specific_file(self):
        from skiritai.llm._factory import load_env

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_LOAD_ENV_VAR=hello_from_file\n")
            f.flush()

            with patch.dict(os.environ, {}, clear=True):
                load_env(f.name)
                assert os.getenv("TEST_LOAD_ENV_VAR") == "hello_from_file"

        os.unlink(f.name)

    def test_load_env_does_not_override_existing(self):
        from skiritai.llm._factory import load_env

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("EXISTING_VAR=from_file\n")
            f.flush()

            with patch.dict(os.environ, {"EXISTING_VAR": "original"}, clear=True):
                load_env(f.name)
                assert os.getenv("EXISTING_VAR") == "original"

        os.unlink(f.name)


# ============================================================
# 6. Env Var Expansion Tests
# ============================================================

class TestEnvVarExpansion:
    """Test ${VAR} expansion in config values."""

    def test_expand_simple(self):
        from skiritai.llm._factory import _expand_env_vars

        with patch.dict(os.environ, {"MY_KEY": "value123"}, clear=True):
            assert _expand_env_vars("${MY_KEY}") == "value123"

    def test_expand_missing_returns_empty(self):
        from skiritai.llm._factory import _expand_env_vars

        with patch.dict(os.environ, {}, clear=True):
            assert _expand_env_vars("${MISSING_VAR}") == ""

    def test_expand_in_string(self):
        from skiritai.llm._factory import _expand_env_vars

        with patch.dict(os.environ, {"HOST": "api.example.com"}, clear=True):
            assert _expand_env_vars("https://${HOST}/v1") == "https://api.example.com/v1"

    def test_no_expansion_in_plain_string(self):
        from skiritai.llm._factory import _expand_env_vars

        assert _expand_env_vars("just-a-string") == "just-a-string"


# ============================================================
# 7. Public API Export Tests
# ============================================================

class TestPublicAPI:
    """Test that create_llm and load_env are accessible from expected locations."""

    def test_import_from_llm_module(self):
        from skiritai.llm import create_llm, load_env

        assert callable(create_llm)
        assert callable(load_env)

    def test_import_from_top_level(self):
        from skiritai import create_llm, load_env

        assert callable(create_llm)
        assert callable(load_env)

    def test_openai_provider_importable(self):
        from skiritai.llm import OpenAIProvider

        assert OpenAIProvider.name == "openai"


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    result = pytest.main([__file__, "-v", "--tb=short", "--no-header"])
    sys.exit(result.returncode if hasattr(result, "returncode") else 0)
