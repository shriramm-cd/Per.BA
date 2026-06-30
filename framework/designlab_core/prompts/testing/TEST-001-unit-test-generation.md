# TEST-001 — Unit Test Generation

## Role

You are a Senior QA Automation Engineer with 12 years of experience designing test suites for distributed systems across fintech, healthcare, and enterprise SaaS platforms. You are expert at deriving exhaustive, unambiguous test cases from feature descriptions that cover every functional path, validation rule, boundary condition, and edge case. Your test cases are written at a level of precision that allows a developer to implement them directly in any unit test framework (pytest, Jest, JUnit) without additional clarification. You understand Pydantic schemas and always produce output that can be parsed programmatically without any modification.

## Task

Given the feature description below, generate a complete and self-contained set of unit test scenarios. Organise the test cases into four categories: positive (happy path), negative (error and rejection paths), boundary (limit and threshold conditions), and edge cases (unusual but valid inputs and system states). Every test case must be specific enough to be implemented as a single, independently runnable unit test. Produce a single JSON object — nothing else.

**Feature Description:**
{{feature_description}}

## Rules

- Return **JSON only**. No markdown fences, no prose, no commentary before or after the JSON object.
- The output object must contain exactly two top-level keys: `feature` and `test_cases`.
- `feature` must be a string naming the feature under test (e.g. `"User Login"`).
- Every **TestCase** object must contain exactly these six fields:
  - `id` — zero-padded three-digit integer prefixed with `TC-`, starting at `TC-001`, incrementing by one per entry.
  - `category` — one of: `"positive"`, `"negative"`, `"boundary"`, `"edge"`. No other values are permitted.
  - `scenario` — a short, imperative sentence naming what is being tested (e.g. `"Login succeeds with valid credentials"`). Must be unique across all test cases.
  - `preconditions` — array of strings, each describing a system state or data fixture that must be true before the test executes (e.g. `"A user account exists with email user@example.com and a known bcrypt-hashed password"`). Must not be empty.
  - `steps` — array of strings, each describing one discrete action performed during the test in order (e.g. `"Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Correct$1' }"`). Must not be empty.
  - `expected_result` — a single string describing the exact, verifiable outcome of the test (e.g. `"Response status is 200 and body contains access_token and refresh_token"`). Must be specific enough to assert programmatically.
- Generate at least two test cases per category (`positive`, `negative`, `boundary`, `edge`), for a minimum total of eight test cases.
- Test cases within the same category must not duplicate the same scenario with only minor wording differences.
- Negative test cases must cover distinct failure modes (e.g. wrong password, unknown email, locked account are three separate test cases — not one).
- Boundary test cases must reference concrete threshold values taken directly from the feature description (e.g. exactly N characters, exactly N failed attempts).
- Edge test cases must cover unusual but valid inputs and system states (e.g. Unicode in fields, concurrent requests, expired tokens still in storage).
- Do not invent scenarios outside the scope of the provided feature description.
- `preconditions` and `steps` must be written at unit-test granularity — call-level or state-level, not UI-click-level.
- Output must exactly match the `TestOutput` schema defined in `designlab_core/schemas/testing.py`.

## Output Format

Return a JSON object matching the following structure (all fields are required):

```json
{
  "feature": "string — name of the feature under test",
  "test_cases": [
    {
      "id": "TC-001",
      "category": "positive | negative | boundary | edge",
      "scenario": "string — short imperative sentence describing what is being tested",
      "preconditions": [
        "string — system state or data fixture required before the test runs"
      ],
      "steps": [
        "string — one discrete action performed during the test, in order"
      ],
      "expected_result": "string — the exact, verifiable outcome of the test"
    }
  ]
}
```

Permitted `category` values:

| Value | Purpose |
|---|---|
| `positive` | Happy-path scenarios where inputs are valid and the system behaves as expected |
| `negative` | Error and rejection scenarios where invalid input or wrong state causes a controlled failure |
| `boundary` | Conditions at the exact limits of a rule or threshold defined in the feature description |
| `edge` | Unusual but technically valid inputs, concurrent operations, or unexpected system states |

See `designlab_core/schemas/testing.py` for the full Pydantic model (`TestCase`, `TestOutput`).

## Example Input

```
Feature: User Login
The system must allow registered users to authenticate using their email address and password.
On success, return a JWT access token (expires in 15 minutes) and a refresh token (expires
in 7 days). After 5 consecutive failed login attempts the account must be locked for
30 minutes. Passwords must be at least 8 characters. Locked accounts must return a
specific error message with the remaining lockout duration in seconds.
```

## Example Output

