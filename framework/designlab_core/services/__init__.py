"""
designlab_core.services
~~~~~~~~~~~~~~~~~~~~~~~~
Orchestration layer — connects prompt templates → LLM client → schema validation.

Provides the universal generate_from_pipeline orchestrator function that downstream
accelerators use to execute dynamic generation workflows.
"""

from designlab_core.services.generation_pipeline import generate_from_pipeline

__all__ = [
    "generate_from_pipeline",
]
