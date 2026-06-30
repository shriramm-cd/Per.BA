# Adding New Accelerator Services

This guide explains how to build a new downstream accelerator that consumes `designlab-core`. Accelerators are domain-specific applications that leverage the core engine's universal pipeline.

---

## Architecture Overview

Every accelerator follows the same composition pattern — inherit the blueprint, provide a prompt template, and wire the factory:

```
┌──────────────────────────────────────────────────────────────────┐
│  Your Accelerator App (e.g. ba-accelerator, qa-accelerator)      │
│                                                                   │
│  1. Define Schema   → class StoryOutput(BaseAcceleratorOutput)   │
│  2. Write Template  → prompts/REQ-001-story-generation.md        │
│  3. Wire Endpoint   → create_generation_router(prompt_id, schema)│
│                                                                   │
│  That's it. The engine handles everything else.                   │
├──────────────────────────────────────────────────────────────────┤
│  designlab-core (the engine — installed via pip)                  │
│  ┌────────────────────────────────────────────────┐              │
│  │  Router Factory  → create_generation_router()  │              │
│  │  Orchestrator    → generate_from_pipeline()    │              │
│  │  LLM Client      → generate_response()         │              │
│  │  Prompt Loader   → load_prompt()               │              │
│  │  Validator        → validate_output()           │              │
│  └────────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

---

## What's Overridable

**Everything.** Every layer is designed so a downstream accelerator can override behaviour without forking or monkey-patching.

| What | How to Override | Where it's Set |
|------|----------------|----------------|
| **LLM model** | Pass `model_name="gpt-4o"` to any function | `config.yaml` → `llm.models` for aliases |
| **System prompt** | Pass `system_prompt="..."` to any function | Per-call parameter |
| **Prompt template** | Pass `template_id="MY-001-custom"` | `.md` file in your `prompts/` directory |
| **Max tokens** | Pass `max_tokens=8192` | Per-call parameter |
| **Retry count** | Set `LLM_MAX_RETRIES=5` in `.env` | `env.py` → `llm_max_retries` |
| **Timeout** | Set `LLM_TIMEOUT_SECONDS=120` in `.env` | `env.py` → `llm_timeout_seconds` |
| **Retry backoff** | Set `retry_wait_seconds: 4` in `config.yaml` | `config.py` → `llm.retry_wait_seconds` |
| **API key** | Set `{PROVIDER}_API_KEY` in `.env` | `env.py` → `get_llm_key()` |
| **CORS origins** | Add URLs to `api.cors_origins` in `config.yaml` | `config.py` → `api.cors_origins` |
| **Log level** | Set `LOG_LEVEL=DEBUG` in `.env` | `env.py` → `log_level` |
| **Validation** | Call `validate_output()` with any Pydantic schema class | `evaluation/validator.py` |

---

## Step-by-Step: Building a New Accelerator

### Step 1: Define Your Output Schema

Create a Pydantic v2 model that inherits from `BaseAcceleratorOutput`. This defines the exact JSON structure your LLM must produce.

```python
# my_accelerator/schemas/story.py

from pydantic import BaseModel, ConfigDict, Field
from designlab_core import BaseAcceleratorOutput


class AcceptanceCriterion(BaseModel):  # type: ignore
    """A single Given/When/Then acceptance criterion."""

    model_config = ConfigDict(populate_by_name=True)

    given: str = Field(..., description="The precondition")
    when: str = Field(..., description="The action taken")
    then: str = Field(..., description="The expected outcome")


