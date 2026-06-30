# Core Architecture Guide

> `designlab-core` is not a standalone application; it is a generic LLM orchestration framework. It provides the base blueprints required to build deterministic AI microservices.

---

## The Core Philosophy: "The Pure Engine"

The engine contains **zero domain-specific business logic**. It does not know what a "User Story" or a "React Component" is. It provides a universal pipeline that downstream applications (*Accelerators*) configure and execute.

This means:
- **No hardcoded API endpoints** like `/api/generate-story` inside the core
- **No domain-specific Pydantic schemas** like `StoryOutput` in the public API surface
- **No domain-specific prompt templates** bundled as first-class citizens

Everything domain-specific lives in downstream accelerator applications that `pip install designlab-core` and compose their own pipelines.

---

## The Three Pillars of the Framework

### Pillar 1: The Blueprint Schema (`BaseAcceleratorOutput`)

**File:** [`designlab_core/schemas/base_schema.py`](../designlab_core/schemas/base_schema.py)

All outputs from the LLM must be strictly validated. Instead of hardcoding domain schemas, the core provides a base Pydantic v2 class: `BaseAcceleratorOutput`.

Downstream accelerators inherit from this blueprint to define their specific expected JSON structures, allowing the engine's validation layer (`validator.py`) to work dynamically with **any** schema shape.

```python
from designlab_core import BaseAcceleratorOutput
from pydantic import Field

class StoryOutput(BaseAcceleratorOutput):
    """Downstream accelerator defines its own fields."""
    title: str = Field(...)
    acceptance_criteria: list[str] = Field(default_factory=list)
```

**Base fields provided by the blueprint:**

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `datetime` | UTC timestamp of generation |
| `confidence_score` | `float (0.0–1.0)` | LLM self-evaluated confidence |
| `raw_context` | `str` | The raw input context that triggered the pipeline |

### Pillar 2: The Universal Orchestrator (`generate_from_pipeline`)

**File:** [`designlab_core/services/generation_pipeline.py`](../designlab_core/services/generation_pipeline.py)

This is the heart of the package. It executes a strictly typed, repeatable workflow:

```
┌─────────────────────────────────────────────────────────────────┐
│                    generate_from_pipeline()                      │
│                                                                  │
│  Step 1: load_prompt(template_id, variables)                    │
│     └─ Discovers .md template by ID, injects {{variables}}      │
│                        ↓                                         │
│  Step 2: generate_response(prompt, model_name, system_prompt)   │
│     └─ Routes to Anthropic/OpenAI, handles retry & timeout      │
│                        ↓                                         │
│  Step 3: _strip_markdown_fences(response.content)               │
│     └─ Cleans LLM output of ```json``` fences                  │
│                        ↓                                         │
│  Step 4: validate_output(raw_json, schema_class)                │
│     └─ Parses JSON, validates against Pydantic schema           │
│                        ↓                                         │
│  Return: Validated instance of schema_class                      │
└─────────────────────────────────────────────────────────────────┘
```

**Function signature:**

```python
async def generate_from_pipeline(
    template_id: str,           # Prompt template ID (e.g. "REQ-001-story-generation")
    schema_class: Type[T],      # Target Pydantic BaseModel subclass
    variables: dict[str, Any],  # Variables to inject into the template
    *,
    model_name: str = "claude-sonnet",      # Model alias from config.yaml
    system_prompt: str | None = None,       # Optional system prompt override
    max_tokens: int = 4096,                 # Max generation tokens
) -> T:
```

**Every parameter is overridable at call time** — no subclassing, no monkey-patching, no forking required.

### Pillar 3: The Router Factory (`create_generation_router`)

**File:** [`designlab_core/api/factory.py`](../designlab_core/api/factory.py)

To support Node.js wrappers and front-end dashboards, accelerators need REST endpoints. Instead of writing custom FastAPI routes for every domain, accelerators use the factory function to instantly generate fully functional POST endpoints bound to the `generate_from_pipeline` orchestrator.

The factory supports both standard single-stage generation and two-stage ("Checker Point") workflows:

#### 1. Single-Stage Mode (Default)
Exposes `POST /`. Takes a `GenerationRequest` and returns a validated `response_schema` instance.

#### 2. Two-Stage Mode (Checker Point)
Enabled when `draft_prompt_id` and `draft_schema` are passed to `create_generation_router()`. This exposes:
- `POST /draft`: Takes `GenerationRequest` and returns a validated `draft_schema` containing a high-level summary (e.g. user story descriptions) for review/approval.
- `POST /finalize`: Takes `FinalizeGenerationRequest` containing `approved_draft`, validates it against `draft_schema`, runs the final prompt utilizing the approved draft as context, and returns the detailed `response_schema` (e.g. full user stories with acceptance criteria).

```python
from designlab_core import create_generation_router

# Two-Stage Router example
router = create_generation_router(
    prompt_id="REQ-001-story-generation",
    response_schema=StoryOutput,
    draft_prompt_id="REQ-001-story-draft-generation",
    draft_schema=StoryDraftList,
    tags=["Story Generation"],
)

app.include_router(router, prefix="/api/generate-story")
```

**What the factory produces:**

| Aspect | Detail (Single-Stage) | Detail (Two-Stage) |
|--------|-----------------------|--------------------|
| **HTTP Method** | `POST` | `POST` |
| **Request Body** | `GenerationRequest` | `GenerationRequest` (for `/draft`) or `FinalizeGenerationRequest` (for `/finalize`) |
| **Response Body** | The `response_schema` model | `draft_schema` (for `/draft`) or `response_schema` (for `/finalize`) |
| **Error Handling** | `504` (timeout), `502` (provider), `422` (validation), `500` (unexpected) | Same mappings + `422` for invalid approved drafts |
| **OpenAPI Docs** | Auto-generated endpoint specs | Auto-generated specs for `/draft` and `/finalize` routes |

