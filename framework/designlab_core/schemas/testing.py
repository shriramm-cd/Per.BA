"""
designlab_core.schemas.testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic models for Unit Test suite generation output.


Status: FINALISED
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TestCase(BaseModel):
    """
    A single, independently runnable unit test case scenario.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "TC-001",
                "category": "positive",
                "scenario": "Login succeeds with valid email and password",
                "preconditions": [
                    "A user account exists with email 'user@example.com' and password 'Correct$1' stored as a valid bcrypt hash"
                ],
                "steps": [
                    "Call POST /api/v1/auth/login with body { email: 'user@example.com', password: 'Correct$1' }"
                ],
                "expected_result": "Response status is 200 and valid tokens are returned."
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this test case. "
            "Format: TC-NNN (zero-padded three digits), e.g. TC-001, TC-012. "
            "Sequential starting at TC-001."
        ),
    )
    category: Literal["positive", "negative", "boundary", "edge"] = Field(
        ...,
        description=(
            "The category of the test case scenario: "
            "positive (happy-path), negative (error validation), boundary (limit/threshold), or edge (unusual inputs/state)."
        ),
    )
    scenario: str = Field(
        ...,
        description="A short, imperative sentence naming what is being tested. Must be unique.",
    )
    preconditions: list[str] = Field(
        default_factory=list,
        description="List of system states, database entries, or fixtures required before the test executes.",
    )
    steps: list[str] = Field(
        default_factory=list,
        description="Ordered list of discrete inputs, actions, or function/endpoint calls performed during the test.",
    )
    expected_result: str = Field(
        ...,
        description="A clear description of the expected assertions, outputs, and side effects of the test.",
    )


class TestOutput(BaseModel):
    """
    Root output model for unit test suite generation.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feature": "User Login",
                "test_cases": []
            }
        }
    )

    feature: str = Field(
        ...,
        description="Name of the feature under test (e.g. 'User Login').",
    )
    test_cases: list[TestCase] = Field(
        default_factory=list,
        description="List of test cases compiled for the given feature.",
    )
