# API Reference

Complete reference for all public symbols exported by `designlab-core`.

```python
import designlab_core
print(designlab_core.__version__)  # "0.1.0"
print(len(designlab_core.__all__))  # 19 symbols
```

---

## Core Blueprints

### `BaseAcceleratorOutput`

**Module:** `designlab_core.schemas.base_schema`  
**Type:** Pydantic `BaseModel` subclass

Generic base schema blueprint that all downstream accelerator outputs inherit from. Contains universal metadata fields common across all domain generations.

```python
from designlab_core import BaseAcceleratorOutput
from pydantic import Field

class MyOutput(BaseAcceleratorOutput):
    title: str = Field(...)
    items: list[str] = Field(default_factory=list)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `generated_at` | `datetime` | `datetime.now(UTC)` | UTC timestamp of generation |
| `confidence_score` | `float` | Required (`0.0–1.0`) | LLM self-evaluated confidence |
| `raw_context` | `str` | Required | Raw input context that triggered the pipeline |

---

### `generate_from_pipeline()`

**Module:** `designlab_core.services.generation_pipeline`  
**Type:** `async` function

Universal orchestrator. Executes the full pipeline: load prompt → call LLM → strip fences → validate schema.

```python
result = await generate_from_pipeline(
    template_id="REQ-001-story-generation",
    schema_class=StoryOutput,
    variables={"feature_description": "Allow users to reset their password."},
    model_name="claude-sonnet",
    system_prompt="You are a senior BA. Output valid JSON only.",
    max_tokens=4096,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `template_id` | `str` | Required | Prompt template ID (filename stem) |
| `schema_class` | `Type[BaseModel]` | Required | Pydantic model for validation |
| `variables` | `dict[str, Any]` | Required | Variables to inject into template |
| `model_name` | `str` | `"claude-sonnet"` | Model alias from `config.yaml` |
| `system_prompt` | `str \| None` | `None` | Optional system prompt override |
| `max_tokens` | `int` | `4096` | Maximum tokens to generate |

**Returns:** Validated instance of `schema_class`.

**Raises:**
- `FileNotFoundError` — Template not found
- `ValueError` — Template has unreplaced placeholders, or LLM output fails schema validation
- `LLMTimeoutError` — Request exceeded timeout
- `LLMProviderError` — Non-retryable provider error
- `LLMRetryExhausted` — All retry attempts exhausted

---

### `create_generation_router()`

**Module:** `designlab_core.api.factory`  
**Type:** Function → returns `FastAPI.APIRouter`

Factory function that returns a ready-to-mount FastAPI router. Supports both standard single-stage and two-stage ("Checker Point") generation workflows.

#### A. Single-Stage Generation (Default)
Exposes a single `POST /` endpoint. The endpoint accepts a `GenerationRequest`, pipes it through `generate_from_pipeline()`, and returns validated JSON matching the `response_schema`.

```python
from designlab_core import create_generation_router

router = create_generation_router(
    prompt_id="ARC-001-system-architecture",
    response_schema=ArchitectureOutput,
    tags=["Architecture Generation"],
)
```

#### B. Two-Stage Generation (Checker Point Enabled)
Activated when `draft_prompt_id` and `draft_schema` are provided. Exposes two endpoints:
- `POST /draft`: Accepts a standard `GenerationRequest`, generates the initial outline, and returns a validated JSON matching `draft_schema`.
- `POST /finalize`: Accepts a `FinalizeGenerationRequest` (containing `feature_description` and `approved_draft`), validates the draft against `draft_schema` for integrity, and runs the final generation to return the detailed `response_schema`.

```python
from designlab_core import create_generation_router

router = create_generation_router(
    prompt_id="REQ-001-story-generation",
    response_schema=StoryOutput,
    draft_prompt_id="REQ-001-story-draft-generation",
    draft_schema=StoryDraftList,
    tags=["Story Generation"],
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt_id` | `str` | Required | Default prompt template ID for final stage |
| `response_schema` | `Type[BaseModel]` | Required | Target Pydantic model for final stage |
| `tags` | `list[str] \| None` | Auto-generated | FastAPI doc grouping tags |
| `summary` | `str \| None` | Auto-generated | Route summary for OpenAPI |
| `response_description` | `str \| None` | Auto-generated | Response body description |
| `draft_prompt_id` | `str \| None` | `None` | Default prompt template ID for draft stage |
| `draft_schema` | `Type[BaseModel] \| None` | `None` | Target Pydantic model for draft stage |

**Returns:** `FastAPI.APIRouter`

**HTTP Error Mapping:**

| Exception | Status Code |
|-----------|-------------|
| `LLMTimeoutError` | `504 Gateway Timeout` |
| `LLMRetryExhausted` | `502 Bad Gateway` |
| `LLMProviderError` | `502 Bad Gateway` |
| `LLMError` | `502 Bad Gateway` |
| `ValueError` | `422 Unprocessable Entity` |
| `Exception` | `500 Internal Server Error` |

---

### `GenerationRequest`

**Module:** `designlab_core.api.factory`  
**Type:** Pydantic `BaseModel` subclass

Request payload accepted by endpoints produced by `create_generation_router()`.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `feature_description` | `str` | ✅ (min 10 chars) | Feature description to generate artifacts for |
| `model_name` | `str \| None` | Optional | Model alias override |
| `system_prompt` | `str \| None` | Optional | System prompt override |
| `template_id` | `str \| None` | Optional | Template ID override |
| `max_tokens` | `int \| None` | Optional | Max tokens override |

---

### `FinalizeGenerationRequest`

**Module:** `designlab_core.api.factory`  
**Type:** Pydantic `BaseModel` subclass

Request payload accepted by the `/finalize` endpoint in two-stage generation.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `feature_description` | `str` | ✅ (min 10 chars) | Feature description to generate artifacts for |
| `approved_draft` | `Any` | ✅ | The user-approved/modified draft object or list |
| `model_name` | `str \| None` | Optional | Model alias override |
| `system_prompt` | `str \| None` | Optional | System prompt override |
| `template_id` | `str \| None` | Optional | Template ID override |
| `max_tokens` | `int \| None` | Optional | Max tokens override |

---

## LLM Layer

### `generate_response()`

**Module:** `designlab_core.llm.client`  
**Type:** `async` function

Low-level LLM call. Send a prompt to an LLM and return a standardised response. This is the only function accelerators should call for direct LLM interaction.

```python
response = await generate_response(
    prompt="Generate a user story for login feature",
    model_name="claude-sonnet",
    system_prompt="You are a senior BA. Output valid JSON only.",
    max_tokens=4096,
)
print(response.content)      # The LLM's text response
print(response.model_used)   # "claude-3-5-sonnet-20241022"
print(response.tokens_used)  # 412
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | `str` | Required | User prompt to send |
| `model_name` | `str` | `"claude-sonnet"` | Model alias from `config.yaml` |
| `system_prompt` | `str \| None` | `None` | System-level instruction |
| `max_tokens` | `int` | `4096` | Maximum generation tokens |

**Returns:** `LLMResponse`

**Raises:** `LLMTimeoutError`, `LLMProviderError`, `LLMRetryExhausted`

---

### `LLMResponse`

**Module:** `designlab_core.llm.client`  
**Type:** `dataclass`

Standardised response from `generate_response()`.

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Text content returned by the LLM |
| `model_used` | `str` | Actual model ID that handled the request |
| `tokens_used` | `int` | Total tokens consumed (default `0`) |
| `metadata` | `dict` | Provider-specific data (stop_reason, etc.) |

---

### Exception Hierarchy

```
LLMError (base)
├── LLMTimeoutError       # Request exceeded configured timeout
├── LLMProviderError      # Non-retryable error (401, 400, 403, 404)
└── LLMRetryExhausted     # All retry attempts exhausted (429, 500+)
```

All exceptions live in `designlab_core.llm.exceptions`.

| Exception | When Raised | HTTP Mapping |
|-----------|-------------|--------------|
| `LLMTimeoutError` | Request exceeds `LLM_TIMEOUT_SECONDS` | `504` |
| `LLMProviderError` | Auth failure, bad request, permission denied, not found | `502` |
| `LLMRetryExhausted` | Rate limits or server errors exhaust all retries | `502` |

**Extra attributes on each exception:**

- `LLMTimeoutError`: `.timeout`, `.provider`, `.model_name`
- `LLMProviderError`: `.status_code`, `.provider`, `.model_name`
- `LLMRetryExhausted`: `.max_retries`, `.provider`, `.model_name`

---

## Prompts

### `load_prompt()`

**Module:** `designlab_core.prompts.loader`  
**Type:** Function

Load a prompt template by ID and inject variables into `{{placeholder}}` patterns.

```python
prompt = load_prompt(
    "REQ-001-story-generation",
    variables={"feature_description": "Allow users to reset their password via email."},
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `template_id` | `str` | Required | Template ID (filename without `.md`) |
| `variables` | `dict[str, str] \| None` | `None` | Placeholder values to inject |

**Returns:** `str` — the fully assembled prompt.

**Raises:**
- `FileNotFoundError` — Template not found
- `ValueError` — Unreplaced placeholders remain

---

### `list_templates()`

**Module:** `designlab_core.prompts.loader`  
**Type:** Function

Return a sorted list of all available template IDs.

```python
templates = list_templates()
# ["ARC-001-system-architecture", "BE-001-api-endpoint-generation", ...]
```

**Returns:** `list[str]`

---

## Validation

### `validate_output()`

**Module:** `designlab_core.evaluation.validator`  
**Type:** Function

Validate raw JSON against any Pydantic schema class.

```python
result = validate_output('{"title": "US-001", ...}', StoryOutput)
if result.is_valid:
    story = result.parsed
else:
    print(result.errors)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `raw_json` | `str` | Raw JSON string to validate |
| `schema_class` | `type` | Pydantic BaseModel subclass |

**Returns:** `ValidationResult`

---

### `ValidationResult`

**Module:** `designlab_core.evaluation.validator`  
**Type:** `dataclass`

| Field | Type | Description |
|-------|------|-------------|
| `is_valid` | `bool` | Whether validation passed |
| `parsed` | `Any \| None` | Validated model instance (or `None` on failure) |
| `errors` | `list[str]` | List of error messages |
| `schema_name` | `str` | Name of the schema class used |

---

## Utilities

### `log_info()`, `log_warning()`, `log_error()`

**Module:** `designlab_core.utilities.logger`

Structured logging functions. Support both dict-style and keyword-style context:

```python
log_info("Story generated", model="claude-sonnet", tokens=412)
log_info("Story generated", context={"model": "claude-sonnet", "tokens": 412})
log_error("Generation failed", exc=some_exception, model="gpt-4o")
```

#### Level-Separated File Logging
When `env.log_file_path` is set (defaults to `logs/designlab.txt`), the logger automatically instantiates separate file outputs:
- **`logs/designlab_info.txt`**: Captures logs ranging from `DEBUG` to `WARNING`.
- **`logs/designlab_error.txt`**: Captures logs of level `ERROR` and `CRITICAL`.

Both files are managed using size-based `RotatingFileHandler` configured via environment variables:
- `LOG_FILE_MAX_BYTES` (default `10MB`) sets the size limit before a log rotates.
- `LOG_FILE_BACKUP_COUNT` (default `5`) sets the maximum backup logs kept per file.

---

### `get_config()`

**Module:** `designlab_core.utilities.config`  
**Returns:** `DesignLabConfig`

Load and return the application configuration from `config.yaml`. Cached after first call.

```python
cfg = get_config()
print(cfg.llm.default_model)       # "claude-3-5-sonnet-20241022"
print(cfg.llm.models)              # {"claude-sonnet": "claude-3-5-sonnet-20241022", ...}
print(cfg.api.cors_origins)        # ["http://localhost:3000", ...]
model_id = cfg.resolve_model("claude-sonnet")  # "claude-3-5-sonnet-20241022"
```

### `get_env()`

**Module:** `designlab_core.utilities.env`  
**Returns:** `DesignLabEnv`

Load and return environment settings from `.env`. Cached after first call.

```python
env = get_env()
key = env.get_llm_key("anthropic")  # Reads ANTHROPIC_API_KEY from .env
print(env.llm_timeout_seconds)      # 60
print(env.llm_max_retries)          # 3
print(env.log_level)                # "INFO"
```

**Dynamic provider keys:** Set `{PROVIDER}_API_KEY=xxx` in `.env` and call `env.get_llm_key("provider")`. Works for **any** provider without code changes.
