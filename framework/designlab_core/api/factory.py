"""
designlab_core.api.factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generic FastAPI Router Factory for the DesignLab generation engine.

This module is the ONLY API surface that designlab-core exposes.
It does NOT define endpoints for specific domains (stories, architecture, etc.).
Instead, downstream accelerator apps import this factory and wire their own
routes with their own schemas, prompt templates, and prefixes.

Usage (in a downstream accelerator app):
    from fastapi import FastAPI
    from designlab_core import create_generation_router
    from my_accelerator.schemas import StoryOutput

    app = FastAPI()

    app.include_router(
        create_generation_router(
            prompt_id="REQ-001-story-generation",
            response_schema=StoryOutput,
            tags=["Story Generation"],
        ),
        prefix="/api/generate-story",
    )

Status: FINALISED
"""

from __future__ import annotations

import json
from typing import Type, TypeVar, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from designlab_core.llm.exceptions import (
    LLMError,
    LLMProviderError,
    LLMRetryExhausted,
    LLMTimeoutError,
)
from designlab_core.services.generation_pipeline import generate_from_pipeline
from designlab_core.utilities.logger import log_error, log_info
from designlab_core.utilities.env import get_env

T = TypeVar("T", bound=BaseModel)  # type: ignore


# ── Request Schemas ───────────────────────────────────────────────────────────


class GenerationRequest(BaseModel):  # type: ignore
    """
    Generic request payload accepted by all generation endpoints.

    Downstream accelerators can subclass this to add domain-specific fields,
    but the factory works with this base shape out of the box.
    """

    feature_description: str = Field(
        ...,
        min_length=get_env().api_min_feature_length,
        description=(
            "Plain-English description of the feature to generate artifacts for. "
            "Should describe the feature's purpose, key user interactions, "
            "business rules, and any constraints. Minimum 10 characters."
        ),
    )
    model_name: str | None = Field(
        default=None,
        description="Model alias from config.yaml. If omitted, uses the active default model.",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Optional override for the system prompt sent to the LLM.",
    )
    template_id: str | None = Field(
        default=None,
        description=(
            "Optional override for the prompt template ID. "
            "If omitted, the router's default prompt_id is used."
        ),
    )
    max_tokens: int | None = Field(
        default=None,
        description="Optional override for maximum tokens generated in the response.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Minimal request",
                    "value": {
                        "feature_description": (
                            "Allow registered users to reset their forgotten password "
                            "via a time-limited email link."
                        ),
                    },
                }
            ]
        }
    )


