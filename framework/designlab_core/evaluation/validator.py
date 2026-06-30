from dataclasses import dataclass
from typing import Any
import json

from pydantic import ValidationError


@dataclass
class ValidationResult:
    is_valid: bool
    parsed: Any | None
    errors: list[str]
    schema_name: str


def validate_output(
    raw_json: str,
    schema_class: type,
) -> ValidationResult:
    """
    Validate LLM JSON output against a Pydantic schema.
    """

    errors: list[str] = []

    # Step 1: Parse JSON
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return ValidationResult(
            is_valid=False,
            parsed=None,
            errors=[f"Invalid JSON: {e}"],
            schema_name=schema_class.__name__,
        )

    # Step 2: Validate schema
    try:
        parsed = schema_class.model_validate(payload)
    except ValidationError as e:
        return ValidationResult(
            is_valid=False,
            parsed=None,
            errors=[str(err["msg"]) for err in e.errors()],
            schema_name=schema_class.__name__,
        )

    # Step 3: Check empty fields
    for field_name, value in parsed.model_dump().items():
        if value in ("", None, [], {}):
            errors.append(
                f"Field '{field_name}' cannot be empty."
            )

    if errors:
        return ValidationResult(
            is_valid=False,
            parsed=None,
            errors=errors,
            schema_name=schema_class.__name__,
        )

    return ValidationResult(
        is_valid=True,
        parsed=parsed,
        errors=[],
        schema_name=schema_class.__name__,
    )