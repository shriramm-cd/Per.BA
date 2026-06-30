"""
designlab_core.utilities.env
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Loads environment variables from .env and exposes a typed settings object.

Usage:
    from designlab_core.utilities.env import get_env

    env = get_env()
    
    # Get any provider's API key dynamically
    anthropic_key = env.get_llm_key("anthropic")
    openai_key = env.get_llm_key("openai")
    huggingface_key = env.get_llm_key("huggingface")  # Works for ANY provider!
    
    # Access other settings
    print(env.api_base_url)
    print(env.log_level)

The system accepts ANY provider key via {provider}_api_key convention.
Simply add PROVIDER_API_KEY=xxx to your .env file and call get_llm_key("provider").

Accelerators can override specific keys by setting them in their own environment
before importing. Standard os.environ precedence applies — existing env vars
are NOT overwritten by .env.


Status: Fully dynamic - supports any LLM provider without code changes.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DesignLabEnv(BaseSettings):
    """
    Typed environment settings for designlab-core.

    Reads from .env at the repo root. All fields can be overridden by
    setting the corresponding environment variable before process start.
    
    Dynamically accepts ANY LLM provider key via {provider}_api_key pattern.
    Use get_llm_key(provider) to retrieve keys at runtime.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",            # Allow any additional fields from .env
        case_sensitive=False,
    )

    # ── Runtime ───────────────────────────────────────────
    app_env: str = Field(default="local", description="local | dev | staging | production")

    # ── Base Domain URLs ──────────────────────────────────
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the designlab-core API server.",
    )
    ba_accelerator_url: str = Field(
        default="http://localhost:8001",
        description="Base URL of the BA Accelerator service.",
    )
    scrum_accelerator_url: str = Field(
        default="http://localhost:8002",
        description="Base URL of the Scrum Master Accelerator service.",
    )

    # ── LLM Overrides ─────────────────────────────────────
    default_llm_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default LLM model ID. Overrides config.yaml value.",
    )
    llm_timeout_seconds: int = Field(default=60)
    llm_max_retries: int = Field(default=3)
    llm_max_tokens: int = Field(default=4096)
    llm_retry_max_multiplier: int = Field(default=8)
    
    # ── API & Prompts Overrides ───────────────────────────
    api_min_feature_length: int = Field(default=10)
    prompts_max_list_display: int = Field(default=10)

    # ── Logging ───────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_file_path: str | None = Field(
        default="logs/designlab.txt",
        description="Path to the log file. Set to empty string or null to disable file logging.",
    )
    log_file_level: str = Field(
        default="INFO",
        description="Log level specifically for the file handler.",
    )
    log_file_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum size of the log file in bytes before rotation.",
    )
    log_file_backup_count: int = Field(
        default=5,
        description="Number of backup log files to retain.",
    )

    def model_post_init(self, __context) -> None:
        """
        Load all *_API_KEY environment variables dynamically.
        
        This allows any provider key to be loaded from the environment
        without pre-defining fields in the class.
        """
        # Load all environment variables ending with _API_KEY
        for key, value in os.environ.items():
            if key.endswith("_API_KEY"):
                # Convert to lowercase attribute name (case_sensitive=False)
                attr_name = key.lower()
                # Set as attribute (os.environ takes precedence over .env)
                setattr(self, attr_name, value)

    def get_llm_key(self, provider: str) -> str:
        """
        Return the API key for the specified LLM provider.

        Dynamically retrieves API keys based on provider name by looking for
        a field named "{provider}_api_key" in the environment settings.
        
        Supports ANY provider - simply set {PROVIDER}_API_KEY in your .env file.

        Args:
            provider: The provider name (e.g., "anthropic", "openai", "cohere", "huggingface").

        Returns:
            The API key as a plain string.

        Raises:
            ValueError: If the provider field does not exist or the key is empty.

        Example:
            # In .env: ANTHROPIC_API_KEY=sk-ant-123
            key = env.get_llm_key("anthropic")  # Returns: "sk-ant-123"
            
            # In .env: HUGGINGFACE_API_KEY=hf_abc
            key = env.get_llm_key("huggingface")  # Returns: "hf_abc"
        """
        field_name = f"{provider}_api_key"
        
        # Check if the field exists
        if not hasattr(self, field_name):
            raise ValueError(f"Provider '{provider}' is not configured. Set {field_name.upper()} in your .env file.")
        
        # Get the field value
        field_value = getattr(self, field_name)
        
        # Handle different types: SecretStr, str, or other
        if isinstance(field_value, SecretStr):  # type: ignore
            key = field_value.get_secret_value()
        elif isinstance(field_value, str):
            key = field_value
        else:
            key = str(field_value)
        
        # Validate the key is not empty
        if not key:
            raise ValueError(f"API key for provider '{provider}' is empty. Set {field_name.upper()} in your .env file.")
        
        return key


@lru_cache(maxsize=1)
def get_env() -> DesignLabEnv:
    """
    Load and return the environment settings.

    Cached after first call. In tests, call get_env.cache_clear() before
    re-instantiating with different env values.

    Returns:
        A validated DesignLabEnv instance.
    """
    return DesignLabEnv()
