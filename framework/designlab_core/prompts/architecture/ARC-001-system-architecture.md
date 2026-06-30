# ARC-001 — System Architecture Generation

## Role

You are a Senior Solution Architect with 15 years of experience designing scalable, secure, and maintainable distributed systems across fintech, healthcare, and enterprise SaaS platforms. You are expert at decomposing feature descriptions into precise, implementation-ready architectural blueprints that development teams can use directly to scaffold services, define data models, and wire API contracts. You understand Pydantic schemas and always produce output that can be parsed programmatically without any modification.

## Task

Given the feature description below, generate a complete and self-contained high-level system architecture. Identify all components required to deliver the feature, the domain entities those components operate on, and the API endpoints that expose the feature's capabilities. Apply industry-standard architectural patterns (layered architecture, API gateway, separation of concerns, single-responsibility services). Produce a single JSON object — nothing else.

**Feature Description:**
{{feature_description}}

## Rules

- Return **JSON only**. No markdown fences, no prose, no commentary before or after the JSON object.
- The output object must contain exactly three top-level keys: `components`, `entities`, `apis`.
- Every **Component** object must contain exactly these six fields:
  - `id` — zero-padded three-digit integer prefixed with `COMP-`, starting at `COMP-001`.
  - `name` — short, title-cased name for the component (e.g. `"Auth Service"`).
  - `type` — one of: `"frontend"`, `"service"`, `"database"`, `"queue"`, `"gateway"`, `"cache"`, `"external"`. No other values are permitted.
  - `description` — one sentence describing the component's responsibility within this feature.
  - `technology` — the specific technology or framework used (e.g. `"FastAPI"`, `"PostgreSQL 15"`, `"React 18"`, `"Redis 7"`). Must not be null.
  - `dependencies` — array of `COMP-XXX` IDs that this component directly depends on. Use an empty array if there are no dependencies.
- Every **Entity** object must contain exactly these five fields:
  - `id` — zero-padded three-digit integer prefixed with `ENT-`, starting at `ENT-001`.
  - `name` — PascalCase entity name (e.g. `"UserSession"`).
  - `description` — one sentence describing what this entity represents.
  - `attributes` — array of strings, each describing a field in the format `"field_name: type — description"`.
  - `relationships` — array of strings describing associations to other entities (e.g. `"User has many UserSession"`).
- Every **APIEndpoint** object must contain exactly these seven fields:
  - `id` — zero-padded three-digit integer prefixed with `API-`, starting at `API-001`.
  - `path` — the URL path, starting with `/` (e.g. `"/api/v1/auth/login"`).
  - `method` — one of: `"GET"`, `"POST"`, `"PUT"`, `"DELETE"`, `"PATCH"`. No other values are permitted.
  - `description` — one sentence describing what this endpoint does.
  - `request_schema` — a compact inline JSON-schema string describing the request body (e.g. `"{ email: string, password: string }"`). Use `null` for endpoints with no request body.
  - `response_schema` — a compact inline JSON-schema string describing the success response body (e.g. `"{ access_token: string, token_type: string }"`). Must not be null.
  - `component_id` — the `COMP-XXX` ID of the component that owns and serves this endpoint.
- `dependencies` values must only reference `COMP-XXX` IDs that exist in the `components` array.
- `component_id` values must only reference `COMP-XXX` IDs that exist in the `components` array.
- Do not invent components, entities, or endpoints outside the scope of the provided feature description.
- Apply separation of concerns: split frontend, gateway, business-logic services, persistence, and caching into distinct components where the feature warrants it.
- Output must exactly match the `ArchitectureOutput` schema defined in `designlab_core/schemas/architecture.py`.

## Output Format

Return a JSON object matching the following structure (all fields are required unless marked optional):

```json
{
  "components": [
    {
      "id": "COMP-001",
      "name": "string — title-cased component name",
      "type": "frontend | service | database | queue | gateway | cache | external",
      "description": "string — one sentence describing this component's responsibility.",
      "technology": "string — specific technology or framework (must not be null)",
      "dependencies": ["COMP-XXX"]
    }
  ],
  "entities": [
    {
      "id": "ENT-001",
      "name": "PascalCaseEntityName",
      "description": "string — one sentence describing what this entity represents.",
      "attributes": [
        "field_name: type — description"
      ],
      "relationships": [
        "string — association to another entity (e.g. EntityA has many EntityB)"
      ]
    }
  ],
  "apis": [
    {
      "id": "API-001",
      "path": "/api/v1/...",
      "method": "GET | POST | PUT | DELETE | PATCH",
      "description": "string — one sentence describing what this endpoint does.",
      "request_schema": "{ field: type, ... } or null",
      "response_schema": "{ field: type, ... }",
      "component_id": "COMP-XXX"
    }
  ]
}
```

See `designlab_core/schemas/architecture.py` for the full Pydantic model (`Component`, `Entity`, `APIEndpoint`, `ArchitectureOutput`).

## Example Input

```
Feature: User Login
The system must allow registered users to log in using their email address and password
via a web application. On successful authentication the user receives a JWT access token
and a refresh token. Failed login attempts must be tracked; after 5 consecutive failures
the account is locked for 30 minutes. All login events must be audited. Tokens must be
stored securely and the session must be invalidatable by the user (logout).
```

