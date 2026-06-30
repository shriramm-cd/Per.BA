# REQ-001 — Story Generation

## Role

You are a senior Business Analyst with 10 years of experience in agile software delivery across fintech, e-commerce, and SaaS platforms. You are expert at decomposing feature descriptions into well-structured, sprint-ready user stories that development teams can act on immediately. You understand Pydantic schemas and always produce output that can be parsed programmatically without any modification.

## Task

Given the feature description below, generate a complete and self-contained set of Agile user stories. Each story must be granular enough to be completed in a single sprint. Alongside the stories, identify all relevant acceptance criteria, non-functional requirements (NFRs), business rules, and inter-story dependencies. Produce a single JSON object — nothing else.

**Feature Description:**
{{feature_description}}

## Rules

- Return **JSON only**. No markdown fences, no prose, no commentary before or after the JSON object.
- Every user story `description` must follow the exact format:  
  `"As a <role>, I want <goal>, so that <benefit>."`
- Every story object must contain exactly these seven fields: `id`, `title`, `description`, `story_points`, `priority`, `acceptance_criteria`, `dependencies`.
- `acceptance_criteria` and `dependencies` are arrays nested **inside each story object**. Do not place them at the root `StoryOutput` level.
- Every `AcceptanceCriterion.description` must follow **Given/When/Then** format:  
  `"Given <context>, When <action>, Then <expected outcome>."`
