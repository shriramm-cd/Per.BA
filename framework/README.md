# designlab-core

> **A generic LLM orchestration framework for building AI Accelerators.**

`designlab-core` is a pure engine — it contains **zero domain-specific business logic**. It does not know what a "User Story" or a "React Component" is. It provides a universal pipeline that downstream applications (called *Accelerators*) configure and execute.

---

## The Three Pillars

| Pillar | What it Does | Entry Point |
|--------|-------------|-------------|
| **Blueprint Schema** | Base Pydantic v2 class — downstream accelerators inherit to define their expected JSON structures | `BaseAcceleratorOutput` |
| **Universal Orchestrator** | Loads prompt → injects variables → routes to LLM → validates JSON against schema | `generate_from_pipeline()` |
| **Router Factory** | Instantly generates fully functional FastAPI POST endpoints bound to the orchestrator | `create_generation_router()` |

## Quick Start

```bash
# Clone & setup
git clone https://github.com/cloud-directions/designlab-core.git
cd designlab-core

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy environment template and fill in your API keys
cp .env.example .env
```

## Usage (Downstream Accelerator)

```python
from fastapi import FastAPI
from designlab_core import (
    BaseAcceleratorOutput,
    create_generation_router,
    generate_from_pipeline,
)
from pydantic import Field

# 1. Define your domain schema
class StoryOutput(BaseAcceleratorOutput):
    title: str = Field(..., description="Story title")
    acceptance_criteria: list[str] = Field(default_factory=list)

# 2. Wire a REST endpoint in one line
app = FastAPI()
app.include_router(
    create_generation_router(
        prompt_id="REQ-001-story-generation",
        response_schema=StoryOutput,
    ),
    prefix="/api/generate-story",
)

# 3. Or call the pipeline directly from Python
result = await generate_from_pipeline(
    template_id="REQ-001-story-generation",
    schema_class=StoryOutput,
    variables={"feature_description": "Allow users to reset their password via email."},
)
```

---

## Package Exports

After `pip install designlab-core`, everything you need is available from the root:

```python
from designlab_core import (
    # Core Blueprints
    BaseAcceleratorOutput,        # Schema base class
    generate_from_pipeline,       # Orchestrator
    create_generation_router,     # API Router Factory
    GenerationRequest,            # Default request model for the factory

    # LLM Layer
    generate_response,            # Low-level LLM call
    LLMResponse,                  # Standardised response dataclass
    LLMError,                     # Base exception
    LLMProviderError,             # Non-retryable provider errors
    LLMRetryExhausted,            # All retries exhausted
    LLMTimeoutError,              # Request timeout

    # Prompts
    load_prompt,                  # Load & inject variables into templates
    list_templates,               # Enumerate available template IDs

    # Validation
    validate_output,              # Validate raw JSON against any schema
    ValidationResult,             # Result dataclass

    # Utilities
    log_info, log_warning, log_error,
    get_config, get_env,
)
```

---

## Project Structure

```
designlab-core/
├── designlab_core/              # Main importable package
│   ├── api/                     # Router Factory (create_generation_router)
│   │   └── factory.py           # ← The API template downstream apps import
│   ├── evaluation/              # Output quality validation
│   │   └── validator.py         # JSON → Pydantic schema validation
│   ├── llm/                     # LLM abstraction layer
│   │   ├── client.py            # Provider-agnostic generate_response()
│   │   └── exceptions.py        # LLMError hierarchy
│   ├── prompts/                 # Prompt template engine
│   │   ├── base_template.md     # Generic template skeleton
│   │   └── loader.py            # Template discovery & variable injection
│   ├── schemas/                 # Schema blueprints
│   │   └── base_schema.py       # BaseAcceleratorOutput base class
│   ├── services/                # Orchestration layer
│   │   └── generation_pipeline.py  # generate_from_pipeline()
│   └── utilities/               # Shared infrastructure
│       ├── config.py            # config.yaml reader
│       ├── env.py               # .env loader (dynamic provider keys)
│       └── logger.py            # Structured logging
├── api/                         # Reference FastAPI application (example wiring)
├── docs/                        # Documentation
├── .env.example                 # Environment variable template
├── config.yaml                  # Application configuration
└── pyproject.toml               # Package definition
```

---

## Configuration

### `config.yaml` (version-controlled, non-secret)

| Section | Key | Purpose |
|---------|-----|---------|
| `llm.default_model` | `claude-3-5-sonnet-20241022` | Default model when no alias matches |
| `llm.models` | `{alias: model_id}` | Friendly name → full model ID mapping |
| `llm.retry_wait_seconds` | `2` | Exponential backoff base |
| `api.cors_origins` | `[...]` | Allowed CORS origins |

### `.env` (secret, never committed)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `{PROVIDER}_API_KEY` | Any provider — dynamically discovered |
| `LLM_TIMEOUT_SECONDS` | Request timeout (default: 60) |
| `LLM_MAX_RETRIES` | Retry count (default: 3) |
| `LOG_LEVEL` | `DEBUG \| INFO \| WARNING \| ERROR` |

---

## Documentation

| Document | Description |
|----------|-------------|
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Core architecture guide — the three pillars in depth |
| [`ADDING_NEW_ACCELERATORS.md`](docs/ADDING_NEW_ACCELERATORS.md) | Step-by-step guide to building downstream accelerators |
| [`API_REFERENCE.md`](docs/API_REFERENCE.md) | Complete API reference for all exported symbols |
| [`contributing.md`](docs/contributing.md) | Branch strategy and PR workflow |

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Protected. Only merge via approved PR. |
| `develop` | Integration branch. All feature branches merge here first. |
| `feature/*` | Feature work — push freely, then open PR → `develop` |

## Versioning

Package version follows [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH` — e.g., `0.1.0`
- Update in `pyproject.toml` before each release tag.
