"""
designlab_core.schemas.architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic models for Architecture generation output.


Status: FINALISED — Literal constraints added, docstrings complete,
        json_schema_extra examples added, Field descriptions improved.

Change log (from scaffold):
- Component.type restricted to Literal enum.
- APIEndpoint.method restricted to Literal enum.
- model_config with json_schema_extra added to all models.
- Comprehensive docstrings and Field descriptions added throughout.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Component(BaseModel):
    """
    A discrete architectural building block that plays a defined role in
    delivering the feature.

    Components map to deployable or logical units: a frontend application,
    a backend service, a database, a message queue, an API gateway, or a
    cache. Every component has a single responsibility. Complex features are
    decomposed into multiple components that communicate through well-defined
    interfaces.

    The ``dependencies`` field records which other components this component
    directly calls or reads from, forming a directed dependency graph that
    can be used to reason about deployment order and blast radius.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "COMP-001",
                "name": "Auth Service",
                "type": "service",
                "description": (
                    "Validates user credentials, issues JWT access and refresh "
                    "tokens, and enforces account lockout policy."
                ),
                "technology": "FastAPI",
                "dependencies": ["COMP-002", "COMP-003"],
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this component within the ArchitectureOutput. "
            "Format: COMP-NNN (zero-padded three digits), e.g. COMP-001, COMP-012. "
            "IDs are assigned sequentially starting at COMP-001 and must be "
            "referenced consistently in APIEndpoint.component_id and in other "
            "components' dependencies lists."
        ),
    )
    name: str = Field(
        ...,
        description=(
            "Short, title-cased human-readable name for the component. "
            "Should reflect the component's role in the system. "
            "Examples: 'Auth Service', 'User Database', 'API Gateway', "
            "'Notification Queue'."
        ),
    )
    type: Literal["service", "database", "queue", "gateway", "frontend"] = Field(
        ...,
        description=(
            "Architectural category of this component. Permitted values: "
            "service — a backend application or microservice that contains "
            "business logic; "
            "database — a persistent data store (relational or document); "
            "queue — an asynchronous message broker or event bus; "
            "gateway — an API gateway, load balancer, or reverse proxy that "
            "routes traffic to downstream services; "
            "frontend — a client-side application (web, mobile, or desktop)."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "One sentence describing this component's single responsibility "
            "within the context of the feature being designed. Should make "
            "clear what the component does and what it owns, without describing "
            "the responsibilities of its dependencies."
        ),
    )
    technology: str | None = Field(
        default=None,
        description=(
            "The specific technology, framework, or managed service used to "
            "implement this component. Should be as precise as possible, "
            "including the major version where relevant. "
            "Examples: 'FastAPI', 'PostgreSQL 15', 'React 18', 'Redis 7', "
            "'AWS SQS', 'Kong Gateway'. Set to null only when the technology "
            "has not yet been decided."
        ),
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "List of COMP-NNN IDs that this component directly depends on — "
            "i.e. components this component calls, reads from, or writes to "
            "at runtime. All referenced IDs must exist in the same "
            "ArchitectureOutput.components list. Use an empty list when this "
            "component has no runtime dependencies (e.g. a standalone database)."
        ),
    )