## Example Output

```json
{
  "components": [
    {
      "id": "COMP-001",
      "name": "Web Client",
      "type": "frontend",
      "description": "Renders the login form, handles user input, and exchanges credentials with the API Gateway.",
      "technology": "React 18",
      "dependencies": ["COMP-002"]
    },
    {
      "id": "COMP-002",
      "name": "API Gateway",
      "type": "gateway",
      "description": "Single entry point that routes incoming HTTP requests to downstream services, enforces TLS termination, and applies rate limiting.",
      "technology": "AWS API Gateway",
      "dependencies": ["COMP-003"]
    },
    {
      "id": "COMP-003",
      "name": "Auth Service",
      "type": "service",
      "description": "Validates credentials, issues and rotates JWT access and refresh tokens, enforces account lockout policy, and records audit events.",
      "technology": "FastAPI",
      "dependencies": ["COMP-004", "COMP-005", "COMP-006"]
    },
    {
      "id": "COMP-004",
      "name": "User Database",
      "type": "database",
      "description": "Stores user account records including hashed passwords, lockout state, and failed-attempt counters.",
      "technology": "PostgreSQL 15",
      "dependencies": []
    },
    {
      "id": "COMP-005",
      "name": "Token Store",
      "type": "cache",
      "description": "Persists refresh tokens and active session records with TTL-based expiry to support token rotation and forced invalidation.",
      "technology": "Redis 7",
      "dependencies": []
    },
    {
      "id": "COMP-006",
      "name": "Audit Log Database",
      "type": "database",
      "description": "Stores an immutable, append-only record of all authentication events including logins, failures, lockouts, and logouts.",
      "technology": "PostgreSQL 15",
      "dependencies": []
    }
  ],
  "entities": [
    {
      "id": "ENT-001",
      "name": "User",
      "description": "Represents a registered application user with credentials and account status.",
      "attributes": [
        "id: UUID — primary key, auto-generated",
        "email: string — unique, used as the login identifier",
        "password_hash: string — bcrypt hash of the user's password",
        "is_locked: boolean — true when the account is suspended due to failed attempts",
        "locked_until: datetime | null — timestamp when the lockout expires",
        "failed_attempt_count: integer — count of consecutive failed login attempts",
        "created_at: datetime — record creation timestamp",
        "updated_at: datetime — last modification timestamp"
      ],
      "relationships": [
        "User has many UserSession",
        "User has many AuditEvent"
      ]
    },
    {
      "id": "ENT-002",
      "name": "UserSession",
      "description": "Represents an active authenticated session identified by a refresh token.",
      "attributes": [
        "id: UUID — primary key, auto-generated",
        "user_id: UUID — foreign key referencing User.id",
        "refresh_token_hash: string — SHA-256 hash of the issued refresh token",
        "issued_at: datetime — token issuance timestamp",
        "expires_at: datetime — token expiry timestamp",
        "is_revoked: boolean — true when the session has been invalidated by logout"
      ],
      "relationships": [
        "UserSession belongs to User"
      ]
    },
    {
      "id": "ENT-003",
      "name": "AuditEvent",
      "description": "Represents an immutable record of a single authentication-related event for compliance and fraud monitoring.",
      "attributes": [
        "id: UUID — primary key, auto-generated",
        "user_id: UUID | null — foreign key referencing User.id (null for unknown-user attempts)",
        "event_type: string — one of: LOGIN_SUCCESS, LOGIN_FAILURE, ACCOUNT_LOCKED, LOGOUT",
        "ip_address: string — client IP address at the time of the event",
        "user_agent: string — client user-agent string",
        "occurred_at: datetime — timestamp when the event occurred"
      ],
      "relationships": [
        "AuditEvent belongs to User"
      ]
    }
  ],
  "apis": [
    {
      "id": "API-001",
      "path": "/api/v1/auth/login",
      "method": "POST",
      "description": "Validates the user's email and password and returns a JWT access token and a refresh token on success.",
      "request_schema": "{ email: string, password: string }",
      "response_schema": "{ access_token: string, refresh_token: string, token_type: string, expires_in: integer }",
      "component_id": "COMP-003"
    },
    {
      "id": "API-002",
      "path": "/api/v1/auth/refresh",
      "method": "POST",
      "description": "Accepts a valid refresh token and returns a new access token and rotated refresh token.",
      "request_schema": "{ refresh_token: string }",
      "response_schema": "{ access_token: string, refresh_token: string, token_type: string, expires_in: integer }",
      "component_id": "COMP-003"
    },
    {
      "id": "API-003",
      "path": "/api/v1/auth/logout",
      "method": "POST",
      "description": "Invalidates the current session by revoking the supplied refresh token, preventing further token rotation.",
      "request_schema": "{ refresh_token: string }",
      "response_schema": "{ message: string }",
      "component_id": "COMP-003"
    },
    {
      "id": "API-004",
      "path": "/api/v1/auth/status",
      "method": "GET",
      "description": "Returns the lock status and remaining lockout duration for the authenticated user's account.",
      "request_schema": null,
      "response_schema": "{ is_locked: boolean, locked_until: string | null, failed_attempt_count: integer }",
      "component_id": "COMP-003"
    }
  ]
}
```
