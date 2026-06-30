"""
api/routers/dynamic_router.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Proxy router for dynamic code/spec generation endpoints delegating to designlab_core.
"""

from designlab_core.api.factory import create_generation_router, GenerationRequest, FinalizeGenerationRequest

__all__ = ["create_generation_router", "GenerationRequest", "FinalizeGenerationRequest"]
