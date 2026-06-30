"""
designlab_core.schemas.story
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic models for Story generation output.


Status: FINALISED — field types locked, validators added, docstrings complete.

Change log (from scaffold):
- AcceptanceCriterion and Dependency moved from StoryOutput into Story so that
  each story is fully self-contained.
- Story.priority restricted to Literal["HIGH", "MEDIUM", "LOW"].
- Story.story_points validated to be > 0 when provided.
- model_config with json_schema_extra added to all models.
- Comprehensive docstrings and Field descriptions added throughout.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal


class AcceptanceCriterion(BaseModel):
    """
    A single, verifiable acceptance criterion belonging to one Story.

    Each criterion is written in Given/When/Then format so that it can be
    executed directly as a test case without further interpretation:

        Given <precondition>, When <action>, Then <expected outcome>.

    Acceptance criteria are scoped to the story that owns them. IDs are
    unique within a story's list and start at AC-001.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "AC-001",
                "description": (
                    "Given a registered user, "
                    "When valid credentials are submitted, "
                    "Then a JWT access token is returned with HTTP 200."
                ),
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this criterion within its parent story. "
            "Format: AC-NNN (zero-padded three digits), e.g. AC-001, AC-002. "
            "Numbering restarts at AC-001 for each story."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "The acceptance criterion written in Given/When/Then format: "
            "'Given <context>, When <action>, Then <expected outcome>.' "
            "Must be specific enough to be asserted programmatically."
        ),
    )


class Dependency(BaseModel):
    """
    An inter-story dependency that declares which other stories must be
    completed before the owning story can begin.

    Dependencies are directional: the story that owns this object depends
    on the stories listed in depends_on. A story with an empty depends_on
    list has no prerequisites and can be started immediately.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "DEP-001",
                "description": (
                    "The email dispatch service cannot be built until the "
                    "token generation logic in US-001 is in place."
                ),
                "depends_on": ["US-001"],
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this dependency within its parent story. "
            "Format: DEP-NNN (zero-padded three digits), e.g. DEP-001. "
            "Numbering restarts at DEP-001 for each story."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "Plain-English explanation of why this dependency exists and "
            "what the owning story requires from the upstream stories."
        ),
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of story IDs that must be completed before the "
            "owning story can begin. Each entry must be a valid US-NNN "
            "identifier that exists elsewhere in the same StoryOutput. "
            "Use an empty list when there are no prerequisites."
        ),
    )


class Story(BaseModel):
    """
    A single Agile user story representing one sprint-sized unit of work.

    Stories follow the standard format:
        'As a <role>, I want <goal>, so that <benefit>.'

    Each story is fully self-contained: its acceptance criteria and
    dependencies are nested directly on the story object rather than
    collected at the StoryOutput level. This makes individual stories
    portable and independently testable.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "US-001",
                "title": "Login with email and password",
                "description": (
                    "As a registered user, I want to log in using my email "
                    "and password, so that I can access my account."
                ),
                "story_points": 5,
                "priority": "HIGH",
                "acceptance_criteria": [
                    {
                        "id": "AC-001",
                        "description": (
                            "Given a registered user, "
                            "When valid credentials are entered, "
                            "Then the user shall be authenticated successfully."
                        ),
                    },
                    {
                        "id": "AC-002",
                        "description": (
                            "Given an authenticated user, "
                            "When login succeeds, "
                            "Then the user shall be redirected to the dashboard."
                        ),
                    },
                ],
                "dependencies": [],
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this story within the StoryOutput. "
            "Format: US-NNN (zero-padded three digits), e.g. US-001, US-012. "
            "IDs are assigned sequentially starting at US-001."
        ),
    )
    title: str = Field(
        ...,
        description=(
            "Short, imperative title summarising the story in five to ten words. "
            "Used as the story card heading in sprint planning tools. "
            "Example: 'Request a password reset email'."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "Full story description in the standard Agile format: "
            "'As a <role>, I want <goal>, so that <benefit>.' "
            "The role identifies who benefits, the goal states what they need, "
            "and the benefit explains the business value delivered."
        ),
    )
    story_points: int | None = Field(
        default=None,
        description=(
            "Effort estimate expressed in story points using the Fibonacci scale "
            "(1, 2, 3, 5, 8, 13). Must be a positive integer greater than zero. "
            "Set to null only when estimation is genuinely impossible at the time "
            "of writing (e.g. a spike or research story)."
        ),
    )
    priority: Literal["HIGH", "MEDIUM", "LOW"] | None = Field(
        default=None,
        description=(
            "Business priority assigned during backlog refinement. "
            "HIGH — must be delivered in the next sprint or release. "
            "MEDIUM — important but can be deferred by one sprint. "
            "LOW — desirable but not time-sensitive. "
            "Set to null only when priority has not yet been determined."
        ),
    )
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        default_factory=list,
        description=(
            "Ordered list of acceptance criteria that define when this story "
            "is considered complete. Each criterion is written in Given/When/Then "
            "format and must be independently verifiable. Should contain at least "
            "one criterion; an empty list indicates the story is not yet refined."
        ),
    )
    dependencies: list[Dependency] = Field(
        default_factory=list,
        description=(
            "List of dependencies declaring which other stories must be completed "
            "before work on this story can begin. Use an empty list when this "
            "story has no prerequisites and can be started immediately."
        ),
    )

    @field_validator("story_points")
    @classmethod
    def story_points_must_be_positive(cls, v: int | None) -> int | None:
        """Ensure story_points is greater than zero when a value is provided."""
        if v is not None and v <= 0:
            raise ValueError("story_points must be greater than 0")
        return v