class Entity(BaseModel):
    """
    A domain entity that is stored, processed, or exchanged within the feature.

    Entities correspond to the core nouns of the domain model — the data
    structures that components operate on. They are implementation-agnostic:
    an Entity describes what data exists and how it relates to other data,
    not which database table or ORM model it maps to.

    ``attributes`` use the format ``"field_name: type — description"`` so that
    a developer can derive a database schema or Pydantic model directly from
    this list without additional specification.

    ``relationships`` describe associations to other entities in plain English
    (e.g. ``"User has many UserSession"``) and are used to generate the
    entity-relationship diagram for the feature.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "ENT-001",
                "name": "User",
                "description": (
                    "Represents a registered application user with credentials, "
                    "account status, and lockout state."
                ),
                "attributes": [
                    "id: UUID — primary key, auto-generated",
                    "email: string — unique login identifier, stored in lowercase",
                    "password_hash: string — bcrypt hash of the user's password",
                    "is_locked: boolean — true when the account is suspended",
                    "failed_attempt_count: integer — consecutive failed login attempts",
                    "created_at: datetime — record creation timestamp",
                ],
                "relationships": [
                    "User has many UserSession",
                    "User has many AuditEvent",
                ],
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this entity within the ArchitectureOutput. "
            "Format: ENT-NNN (zero-padded three digits), e.g. ENT-001. "
            "IDs are assigned sequentially starting at ENT-001."
        ),
    )
    name: str = Field(
        ...,
        description=(
            "PascalCase name for the entity matching the domain language used "
            "by the team. Should be a singular noun. "
            "Examples: 'User', 'UserSession', 'AuditEvent', 'RefreshToken'."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "One sentence describing what real-world concept or data this entity "
            "represents and its role within the feature."
        ),
    )
    attributes: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of field definitions for this entity. Each entry must "
            "follow the format: 'field_name: type — description'. "
            "The type should use standard notation (UUID, string, integer, boolean, "
            "datetime, list[string]). The description should note constraints such "
            "as uniqueness, nullability, or default values. "
            "Example: 'email: string — unique, stored in lowercase, used as the "
            "login identifier'."
        ),
    )
    relationships: list[str] = Field(
        default_factory=list,
        description=(
            "List of plain-English association statements describing how this "
            "entity relates to other entities in the ArchitectureOutput. "
            "Use standard cardinality language: 'has one', 'has many', "
            "'belongs to', 'has and belongs to many'. "
            "Example: 'User has many UserSession'."
        ),
    )


class APIEndpoint(BaseModel):
    """
    A single REST API endpoint exposed by one of the feature's components.

    Each endpoint represents one HTTP operation on one resource path. The
    ``request_schema`` and ``response_schema`` fields use compact inline
    JSON-schema strings rather than nested objects so that the full endpoint
    definition remains readable in a single JSON document.

    ``component_id`` ties the endpoint back to the component that owns and
    serves it, enabling code generators to place the route handler in the
    correct service.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "API-001",
                "path": "/api/v1/auth/login",
                "method": "POST",
                "description": (
                    "Authenticates a user with email and password and returns "
                    "a JWT access token and refresh token on success."
                ),
                "request_schema": "{ email: string, password: string }",
                "response_schema": (
                    "{ access_token: string, refresh_token: string, "
                    "token_type: string, expires_in: integer }"
                ),
                "component_id": "COMP-001",
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this endpoint within the ArchitectureOutput. "
            "Format: API-NNN (zero-padded three digits), e.g. API-001. "
            "IDs are assigned sequentially starting at API-001."
        ),
    )
    path: str = Field(
        ...,
        description=(
            "The URL path for this endpoint, starting with '/'. Use snake_case "
            "path segments and {param} notation for path parameters. All paths "
            "should be versioned under /api/v1/. "
            "Examples: '/api/v1/auth/login', '/api/v1/users/{user_id}'."
        ),
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        ...,
        description=(
            "HTTP method for this endpoint. Permitted values: "
            "GET — retrieve a resource without side effects; "
            "POST — create a resource or trigger an action; "
            "PUT — fully replace an existing resource; "
            "DELETE — remove a resource; "
            "PATCH — partially update an existing resource."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "One sentence describing what this endpoint does and what it returns "
            "on a successful response. Should make the endpoint's purpose clear "
            "without needing to read the request or response schemas."
        ),
    )
    request_schema: str | None = Field(
        default=None,
        description=(
            "Compact inline description of the request body payload using "
            "JSON-schema-like notation, e.g. '{ email: string, password: string }'. "
            "Set to null for GET and DELETE endpoints that carry no request body. "
            "For all other methods this field must describe the expected payload."
        ),
    )
    response_schema: str | None = Field(
        default=None,
        description=(
            "Compact inline description of the success response body using "
            "JSON-schema-like notation, e.g. "
            "'{ access_token: string, token_type: string }'. "
            "Should represent the 2xx success response. Must not be null for "
            "endpoints that return a response body."
        ),
    )
    component_id: str = Field(
        ...,
        description=(
            "COMP-NNN ID of the component that owns and serves this endpoint. "
            "Must reference a valid ID present in ArchitectureOutput.components. "
            "Used by code generators to place the route handler in the correct "
            "service and by documentation tools to group endpoints by service."
        ),
    )


class ArchitectureOutput(BaseModel):
    """
    Root output model for the /api/generate-architecture endpoint.

    Returned by generate_response() after the LLM response is parsed from JSON.
    Represents a complete, self-contained high-level system architecture for a
    single feature: the components that implement it, the domain entities those
    components operate on, and the API endpoints that expose its capabilities.

    The three lists are cross-referenced by ID:
    - ``APIEndpoint.component_id`` → ``Component.id``
    - ``Component.dependencies`` → other ``Component.id`` values
    - ``Entity.relationships`` reference other entity names by convention

    This structure is intentionally technology-agnostic at the output level.
    Technology choices are captured on each ``Component`` via the ``technology``
    field rather than being baked into the schema itself.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "components": [
                    {
                        "id": "COMP-001",
                        "name": "Auth Service",
                        "type": "service",
                        "description": "Validates credentials and issues JWT tokens.",
                        "technology": "FastAPI",
                        "dependencies": ["COMP-002"],
                    },
                    {
                        "id": "COMP-002",
                        "name": "User Database",
                        "type": "database",
                        "description": "Stores user accounts and hashed passwords.",
                        "technology": "PostgreSQL 15",
                        "dependencies": [],
                    },
                ],
                "entities": [
                    {
                        "id": "ENT-001",
                        "name": "User",
                        "description": "A registered application user.",
                        "attributes": [
                            "id: UUID — primary key",
                            "email: string — unique login identifier",
                            "password_hash: string — bcrypt hash",
                        ],
                        "relationships": ["User has many UserSession"],
                    }
                ],
                "apis": [
                    {
                        "id": "API-001",
                        "path": "/api/v1/auth/login",
                        "method": "POST",
                        "description": "Authenticates a user and returns JWT tokens.",
                        "request_schema": "{ email: string, password: string }",
                        "response_schema": "{ access_token: string, token_type: string }",
                        "component_id": "COMP-001",
                    }
                ],
            }
        }
    )

    components: list[Component] = Field(
        default_factory=list,
        description=(
            "Ordered list of architectural components that together implement "
            "the feature. Should be ordered from infrastructure (databases, queues) "
            "through services to frontend so that the dependency graph flows "
            "naturally from top to bottom. Every component_id referenced in "
            "apis must have a corresponding entry here."
        ),
    )
    entities: list[Entity] = Field(
        default_factory=list,
        description=(
            "List of domain entities that the feature's components create, read, "
            "update, or delete. Entities are implementation-agnostic and describe "
            "the data model at the domain level, independent of any specific "
            "database schema or ORM."
        ),
    )
    apis: list[APIEndpoint] = Field(
        default_factory=list,
        description=(
            "List of REST API endpoints exposed by the feature's components. "
            "Each endpoint is owned by exactly one component identified by "
            "component_id. Endpoints should cover the complete surface area "
            "needed to implement all user stories associated with the feature."
        ),
    )
