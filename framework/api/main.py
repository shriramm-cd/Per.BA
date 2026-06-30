"""
api/main.py
~~~~~~~~~~~
FastAPI application entry point for designlab-core Integration APIs.

Endpoints:
    POST /api/generate-story
    GET  /health

Run locally:
    uvicorn api.main:app --reload --port 8000


Status: COMPLETE — story router wired, lifespan context manager used.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from designlab_core.utilities.config import get_config
from designlab_core.utilities.logger import log_info

cfg = get_config()


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — runs startup and shutdown logic."""
    log_info("DesignLab Core API starting", env=cfg.app.name, version=cfg.app.version)
    yield
    log_info("DesignLab Core API shutting down")


# ── Application ───────────────────────────────────────────────────────────────


app = FastAPI(
    title=cfg.api.title,
    version=cfg.api.version,
    description="Core API for all DesignLab Accelerators.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────
# To add new accelerator routers, see docs/ADDING_NEW_ACCELERATORS.md

from api.routers.dynamic_router import create_generation_router
from designlab_core.schemas import (
    StoryOutput,
    ArchitectureOutput,
    UIOutput,
    BackendOutput,
    TestOutput,
)

app.include_router(
    create_generation_router(
        prompt_id="REQ-001-story-generation",
        response_schema=StoryOutput,
        tags=["Story Generation"],
    ),
    prefix="/api/generate-story",
)

app.include_router(
    create_generation_router(
        prompt_id="ARC-001-system-architecture",
        response_schema=ArchitectureOutput,
        tags=["Architecture Generation"],
    ),
    prefix="/api/generate-architecture",
)

app.include_router(
    create_generation_router(
        prompt_id="UI-001-react-page-generation",
        response_schema=UIOutput,
        tags=["UI Generation"],
    ),
    prefix="/api/generate-ui",
)

app.include_router(
    create_generation_router(
        prompt_id="BE-001-api-endpoint-generation",
        response_schema=BackendOutput,
        tags=["Backend Generation"],
    ),
    prefix="/api/generate-backend",
)

app.include_router(
    create_generation_router(
        prompt_id="TEST-001-unit-test-generation",
        response_schema=TestOutput,
        tags=["Testing Generation"],
    ),
    prefix="/api/generate-tests",
)


@app.get("/health")
async def health() -> dict:
    """Simple health check. Always returns 200 if the server is running."""
    return {"status": "ok", "version": cfg.app.version}