class NFR(BaseModel):
    """
    A single Non-Functional Requirement (NFR) associated with the feature.

    NFRs define the quality attributes the system must satisfy — performance
    thresholds, security standards, accessibility conformance levels, etc.
    Every NFR must be measurable and specific enough to be verified by a
    test, a monitoring alert, or a compliance audit.

    NFRs are collected at the StoryOutput level because they typically apply
    across multiple stories within the same feature.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "NFR-001",
                "category": "Performance",
                "description": (
                    "The authentication API must respond within 500 ms at the "
                    "95th percentile under a sustained load of 1,000 concurrent "
                    "requests."
                ),
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this NFR within the StoryOutput. "
            "Format: NFR-NNN (zero-padded three digits), e.g. NFR-001. "
            "IDs are assigned sequentially starting at NFR-001."
        ),
    )
    category: str = Field(
        ...,
        description=(
            "Quality attribute category this NFR belongs to. "
            "Permitted values: Performance, Security, Scalability, Reliability, "
            "Accessibility, Maintainability. "
            "Used to group NFRs by concern during architecture and review."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "Measurable, specific statement of the non-functional requirement. "
            "Must include a concrete threshold, standard reference, or verifiable "
            "criterion. Vague statements such as 'the system should be fast' are "
            "not acceptable."
        ),
    )


class StoryOutput(BaseModel):
    """
    Root output model for the /api/generate-story endpoint.

    Returned by generate_response() after the LLM response is parsed from JSON.
    Represents a complete, self-contained set of Agile artefacts for a single
    feature: the stories (each carrying their own acceptance criteria and
    dependencies), the governing business rules, and the non-functional
    requirements that apply across the feature.

    Acceptance criteria and dependencies are nested inside each Story object,
    not at this level. StoryOutput only holds artefacts that are feature-wide
    in scope: rules and NFRs.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "epic": "User Account Management",
                "feature": "User Login",
                "stories": [
                    {
                        "id": "US-001",
                        "title": "Login with email and password",
                        "description": (
                            "As a registered user, I want to log in using my "
                            "email and password, so that I can access my account."
                        ),
                        "story_points": 5,
                        "priority": "HIGH",
                        "acceptance_criteria": [
                            {
                                "id": "AC-001",
                                "description": (
                                    "Given a registered user, "
                                    "When valid credentials are entered, "
                                    "Then the user shall be authenticated successfully."
                                ),
                            }
                        ],
                        "dependencies": [],
                    }
                ],
                "rules": [
                    "Accounts are locked for 30 minutes after 5 consecutive failed login attempts."
                ],
                "nfrs": [
                    {
                        "id": "NFR-001",
                        "category": "Security",
                        "description": (
                            "Passwords must be stored using bcrypt with a minimum "
                            "cost factor of 12."
                        ),
                    }
                ],
            }
        }
    )

    epic: str = Field(
        ...,
        description=(
            "Name of the parent epic that this feature belongs to. "
            "An epic groups related features that together deliver a larger "
            "business capability. Example: 'User Account Management'."
        ),
    )
    feature: str = Field(
        ...,
        description=(
            "Name of the specific feature within the epic that these stories "
            "implement. Should be concise and match the feature name used in "
            "the product backlog. Example: 'Password Reset'."
        ),
    )
    stories: list[Story] = Field(
        default_factory=list,
        description=(
            "Ordered list of user stories that together deliver the feature. "
            "Each story is self-contained and includes its own acceptance "
            "criteria and dependencies. Stories should be ordered from "
            "foundational (no dependencies) to dependent."
        ),
    )
    rules: list[str] = Field(
        default_factory=list,
        description=(
            "Feature-wide business rules expressed as plain-English strings. "
            "These are constraints that govern the feature's behaviour across "
            "all stories — rate limits, data retention policies, role permissions, "
            "invariants. Example: 'Only one active reset link may exist per user "
            "at any time.'"
        ),
    )
    nfrs: list[NFR] = Field(
        default_factory=list,
        description=(
            "Feature-wide non-functional requirements that apply across all "
            "stories in this output. Covers quality attributes such as performance "
            "thresholds, security standards, accessibility conformance levels, "
            "and reliability targets."
        ),
    )
