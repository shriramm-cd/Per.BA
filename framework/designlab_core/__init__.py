"""
designlab-core
~~~~~~~~~~~~~~
Core engine/framework for all DesignLab Accelerators.

This package is a pure engine — it contains NO domain-specific schemas,
prompts, or hardcoded API routes. Downstream accelerator apps compose
their own pipelines by importing these building blocks:

    from designlab_core import (
        GenerationPipeline,           # Orchestrator Blueprint
        BaseAcceleratorOutput,        # Schema Blueprint
        create_generation_router,     # API Router Factory
        generate_response,            # Low-level LLM client
        load_prompt,                  # Prompt template loader
    )

See docs/ADDING_NEW_ACCELERATORS.md for full integration guide.
"""

# ── Schema Blueprint ──────────────────────────────────────────────────────────
from designlab_core.schemas.base_schema import BaseAcceleratorOutput

# ── Orchestrator Blueprint ────────────────────────────────────────────────────
from designlab_core.services.generation_pipeline import generate_from_pipeline

# ── API Router Factory ────────────────────────────────────────────────────────
from designlab_core.api.factory import create_generation_router, GenerationRequest, FinalizeGenerationRequest

# ── LLM Infrastructure ───────────────────────────────────────────────────────
from designlab_core.llm.client import generate_response, LLMResponse
from designlab_core.llm.exceptions import (
    LLMError,
    LLMProviderError,
    LLMRetryExhausted,
    LLMTimeoutError,
)

# ── Prompt Infrastructure ────────────────────────────────────────────────────
from designlab_core.prompts.loader import load_prompt, list_templates

# ── Validation Infrastructure ────────────────────────────────────────────────
from designlab_core.evaluation.validator import validate_output, ValidationResult

# ── Logging ───────────────────────────────────────────────────────────────────
from designlab_core.utilities.logger import (
    log_info,
    log_warning,
    log_error,
)

# ── Configuration ─────────────────────────────────────────────────────────────
from designlab_core.utilities.config import get_config
from designlab_core.utilities.env import get_env


__version__ = "0.1.0"

__all__ = [
    # ── Core Blueprints (what downstream apps need most) ──────────────────
    "BaseAcceleratorOutput",       # Schema base class — inherit to define your domain output
    "generate_from_pipeline",      # Orchestrator — template → LLM → validate → schema
    "create_generation_router",    # API factory — builds a FastAPI router for any schema
    "GenerationRequest",           # Default request model used by the router factory
    "FinalizeGenerationRequest",   # Request model for the finalize stage of two-stage generation

    # ── LLM Layer ─────────────────────────────────────────────────────────
    "generate_response",           # Low-level LLM call (use for full control)
    "LLMResponse",                 # Standardised response dataclass
    "LLMError",                    # Base exception for all LLM errors
    "LLMProviderError",            # Non-retryable provider error (401, 400, etc.)
    "LLMRetryExhausted",           # All retry attempts exhausted
    "LLMTimeoutError",             # Request exceeded configured timeout
    # ── Prompts ───────────────────────────────────────────────────────────
    "load_prompt",                 # Load & inject variables into a template by ID
    "list_templates",              # Enumerate all available template IDs
    # ── Validation ────────────────────────────────────────────────────────
    "validate_output",             # Validate raw JSON against a Pydantic schema
    "ValidationResult",            # Result dataclass from validate_output()
    # ── Utilities ─────────────────────────────────────────────────────────
    "log_info",
    "log_warning",
    "log_error",
    "get_config",
    "get_env",
]