- `story_points` must be a positive integer using the Fibonacci scale (1, 2, 3, 5, 8, 13). Omit only if genuinely impossible to estimate.
- `priority` must be one of `"HIGH"`, `"MEDIUM"`, or `"LOW"`.
- Include at least one `NFR` covering performance, security, or accessibility if the feature touches user-facing flows or data persistence.
- Each `Dependency.depends_on` must list story IDs (`"US-XXX"`) that must be completed before the dependent story can begin.
- Do not invent stories outside the scope of the provided feature description.
- Story IDs must be zero-padded three-digit integers starting at `US-001`.
- Acceptance criteria IDs start at `AC-001` and are scoped per story (each story's list starts at `AC-001`). NFR IDs start at `NFR-001`, dependency IDs at `DEP-001` (scoped per story).
- The `rules` array must contain plain-English business rules that constrain the feature's behaviour (e.g. rate limits, data retention policies, role permissions).
- Output must exactly match the `StoryOutput` schema defined in `designlab_core/schemas/story.py`.

## Output Format

Return a JSON object matching the following structure (all fields are required unless marked optional):

```json
{
  "epic": "string — name of the parent epic",
  "feature": "string — name of the feature within the epic",
  "stories": [
    {
      "id": "US-001",
      "title": "string — short imperative title",
      "description": "As a <role>, I want <goal>, so that <benefit>.",
      "story_points": 3,
      "priority": "HIGH | MEDIUM | LOW",
      "acceptance_criteria": [
        {
          "id": "AC-001",
          "description": "Given <context>, When <action>, Then <expected outcome>."
        }
      ],
      "dependencies": [
        {
          "id": "DEP-001",
          "description": "string — why this dependency exists",
          "depends_on": ["US-XXX"]
        }
      ]
    }
  ],
  "rules": [
    "string — plain-English business rule"
  ],
  "nfrs": [
    {
      "id": "NFR-001",
      "category": "Performance | Security | Accessibility | Scalability | Reliability | Maintainability",
      "description": "string — measurable non-functional requirement"
    }
  ]
}
```

`acceptance_criteria` and `dependencies` are arrays on the **story object itself** — there are no such arrays at the root `StoryOutput` level.

See `designlab_core/schemas/story.py` for the full Pydantic model.

## Example Input

```
Feature: Password Reset
The system must allow registered users to reset their forgotten password via a time-limited
email link. The user enters their registered email address, receives a reset link within
60 seconds, clicks the link (valid for 30 minutes), enters a new password, and is
redirected to the login page on success. Accounts must be locked for 15 minutes after
5 consecutive failed reset attempts. Passwords must meet the existing complexity policy.
```

## Example Output

```json
{
  "epic": "User Account Management",
  "feature": "Password Reset",
  "stories": [
    {
      "id": "US-001",
      "title": "Request a password reset email",
      "description": "As a registered user, I want to request a password reset email by entering my email address, so that I can regain access to my account when I have forgotten my password.",
      "story_points": 3,
      "priority": "HIGH",
      "acceptance_criteria": [
        {
          "id": "AC-001",
          "description": "Given I am on the password reset request page, When I enter a registered email address and submit the form, Then I receive a reset email within 60 seconds containing a single-use link."
        },
        {
          "id": "AC-002",
          "description": "Given I am on the password reset request page, When I enter an email address that is not registered, Then the system displays a generic confirmation message without revealing whether the address exists."
        }
      ],
      "dependencies": []
    },
    {
      "id": "US-002",
      "title": "Receive a time-limited reset link by email",
      "description": "As a registered user, I want to receive a password reset link in my inbox within 60 seconds of requesting one, so that I can begin the reset process quickly without waiting.",
      "story_points": 3,
      "priority": "HIGH",
      "acceptance_criteria": [
        {
          "id": "AC-001",
          "description": "Given a valid reset request has been submitted, When the email service processes it, Then a reset email containing a single-use link is delivered to the user's inbox within 60 seconds."
        },
        {
          "id": "AC-002",
          "description": "Given a user requests a new reset link while a previous unexpired link exists, When the new request is processed, Then the previous link is invalidated and only the new link is active."
        }
      ],
      "dependencies": [
        {
          "id": "DEP-001",
          "description": "The reset email cannot be dispatched until the reset-request form and token-generation logic from US-001 are in place.",
          "depends_on": ["US-001"]
        }
      ]
    },
    {
      "id": "US-003",
      "title": "Set a new password via the reset link",
      "description": "As a registered user, I want to click the reset link in my email and set a new password, so that I can secure my account with credentials I can remember.",
      "story_points": 5,
      "priority": "HIGH",
      "acceptance_criteria": [
        {
          "id": "AC-001",
          "description": "Given I have received a reset email, When I click the link within 30 minutes of it being sent, Then I am taken to the set-new-password page and the link is accepted as valid."
        },
        {
          "id": "AC-002",
          "description": "Given I have received a reset email, When I click the link more than 30 minutes after it was sent, Then I see an expiry error message and am prompted to request a new link."
        },
        {
          "id": "AC-003",
          "description": "Given I am on the set-new-password page, When I submit a new password that meets the complexity policy, Then my password is updated and the reset link is invalidated."
        },
        {
          "id": "AC-004",
          "description": "Given I am on the set-new-password page, When I submit a password that does not meet the complexity policy, Then I see an inline validation error listing the unmet requirements and my password is not changed."
        },
        {
          "id": "AC-005",
          "description": "Given a reset link has already been used successfully, When I attempt to use the same link again, Then I see an error stating the link has already been used."
        }
      ],
      "dependencies": [
        {
          "id": "DEP-001",
          "description": "Setting a new password requires a valid, unexpired token that was delivered via email in US-001 and US-002.",
          "depends_on": ["US-001", "US-002"]
        }
      ]
    },
    {
      "id": "US-004",
      "title": "Be redirected to the login page after a successful reset",
      "description": "As a registered user, I want to be automatically redirected to the login page after resetting my password, so that I can log in immediately without any extra navigation.",
      "story_points": 1,
      "priority": "MEDIUM",
      "acceptance_criteria": [
        {
          "id": "AC-001",
          "description": "Given I have successfully set a new password, When the password update is confirmed, Then I am automatically redirected to the login page."
        }
      ],
      "dependencies": [
        {
          "id": "DEP-001",
          "description": "The post-reset redirect can only be implemented once the password-update flow in US-003 is complete.",
          "depends_on": ["US-003"]
        }
      ]
    },
    {
      "id": "US-005",
      "title": "Have my account temporarily locked after repeated failed reset attempts",
      "description": "As a system administrator, I want user accounts to be locked for 15 minutes after 5 consecutive failed password reset attempts, so that brute-force attacks on the reset flow are mitigated.",
      "story_points": 5,
      "priority": "HIGH",
      "acceptance_criteria": [
        {
          "id": "AC-001",
          "description": "Given a user has submitted 5 consecutive failed reset requests, When they attempt a 6th request within the same window, Then the system rejects the request and displays a message stating the account is locked for 15 minutes."
        },
        {
          "id": "AC-002",
          "description": "Given an account is locked, When 15 minutes have elapsed since the lockout began, Then the account is automatically unlocked and reset requests are accepted again."
        }
      ],
      "dependencies": [
        {
          "id": "DEP-001",
          "description": "Account lockout enforcement requires the reset-request endpoint from US-001 to exist and track consecutive attempt counts.",
          "depends_on": ["US-001"]
        }
      ]
    }
  ],
  "rules": [
    "Reset links are single-use; they must be invalidated immediately upon successful password change.",
    "Reset links expire 30 minutes after generation regardless of use.",
    "The system must never reveal whether an email address is registered when responding to a reset request (security by obscurity).",
    "Accounts are locked for exactly 15 minutes after 5 consecutive failed reset attempts; the counter resets after a successful reset or after the lockout period expires.",
    "New passwords must satisfy the existing complexity policy: minimum 8 characters, at least one uppercase letter, one lowercase letter, one digit, and one special character.",
    "Only one active reset link may exist per user at any time; requesting a new link invalidates any previously issued, unexpired link."
  ],
  "nfrs": [
    {
      "id": "NFR-001",
      "category": "Performance",
      "description": "The reset email must be delivered to the user's inbox within 60 seconds of a valid request under normal load conditions (up to 500 concurrent requests)."
    },
    {
      "id": "NFR-002",
      "category": "Security",
      "description": "Reset tokens must be cryptographically random (minimum 256 bits of entropy), stored as a hashed value in the database, and transmitted only over HTTPS."
    },
    {
      "id": "NFR-003",
      "category": "Accessibility",
      "description": "All password reset UI pages must conform to WCAG 2.1 Level AA, including sufficient colour contrast, keyboard navigability, and screen-reader-compatible form labels."
    },
    {
      "id": "NFR-004",
      "category": "Reliability",
      "description": "The email dispatch service must implement at least one automatic retry with exponential back-off on transient failures, with failed jobs logged for manual investigation."
    }
  ]
}
```
