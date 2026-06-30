"""
designlab_core.utilities.config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Reads config.yaml and exposes a typed settings object.

Usage:
    from designlab_core.utilities.config import get_config

    cfg = get_config()
    print(cfg.llm.default_model)
    print(cfg.api.prefix)


"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

# Set up logger for this module
_logger = logging.getLogger("designlab.config")


# ── Sub-models ────────────────────────────────────────────────────────────────

class LLMConfig(BaseModel):
    default_model: str = "claude-3-5-sonnet-20241022"
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_wait_seconds: int = 2
    max_tokens: int = 4096
    retry_max_multiplier: int = 8
    models: dict[str, str] = {}


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_path: str | None = "logs/designlab.txt"
    file_level: str = "INFO"
    file_max_bytes: int = 10485760
    file_backup_count: int = 5


class APIConfig(BaseModel):
    title: str = "DesignLab Core API"
    version: str = "0.1.0"
    prefix: str = "/api"
    min_feature_length: int = 10
    cors_origins: list[str] = []

class PromptsConfig(BaseModel):
    max_list_display: int = 10


class AppConfig(BaseModel):
    name: str = "designlab-core"
    version: str = "0.1.0"


class DesignLabConfig(BaseModel):
    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    logging: LoggingConfig = LoggingConfig()
    api: APIConfig = APIConfig()
    prompts: PromptsConfig = PromptsConfig()

    def resolve_model(self, alias: str) -> str:
        """
        Resolve a model alias to its full model ID.

        Looks up the alias in self.llm.models. If the alias is not found,
        falls back to self.llm.default_model and logs a warning.

        Args:
            alias: The friendly model alias (e.g., "claude-sonnet", "gpt-4o").

        Returns:
            The full model ID (e.g., "claude-3-5-sonnet-20241022").

        Example:
            cfg = get_config()
            model_id = cfg.resolve_model("claude-sonnet")
            # Returns: "claude-3-5-sonnet-20241022"
            
            model_id = cfg.resolve_model("unknown-alias")
            # Logs warning and returns default_model
        """
        # Check if alias exists in models dict
        if alias in self.llm.models:
            return self.llm.models[alias]
        
        # Alias not found - log warning and return default
        _logger.warning(
            f"Model alias '{alias}' not found in config. "
            f"Falling back to default model: {self.llm.default_model}"
        )
        return self.llm.default_model


# ── Loader ────────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


@lru_cache(maxsize=1)
def get_config(config_path: Path = _DEFAULT_CONFIG_PATH) -> DesignLabConfig:
    """
    Load and return the application configuration from config.yaml.

    Cached after first call — the same object is returned on all subsequent calls.

    Args:
        config_path: Path to config.yaml. Defaults to the repo root config.yaml.

    Returns:
        A validated DesignLabConfig instance.

    Raises:
        FileNotFoundError: If config.yaml does not exist at the given path.
        ValueError: If the YAML structure is invalid.

    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return DesignLabConfig(**raw)
