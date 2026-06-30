"""
designlab_core.services.generation_pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Universal generation pipeline for all accelerators.


Status: COMPLETE
"""

from __future__ import annotations

from typing import Any, Type, TypeVar
from pydantic import BaseModel

from designlab_core.evaluation.validator import validate_output
from designlab_core.llm.client import LLMResponse, generate_response
from designlab_core.prompts.loader import load_prompt
from designlab_core.utilities.logger import get_logger

_logger = get_logger("services.pipeline")

T = TypeVar("T", bound=BaseModel)  # type: ignore


async def generate_from_pipeline(
    template_id: str,
    schema_class: Type[T],
    variables: dict[str, Any],
    *,
    model_name: str = "claude-sonnet",
    system_prompt: str | None = None,
    max_tokens: int | None = None,
) -> T:
    """
    Orchestrate the core LLM-to-schema pipeline.

    Steps:
        1. Load prompt template by ID and inject variables.
        2. Call LLM using dynamic routing/retry logic.
        3. Clean up markdown fences from LLM output.
        4. Validate against the target Pydantic schema class.

    Args:
        template_id:   The prompt template ID (e.g. 'REQ-001-story-generation').
        schema_class:  The Pydantic BaseModel subclass for parsing/validation.
        variables:     Variables to inject into the template placeholders.
        model_name:    Model alias (default: 'claude-sonnet').
        system_prompt: Optional override for the LLM system prompt.
        max_tokens:    Maximum generation tokens.

    Returns:
        An instance of schema_class populated with validated data.
    """
    _logger.info(
        f"Pipeline start: template={template_id}, "
        f"schema={schema_class.__name__}, variables={list(variables.keys())}"
    )

    # Step 1: Load and assemble the prompt
    prompt = load_prompt(template_id, variables=variables)

    # If no system prompt is provided, default to a persona matching the schema
    if not system_prompt:
        system_prompt = (
            f"You are an expert AI assistant. You produce valid JSON only — "
            f"no markdown fences, no commentary, no text outside the JSON object. "
            f"Your output must exactly match the {schema_class.__name__} Pydantic schema."
        )

    # Step 2: Call the LLM
    response: LLMResponse = await generate_response(
        prompt=prompt,
        model_name=model_name,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )

    # Step 3: Strip markdown fences if present
    raw_json = _strip_markdown_fences(response.content)

    # Step 4: Validate against the Pydantic schema class
    result = validate_output(raw_json, schema_class)

    if not result.is_valid:
        error_summary = "; ".join(result.errors)
        _logger.error(
            f"Schema validation failed for {schema_class.__name__}: {error_summary}"
        )
        raise ValueError(
            f"LLM response failed {schema_class.__name__} validation: {error_summary}. "
            f"Model: {response.model_used}."
        )

    _logger.info(f"Pipeline complete: schema={schema_class.__name__} validated successfully.")
    if result.parsed is None:
        raise ValueError(f"Orchestration pipeline returned None for schema {schema_class.__name__}")
    return result.parsed


def _strip_markdown_fences(text: str) -> str:
    """
    Strip markdown code fences from LLM output if present.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()
    return stripped
