"""
designlab_core.llm.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Custom exceptions for the LLM layer.

Accelerators should catch these — never catch provider-specific exceptions directly.


"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for all LLM-related errors."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LLMTimeoutError(LLMError):
    """
    Raised when the LLM call exceeds the configured timeout.
    """
    def __init__(
        self,
        message: str,
        *,
        timeout: float | None = None,
        provider: str | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.timeout = timeout
        self.provider = provider
        self.model_name = model_name


class LLMProviderError(LLMError):
    """
    Raised for non-retryable provider errors.
    Examples: invalid API key (401), malformed request (400).
    """
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        provider: str | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider
        self.model_name = model_name


class LLMRetryExhausted(LLMError):
    """
    Raised when all retry attempts are exhausted without a successful response.
    Examples: repeated 429 rate limits, repeated 500 server errors.
    """
    def __init__(
        self,
        message: str,
        *,
        max_retries: int | None = None,
        provider: str | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.max_retries = max_retries
        self.provider = provider
        self.model_name = model_name
