"""LLM factory — create_llm(), load_env(), and config file parsing."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from skiritai.logger import logger

from ._config import LLMConfig

if TYPE_CHECKING:
    from .base import LLMProvider


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

def load_env(env_file: str | Path | None = None, *, search: bool = True) -> None:
    """Load .env with smart search: CWD -> parent dirs -> ~/.skiritai/.env."""
    from dotenv import load_dotenv

    if env_file is not None:
        load_dotenv(Path(env_file), override=False)
        return

    if search:
        _search_and_load_dotenv()
    else:
        load_dotenv(override=False)


def _search_and_load_dotenv() -> None:
    """Search for .env in CWD -> parent dirs (max 10) -> ~/.skiritai/.env."""
    from dotenv import load_dotenv

    # 1. CWD and parent dirs (limit depth)
    cwd = Path.cwd()
    for i, parent in enumerate([cwd] + list(cwd.parents)):
        if i > 10:
            break
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return

    # 2. ~/.skiritai/.env
    home_env = Path.home() / ".skiritai" / ".env"
    if home_env.is_file():
        load_dotenv(home_env, override=False)


def _auto_load_env() -> None:
    """Safe auto-load called by create_llm(). Idempotent, never overwrites."""
    from dotenv import load_dotenv

    load_dotenv(override=False)


# ---------------------------------------------------------------------------
# Config file parsing
# ---------------------------------------------------------------------------

def _expand_env_vars(value: str) -> str:
    """Expand ${VAR} references in config values."""
    def _replace(m: re.Match) -> str:
        var_name = m.group(1)
        val = os.getenv(var_name)
        if val is None:
            logger.warning(
                f"[Config] Environment variable '${{{var_name}}}' referenced in "
                f"config but not set — substituting empty string."
            )
            return ""
        return val
    return re.sub(r'\$\{(\w+)\}', _replace, value)


def _load_toml(path: Path) -> dict:
    """Load a TOML config file."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            raise ImportError(
                "TOML support requires Python 3.11+ or 'tomli' package. "
                "Install with: pip install tomli"
            )

    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data


def _load_yaml(path: Path) -> dict:
    """Load a YAML config file."""
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "YAML support requires 'pyyaml' package. "
            "Install with: pip install pyyaml"
        )

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _parse_config_file(path: Path) -> LLMConfig:
    """Parse a config file (TOML or YAML) into an LLMConfig."""
    suffix = path.suffix.lower()
    if suffix == ".toml":
        data = _load_toml(path)
    elif suffix in (".yaml", ".yml"):
        data = _load_yaml(path)
    else:
        raise ValueError(f"Unsupported config file format: {suffix}. Use .toml or .yaml")

    llm_section = data.get("llm", {})
    if not isinstance(llm_section, dict):
        raise ValueError("'llm' section must be a mapping")

    cfg = LLMConfig()
    for field in ("provider", "api_key", "base_url", "model"):
        val = llm_section.get(field)
        if val is not None:
            if isinstance(val, str):
                val = _expand_env_vars(val)
            setattr(cfg, field, val)

    for field in ("temperature", "max_tokens"):
        val = llm_section.get(field)
        if val is not None:
            setattr(cfg, field, val)

    return cfg


def _discover_config_file() -> Path | None:
    """Auto-discover config file: CWD upward (max 10 levels), then $SKIRITAI_CONFIG, then home."""
    # 1. CWD upward search (limit depth to avoid scanning entire filesystem)
    cwd = Path.cwd()
    for i, parent in enumerate([cwd] + list(cwd.parents)):
        if i > 10:
            break
        for name in ("skiritai.toml", "skiritai.yaml", "skiritai.yml"):
            candidate = parent / name
            if candidate.is_file():
                return candidate

    # 2. $SKIRITAI_CONFIG env var
    env_config = os.getenv("SKIRITAI_CONFIG")
    if env_config:
        p = Path(env_config)
        if p.is_file():
            return p

    # 3. ~/.skiritai/config.toml
    home_config = Path.home() / ".skiritai" / "config.toml"
    if home_config.is_file():
        return home_config

    return None


def _load_config_file(from_file: str | Path | None) -> LLMConfig | None:
    """Load config from file, auto-discovering if needed."""
    if from_file is not None:
        path = Path(from_file)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")
        return _parse_config_file(path)

    # Auto-discover
    discovered = _discover_config_file()
    if discovered is not None:
        logger.info(f"[LLM] Using config file: {discovered}")
        return _parse_config_file(discovered)

    return None


def _resolve_config(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    *,
    from_file: str | Path | None = None,
) -> tuple[LLMConfig, Path | None]:
    """Resolve and merge all config sources into a single LLMConfig.

    Returns:
        (merged_config, config_file_path_or_None)
    """
    # 1. Build base from env vars (lowest priority)
    cfg = LLMConfig()
    cfg.provider = os.getenv("LLM_PROVIDER")
    cfg.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    cfg.base_url = os.getenv("OPENAI_BASE_URL")
    cfg.model = os.getenv("LLM_MODEL")

    # 2. Load config file (overrides env)
    config_file = None
    if from_file is not None:
        config_file = Path(from_file)
    else:
        config_file = _discover_config_file()

    file_cfg = _load_config_file(config_file) if config_file else None
    if file_cfg is not None:
        logger.info(f"[LLM] Using config file: {config_file}")
        for field in ("provider", "api_key", "base_url", "model", "temperature", "max_tokens"):
            val = getattr(file_cfg, field)
            if val is not None:
                setattr(cfg, field, val)

    # 3. Explicit args override everything (highest)
    if provider:
        cfg.provider = provider
    if api_key:
        cfg.api_key = api_key
    if base_url:
        cfg.base_url = base_url
    if model:
        cfg.model = model

    return cfg, config_file


# ---------------------------------------------------------------------------
# create_llm() — public factory function
# ---------------------------------------------------------------------------

def create_llm(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    *,
    from_file: str | Path | None = None,
) -> LLMProvider:
    """Create an LLM provider with automatic configuration.

    Resolution priority: explicit args > config file > env vars > defaults.

    Args:
        provider: Provider name ("openai" or "anthropic").
        api_key: API key for the provider.
        base_url: Custom API base URL.
        model: Model name.
        from_file: Path to a TOML or YAML config file.

    Returns:
        An LLMProvider instance ready to use.

    Raises:
        ValueError: If no valid configuration is found.
    """
    # Import here to avoid circular imports
    from .registry import _PROVIDERS

    # 0. Auto-load .env (safe: override=False)
    _auto_load_env()

    # 1-3. Resolve merged config from all sources
    cfg, _ = _resolve_config(
        provider=provider, api_key=api_key,
        base_url=base_url, model=model, from_file=from_file,
    )

    # 4. Validate
    if not cfg.api_key:
        raise ValueError(
            "LLM API key not found. Set OPENAI_API_KEY / ANTHROPIC_API_KEY "
            "or pass api_key= to create_llm()."
        )

    # 5. Resolve provider class
    if cfg.provider:
        pcls = _PROVIDERS.get(cfg.provider.lower())
        if not pcls:
            raise ValueError(
                f"Unknown LLM provider: {cfg.provider}. "
                f"Available: {list(_PROVIDERS.keys())}"
            )
    else:
        # Auto-detect from available keys
        pcls = None
        for _pname, cls in _PROVIDERS.items():
            if cls.is_available():
                pcls = cls
                break
        if pcls is None:
            raise ValueError("No LLM provider available.")

    logger.info(f"[LLM] Using provider: {pcls.name}")
    return pcls.from_config(cfg)