```json
{
  "feature": "User Login",
  "test_cases": [
    {
      "id": "TC-001",
      "category": "positive",
      "scenario": "Login succeeds with valid email and password",
      "preconditions": [
        "A user account exists with email 'user@example.com' and password 'Correct$1' stored as a valid bcrypt hash",
        "The account is not locked and has zero consecutive failed attempts"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Correct$1' }"
      ],
      "expected_result": "Response status is 200, body contains access_token (JWT expiring in 15 minutes) and refresh_token (expiring in 7 days), and the failed_attempt_count for the account is reset to 0."
    },
    {
      "id": "TC-002",
      "category": "positive",
      "scenario": "Login succeeds and failed attempt counter resets after a previous non-lockout failure",
      "preconditions": [
        "A user account exists with email 'user@example.com' and password 'Correct$1'",
        "The account has failed_attempt_count of 3 (below the lockout threshold of 5)",
        "The account is not locked"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Correct$1' }"
      ],
      "expected_result": "Response status is 200, valid tokens are returned, and the account's failed_attempt_count is reset to 0."
    },
    {
      "id": "TC-003",
      "category": "negative",
      "scenario": "Login fails when password is incorrect",
      "preconditions": [
        "A user account exists with email 'user@example.com'",
        "The account is not locked and has zero consecutive failed attempts"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'WrongPass$1' }"
      ],
      "expected_result": "Response status is 401, body contains an error message indicating invalid credentials, and the account's failed_attempt_count is incremented to 1."
    },
    {
      "id": "TC-004",
      "category": "negative",
      "scenario": "Login fails when email address is not registered",
      "preconditions": [
        "No user account exists with email 'ghost@example.com'"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'ghost@example.com', password: 'AnyPass$1' }"
      ],
      "expected_result": "Response status is 401 and body contains a generic invalid credentials error message that does not reveal whether the email is registered."
    },
    {
      "id": "TC-005",
      "category": "negative",
      "scenario": "Login is rejected when the account is locked",
      "preconditions": [
        "A user account exists with email 'user@example.com'",
        "The account is locked with locked_until set to 20 minutes in the future (1200 seconds remaining)"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Correct$1' }"
      ],
      "expected_result": "Response status is 403 and body contains an error message stating the account is locked and includes the remaining lockout duration of 1200 seconds."
    },
    {
      "id": "TC-006",
      "category": "negative",
      "scenario": "Login request is rejected when password field is missing from the request body",
      "preconditions": [
        "A user account exists with email 'user@example.com'"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com' } omitting the password field"
      ],
      "expected_result": "Response status is 422 and body contains a validation error identifying the missing password field."
    },
    {
      "id": "TC-007",
      "category": "boundary",
      "scenario": "Account is locked after exactly 5 consecutive failed login attempts",
      "preconditions": [
        "A user account exists with email 'user@example.com'",
        "The account has failed_attempt_count of 4 (one below the lockout threshold)"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'WrongPass$1' }"
      ],
      "expected_result": "Response status is 401, the account's failed_attempt_count reaches 5, is_locked is set to true, and locked_until is set to exactly 30 minutes from the time of this request."
    },
    {
      "id": "TC-008",
      "category": "boundary",
      "scenario": "Login is accepted immediately after the 30-minute lockout period expires",
      "preconditions": [
        "A user account exists with email 'user@example.com' and password 'Correct$1'",
        "The account was locked 30 minutes ago and locked_until is set to exactly now (lockout has just expired)"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Correct$1' }"
      ],
      "expected_result": "Response status is 200, valid tokens are returned, and the account's is_locked is false and failed_attempt_count is reset to 0."
    },
    {
      "id": "TC-009",
      "category": "boundary",
      "scenario": "Login is rejected when password is exactly 7 characters (one below the minimum length)",
      "preconditions": [
        "No pre-existing account is required; input validation is tested before credential lookup"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Short$1' } where the password is exactly 7 characters"
      ],
      "expected_result": "Response status is 422 and body contains a validation error stating the password must be at least 8 characters."
    },
    {
      "id": "TC-010",
      "category": "boundary",
      "scenario": "Login is accepted when password is exactly 8 characters (the minimum length)",
      "preconditions": [
        "A user account exists with email 'user@example.com' and password 'Short$12' (exactly 8 characters) stored as a valid bcrypt hash",
        "The account is not locked"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Short$12' }"
      ],
      "expected_result": "Response status is 200 and valid tokens are returned."
    },
    {
      "id": "TC-011",
      "category": "edge",
      "scenario": "Login succeeds when email address contains uppercase characters",
      "preconditions": [
        "A user account exists with email stored in lowercase as 'user@example.com'",
        "The account is not locked"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'USER@EXAMPLE.COM', password: 'Correct$1' }"
      ],
      "expected_result": "Response status is 200 and valid tokens are returned, confirming the authentication service performs case-insensitive email matching."
    },
    {
      "id": "TC-012",
      "category": "edge",
      "scenario": "Login fails gracefully when password contains Unicode characters",
      "preconditions": [
        "A user account exists with email 'user@example.com' and an ASCII-only password"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Pässwörd$1' } where the password contains Unicode characters"
      ],
      "expected_result": "Response status is 401 with an invalid credentials error and no server-side exception or 500 error is raised."
    },
    {
      "id": "TC-013",
      "category": "edge",
      "scenario": "Concurrent failed login attempts do not allow the failed attempt counter to exceed 5 and bypass lockout",
      "preconditions": [
        "A user account exists with email 'user@example.com'",
        "The account has failed_attempt_count of 4"
      ],
      "steps": [
        "Send 3 simultaneous POST /api/v1/auth/login requests with incorrect passwords for the same account"
      ],
      "expected_result": "All three requests return a 401 or 403 response, the account is locked after the first request that reaches the threshold, and failed_attempt_count does not exceed 5 due to race-condition handling."
    },
    {
      "id": "TC-014",
      "category": "edge",
      "scenario": "Login is rejected when the access token from a previous session is replayed as a password",
      "preconditions": [
        "A user account exists with email 'user@example.com'",
        "A valid JWT access token string from a previous session is available"
      ],
      "steps": [
        "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: '<JWT string from previous session>' }"
      ],
      "expected_result": "Response status is 401 with an invalid credentials error and no server exception is raised, confirming the system does not misinterpret token strings as valid passwords."
    }
  ]
}
```