---

## Infrastructure Layer

### LLM Client (`llm/client.py`)

**File:** [`designlab_core/llm/client.py`](../designlab_core/llm/client.py)

Provider-agnostic abstraction. All accelerators call `generate_response()` — never a provider SDK directly. This keeps provider details (Anthropic, OpenAI, etc.) completely hidden.

```python
response = await generate_response(
    prompt="Generate a user story for login feature",
    model_name="claude-sonnet",   # Friendly alias from config.yaml
    system_prompt="You are a senior BA. Output valid JSON only.",
    max_tokens=4096,
)
```

**Provider routing:**
- Model ID starts with `claude` → Anthropic
- Model ID starts with `gpt-`, `o1`, `o3`, `o4` → OpenAI
- Extensible via `_detect_provider()` in `client.py`

**Resilience:**
- Exponential backoff retry (configurable via `LLM_MAX_RETRIES`, `retry_wait_seconds`)
- Timeout protection (configurable via `LLM_TIMEOUT_SECONDS`)
- Granular exception hierarchy: `LLMTimeoutError`, `LLMProviderError`, `LLMRetryExhausted`
- Retryable (429, 500+, connection errors) vs non-retryable (401, 400, 403, 404)

### Prompt Loader (`prompts/loader.py`)

**File:** [`designlab_core/prompts/loader.py`](../designlab_core/prompts/loader.py)

Discovers `.md` template files by ID and injects `{{variable}}` placeholders:

```python
prompt = load_prompt(
    "REQ-001-story-generation",
    variables={"feature_description": "Allow users to reset their password via email."},
)
```

**Template discovery:** Recursively scans all subdirectories under `prompts/` for `.md` files. Template ID = filename stem.

### Validation Engine (`evaluation/validator.py`)

**File:** [`designlab_core/evaluation/validator.py`](../designlab_core/evaluation/validator.py)

Validates raw JSON strings against any Pydantic schema class:

```python
result = validate_output(raw_json, StoryOutput)
if result.is_valid:
    story = result.parsed  # Validated StoryOutput instance
else:
    print(result.errors)   # List of validation error messages
```

**Validation steps:**
1. Parse JSON (catches `JSONDecodeError`)
2. Validate against Pydantic schema (catches `ValidationError`)
3. Check for empty fields (rejects empty strings, None, empty lists/dicts)

### Logging Engine (`utilities/logger.py`)

**File:** [`designlab_core/utilities/logger.py`](../designlab_core/utilities/logger.py)

Provides centralised structured logging for all accelerators.

**Level-Separated File Logging:**
To prevent standard logs from clogging critical error channels and taking up excessive server storage, the logging system automatically splits outputs:
- **Info/Warning Log (`logs/designlab_info.txt`)**: Contains all logs from `DEBUG` to `WARNING`.
- **Error Log (`logs/designlab_error.txt`)**: Contains strictly `ERROR` and `CRITICAL` logs.

Both file handlers use size-based `RotatingFileHandler` configured by the environment variables `LOG_FILE_MAX_BYTES` and `LOG_FILE_BACKUP_COUNT`.

### Configuration (`utilities/config.py` + `utilities/env.py`)

| Source | Purpose | Secret? |
|--------|---------|---------|
| `config.yaml` | Model aliases, retry settings, CORS origins, API metadata | No — version-controlled |
| `.env` | API keys, environment, timeouts, log level | Yes — never committed |

**Dynamic provider keys:** Set `{PROVIDER}_API_KEY` in `.env` and call `env.get_llm_key("provider")`. Works for ANY provider without code changes.

---

## Data Flow Diagram

```
Downstream Accelerator App
│
├─ Option A: Python Import
│   └─ from designlab_core import generate_from_pipeline
│       └─ generate_from_pipeline(template_id, schema_class, variables)
│
├─ Option B: REST API (via Router Factory)
│   └─ POST /api/generate-story  { "feature_description": "..." }
│       └─ create_generation_router() → generates endpoint → calls pipeline
│
└─ Option C: Low-Level Control
    └─ prompt = load_prompt("MY-TEMPLATE", variables={...})
        └─ response = await generate_response(prompt=prompt, model_name="gpt-4o")
            └─ result = validate_output(response.content, MySchema)
```

---

## What's Overridable

**Everything.** Every layer is designed so a downstream accelerator can override behaviour without forking or monkey-patching.

| What | How to Override | Where it's Set |
|------|----------------|----------------|
| **LLM model** | `model_name="gpt-4o"` | `config.yaml` → `llm.models` |
| **System prompt** | `system_prompt="..."` | Per-call parameter |
| **Prompt template** | `template_id="MY-001-custom"` | `.md` file in `prompts/` |
| **Max tokens** | `max_tokens=8192` | Per-call parameter |
| **Retry count** | `LLM_MAX_RETRIES=5` in `.env` | `env.py` |
| **Timeout** | `LLM_TIMEOUT_SECONDS=120` in `.env` | `env.py` |
| **Retry backoff** | `retry_wait_seconds: 4` in `config.yaml` | `config.py` |
| **API key** | `{PROVIDER}_API_KEY` in `.env` | `env.py` → `get_llm_key()` |
| **CORS origins** | `api.cors_origins` in `config.yaml` | `config.py` |
| **Log level** | `LOG_LEVEL=DEBUG` in `.env` | `env.py` |