class StoryOutput(BaseAcceleratorOutput):  # type: ignore
    """Root output model for the BA Story Accelerator."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "title": "US-001: Password Reset via Email",
                "user_story": "As a registered user, I want to...",
                "acceptance_criteria": [
                    {"given": "...", "when": "...", "then": "..."}
                ],
                "confidence_score": 0.92,
                "raw_context": "Allow users to reset their password...",
            }
        },
    )

    title: str = Field(..., description="Story title in US-NNN format")
    user_story: str = Field(..., description="As a <role>, I want <goal>, so that <reason>")
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
```

> **Rules:**
> - Always inherit from `BaseAcceleratorOutput` — this gives you `generated_at`, `confidence_score`, and `raw_context` for free.
> - Use `ConfigDict`, `Field` descriptions, and `json_schema_extra` examples.
> - Use `Literal` constraints wherever values are bounded.

### Step 2: Create the Prompt Template

Add a Markdown file to your accelerator's `prompts/` directory. The template must follow the [base template pattern](../designlab_core/prompts/base_template.md):

```markdown
<!-- my_accelerator/prompts/REQ-001-story-generation.md -->

# Senior Business Analyst

## Role & Context
You are a senior Business Analyst with 10+ years of experience in Agile methodologies.

## Task Description
Generate a comprehensive user story from the following feature description:
{{feature_description}}

## Constraints & Rules
- Output must be valid JSON — no markdown fences, no commentary.
- User story must follow "As a <role>, I want <goal>, so that <reason>" format.
- Include at least 3 acceptance criteria in Given/When/Then format.

## Input Context
{{feature_description}}

## Expected Output Format
The response must be a single, well-formed JSON object matching the schema below:
{
  "title": "US-NNN: Short title",
  "user_story": "As a...",
  "acceptance_criteria": [{"given": "...", "when": "...", "then": "..."}],
  "confidence_score": 0.0-1.0,
  "raw_context": "The original feature description"
}
```

> **Rules:**
> - Template ID = filename without `.md` → `REQ-001-story-generation`
> - Use the naming convention `DOMAIN-NNN-description.md`
> - Always include the `{{feature_description}}` placeholder (or whatever variable your pipeline injects)
> - The prompt loader auto-discovers templates in all subdirectories of `prompts/`

### Step 3: Wire the REST Endpoint (Router Factory)

Use `create_generation_router()` — **one line** produces a production-ready endpoint:

```python
# my_accelerator/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from designlab_core import create_generation_router
from my_accelerator.schemas.story import StoryOutput

app = FastAPI(title="BA Accelerator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
# Each call to create_generation_router() produces a POST endpoint that:
#   1. Accepts a GenerationRequest (feature_description + optional overrides)
#   2. Loads the prompt template
#   3. Calls the LLM via generate_from_pipeline()
#   4. Validates the response against your schema
#   5. Returns validated JSON

app.include_router(
    create_generation_router(
        prompt_id="REQ-001-story-generation",
        response_schema=StoryOutput,
        tags=["Story Generation"],
    ),
    prefix="/api/generate-story",
)

# Add more endpoints for other domains:
# app.include_router(
#     create_generation_router(
#         prompt_id="ARC-001-system-architecture",
#         response_schema=ArchitectureOutput,
#         tags=["Architecture Generation"],
#     ),
#     prefix="/api/generate-architecture",
# )

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

That's it. Three files — schema, template, app — and you have a complete AI microservice.

---

## Alternative: Direct Python Usage (No REST API)

If your accelerator doesn't need REST endpoints, use the pipeline directly:

```python
# Option 1: High-level orchestrator (recommended)
from designlab_core import generate_from_pipeline
from my_accelerator.schemas.story import StoryOutput

result = await generate_from_pipeline(
    template_id="REQ-001-story-generation",
    schema_class=StoryOutput,
    variables={"feature_description": "Allow VIP users to view reward points."},
)
print(result.title)                  # "US-001: VIP Reward Points Display"
print(result.acceptance_criteria)    # [AcceptanceCriterion(...), ...]

# Option 2: Override just what you need
result = await generate_from_pipeline(
    template_id="REQ-001-story-generation",
    schema_class=StoryOutput,
    variables={"feature_description": "Allow VIP users to view reward points."},
    model_name="gpt-4o",
    system_prompt="You are a fintech BA specialising in loyalty programs.",
    max_tokens=8192,
)

# Option 3: Full low-level control
from designlab_core import generate_response, load_prompt, validate_output

prompt = load_prompt("REQ-001-story-generation", variables={"feature_description": desc})
response = await generate_response(prompt=prompt, model_name="claude-sonnet")
result = validate_output(response.content, StoryOutput)
if result.is_valid:
    story = result.parsed
```

---

## Using Your Accelerator via REST API

Once your app is running (`uvicorn my_accelerator.app:app --port 8001`):

```bash
# Minimal request (all defaults)
curl -X POST http://localhost:8001/api/generate-story \
  -H "Content-Type: application/json" \
  -d '{"feature_description": "Allow VIP users to view reward points."}'

# Fully overridden request
curl -X POST http://localhost:8001/api/generate-story \
  -H "Content-Type: application/json" \
  -d '{
    "feature_description": "Allow VIP users to view reward points.",
    "model_name": "gpt-4o",
    "system_prompt": "You are a fintech BA. Output JSON only.",
    "template_id": "REQ-001-story-generation",
    "max_tokens": 8192
  }'
```

**Request schema (`GenerationRequest`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `feature_description` | `str` | ✅ (min 10 chars) | The feature to generate artifacts for |
| `model_name` | `str \| null` | Optional | Model alias override |
| `system_prompt` | `str \| null` | Optional | System prompt override |
| `template_id` | `str \| null` | Optional | Template ID override |
| `max_tokens` | `int \| null` | Optional | Max tokens override |

**Error responses:**

| Status | Meaning |
|--------|---------|
| `422` | Schema validation failed (LLM output didn't match your Pydantic model) |
| `502` | LLM provider error or retries exhausted |
| `504` | LLM request timed out |
| `500` | Unexpected server error |

---

## Recommended Project Structure for an Accelerator

```
my-accelerator/
├── my_accelerator/
│   ├── __init__.py
│   ├── app.py                  # FastAPI app with create_generation_router()
│   └── schemas/
│       ├── __init__.py
│       └── story.py            # StoryOutput(BaseAcceleratorOutput)
├── prompts/
│   └── requirements/
│       └── REQ-001-story-generation.md
├── tests/
│   └── test_story_generation.py
├── .env                         # API keys (from designlab-core's .env.example)
├── config.yaml                  # Model aliases, CORS origins
├── pyproject.toml
└── README.md
```

---

## Checklist for New Accelerators

- [ ] Schema defined — inherits from `BaseAcceleratorOutput` with `ConfigDict`, `Field`, and `json_schema_extra`
- [ ] Prompt template `.md` file created with `{{feature_description}}` placeholder (or custom variables)
- [ ] Template follows the naming convention `DOMAIN-NNN-description.md`
- [ ] Endpoint wired via `create_generation_router(prompt_id, response_schema)`
- [ ] `.env` configured with required `{PROVIDER}_API_KEY`
- [ ] `config.yaml` configured with model aliases
- [ ] Health check endpoint added
- [ ] Tests added with mocked `generate_response()`
- [ ] README documenting the accelerator's purpose and API surface
