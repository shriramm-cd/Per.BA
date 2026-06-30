"""
designlab_core.schemas.base_schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generic base Pydantic schema blueprint for all Accelerator outputs.


Status: FINALISED
"""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class BaseAcceleratorOutput(BaseModel):  # type: ignore
    """
    Base generic schema blueprint that all downstream accelerator outputs inherit from.

    Contains universal metadata fields common across all domain generations.
    """
    model_config = ConfigDict(
        populate_by_name=True,
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp indicating when the output was generated."
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Self-evaluated LLM confidence score between 0.0 and 1.0."
    )
    raw_context: str = Field(
        ...,
        description="The raw input context/feature description used to trigger the pipeline."
    )
