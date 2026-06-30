"""
designlab_core.schemas.backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic models for Backend endpoint specifications generation output.


Status: FINALISED
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SchemaField(BaseModel):  # type: ignore
    """
    Metadata describing a field inside a request or response JSON schema.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "str",
                "description": "The user's registered email address used as the login identifier"
            }
        }
    )

    type: str = Field(
        ...,
        description=(
            "The data type of the field using Python/Pydantic notation. "
            "Examples: 'str', 'int', 'bool', 'UUID', 'datetime', 'list[str]', 'str | None'."
        ),
    )
    description: str = Field(
        ...,
        description="A clear description of the field's purpose, format requirements, and business significance.",
    )


class ErrorResponse(BaseModel):  # type: ignore
    """
    An expected error response structure that an endpoint can return.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status_code": 401,
                "error_code": "INVALID_CREDENTIALS",
                "description": "Returned when the email is not registered or the password does not match."
            }
        }
    )

    status_code: int = Field(
        ...,
        description="The HTTP status code returned for this error scenario (e.g. 400, 401, 403, 429, 500).",
    )
    error_code: str = Field(
        ...,
        description="A machine-readable SCREAMING_SNAKE_CASE string identifying the specific error type.",
    )
    description: str = Field(
        ...,
        description="A plain-English explanation of exactly when this error code is returned to the client.",
    )


class Endpoint(BaseModel):  # type: ignore
    """
    Represents a single backend REST API endpoint specification.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "EP-001",
                "path": "/api/v1/auth/login",
                "method": "POST",
                "description": "Authenticates a user and returns tokens.",
                "request_schema": {
                    "email": {
                        "type": "str",
                        "description": "User's email address"
                    }
                },
                "response_schema": {
                    "access_token": {
                        "type": "str",
                        "description": "JWT access token"
                    }
                },
                "validation_rules": [
                    "email must be a valid RFC 5321 email address"
                ],
                "error_responses": [
                    {
                        "status_code": 401,
                        "error_code": "INVALID_CREDENTIALS",
                        "description": "Wrong password or unregistered email"
                    }
                ]
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this endpoint. "
            "Format: EP-NNN (zero-padded three digits), e.g. EP-001, EP-002. "
            "Sequential starting at EP-001."
        ),
    )
    path: str = Field(
        ...,
        description=(
            "The URL path segment starting with a slash, e.g. '/api/v1/auth/login' "
            "or '/api/v1/users/{user_id}'."
        ),
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        ...,
        description="The HTTP method required to access the endpoint.",
    )
    description: str = Field(
        ...,
        description="A concise summary of what this endpoint does and what it returns.",
    )
    request_schema: dict[str, SchemaField] | None = Field(
        default=None,
        description=(
            "An object mapping request field names to their type and description metadata. "
            "Set to null for GET and DELETE endpoints that carry no request body."
        ),
    )
    response_schema: dict[str, SchemaField] = Field(
        ...,
        description="An object mapping success response field names to their type and description metadata.",
    )
    validation_rules: list[str] = Field(
        default_factory=list,
        description="List of validation rules, parameter constraints, and business logic conditions enforced.",
    )
    error_responses: list[ErrorResponse] = Field(
        default_factory=list,
        description="List of potential error responses the endpoint can return on failure.",
    )


class BackendOutput(BaseModel):  # type: ignore
    """
    Root output model for backend REST API specifications generation.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feature": "User Login",
                "endpoints": []
            }
        }
    )

    feature: str = Field(
        ...,
        description="Name of the feature these endpoints implement (e.g. 'User Login').",
    )
    endpoints: list[Endpoint] = Field(
        default_factory=list,
        description="List of endpoints required to implement the given feature.",
    )