class FinalizeGenerationRequest(BaseModel):  # type: ignore
    """
    Request payload accepted by the finalize generation endpoint.
    """

    feature_description: str = Field(
        ...,
        min_length=get_env().api_min_feature_length,
        description="Plain-English description of the feature to generate artifacts for.",
    )
    approved_draft: Any = Field(
        ...,
        description="The user-approved/modified draft object or list from the first stage.",
    )
    model_name: str | None = Field(
        default=None,
        description="Model alias from config.yaml. If omitted, uses the active default model.",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Optional override for the system prompt sent to the LLM.",
    )
    template_id: str | None = Field(
        default=None,
        description="Optional override for the prompt template ID.",
    )
    max_tokens: int | None = Field(
        default=None,
        description="Optional override for maximum tokens generated in the response.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Finalize request",
                    "value": {
                        "feature_description": "Allow registered users to reset password.",
                        "approved_draft": {
                            "stories": [
                                {
                                    "id": "US-001",
                                    "title": "Reset password request",
                                    "description": "As a user..."
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )


# ── Router Factory ────────────────────────────────────────────────────────────


def create_generation_router(
    prompt_id: str,
    response_schema: Type[T],
    *,
    tags: list[str] | None = None,
    summary: str | None = None,
    response_description: str | None = None,
    draft_prompt_id: str | None = None,
    draft_schema: Type[BaseModel] | None = None,
) -> APIRouter:
    """
    Factory function that returns a ready-to-mount FastAPI APIRouter.

    If draft_prompt_id and draft_schema are provided, it exposes:
        - POST /draft -> returns a validated draft_schema
        - POST /finalize -> accepts FinalizeGenerationRequest and returns response_schema

    Otherwise, it exposes:
        - POST / -> returns a validated response_schema (backward compatible)
    """
    router = APIRouter(tags=tags or [f"{response_schema.__name__} Generation"])

    # Helper function to orchestrate the generation and handle error mapping
    async def run_pipeline(
        template_id: str,
        schema: Type[BaseModel],
        feature_description: str,
        additional_vars: dict[str, Any] | None = None,
        model_name: str | None = None,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        try:
            log_info(
                f"Generation requested: schema={schema.__name__}",
                desc_len=len(feature_description),
                model=model_name,
            )

            # Build variables
            variables = {"feature_description": feature_description}
            if additional_vars:
                variables.update(additional_vars)

            # Build optional kwargs for the pipeline
            kwargs: dict = {}
            if model_name is not None:
                kwargs["model_name"] = model_name
            if system_prompt is not None:
                kwargs["system_prompt"] = system_prompt
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            # Orchestrate via the universal generation pipeline
            result = await generate_from_pipeline(
                template_id=template_id,
                schema_class=schema,
                variables=variables,
                **kwargs,
            )

            log_info(
                f"Generation complete: schema={schema.__name__}",
                model=model_name,
            )
            return result

        except LLMTimeoutError as exc:
            log_error("Generation timed out", exc=exc)
            raise HTTPException(status_code=504, detail=str(exc))

        except LLMRetryExhausted as exc:
            log_error("Generation retries exhausted", exc=exc)
            raise HTTPException(status_code=502, detail=str(exc))

        except LLMProviderError as exc:
            log_error("LLM provider error", exc=exc)
            raise HTTPException(status_code=502, detail=str(exc))

        except LLMError as exc:
            log_error("LLM error", exc=exc)
            raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

        except ValueError as exc:
            log_error("Schema validation failed", exc=exc)
            raise HTTPException(
                status_code=422,
                detail=f"Schema validation failed: {exc}",
            )

        except Exception as exc:
            log_error("Unexpected error in generation endpoint", exc=exc)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {type(exc).__name__}",
            )

    if draft_prompt_id is not None and draft_schema is not None:
        # Two-stage Generation (with Checker Point)
        @router.post(
            "/draft",
            response_model=draft_schema,
            summary=f"Generate draft for {response_schema.__name__}",
            response_description=f"A validated draft {draft_schema.__name__} instance.",
        )
        async def generate_draft_endpoint(request: GenerationRequest) -> Any:
            active_template_id = request.template_id or draft_prompt_id
            return await run_pipeline(
                template_id=active_template_id,
                schema=draft_schema,
                feature_description=request.feature_description,
                model_name=request.model_name,
                system_prompt=request.system_prompt,
                max_tokens=request.max_tokens,
            )

        @router.post(
            "/finalize",
            response_model=response_schema,
            summary=summary or f"Finalize {response_schema.__name__} from draft",
            response_description=response_description or f"A validated {response_schema.__name__} instance.",
        )
        async def finalize_endpoint(request: FinalizeGenerationRequest) -> Any:
            # Validate approved_draft against draft_schema to ensure checker point integrity
            try:
                draft_schema.model_validate(request.approved_draft)
            except Exception as exc:
                log_error("Approved draft failed validation against draft schema", exc=exc)
                raise HTTPException(
                    status_code=422,
                    detail=f"Approved draft failed validation: {exc}",
                )

            # Serialize approved draft to be passed to final generation prompt template
            approved_draft_str = json.dumps(request.approved_draft)
            active_template_id = request.template_id or prompt_id

            return await run_pipeline(
                template_id=active_template_id,
                schema=response_schema,
                feature_description=request.feature_description,
                additional_vars={"approved_draft": approved_draft_str},
                model_name=request.model_name,
                system_prompt=request.system_prompt,
                max_tokens=request.max_tokens,
            )

    else:
        # Standard Single-stage Generation
        route_summary = summary or f"Generate {response_schema.__name__}"
        route_response_desc = (
            response_description or f"A validated {response_schema.__name__} instance."
        )

        @router.post(
            "",
            response_model=response_schema,
            summary=route_summary,
            response_description=route_response_desc,
        )
        async def generate_endpoint(request: GenerationRequest) -> T:
            active_template_id = request.template_id or prompt_id
            return await run_pipeline(
                template_id=active_template_id,
                schema=response_schema,
                feature_description=request.feature_description,
                model_name=request.model_name,
                system_prompt=request.system_prompt,
                max_tokens=request.max_tokens,
            )
    return router
