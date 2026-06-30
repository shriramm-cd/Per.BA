import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import openai

from designlab_core.llm.client import (
    _detect_provider,
    _is_retryable,
    generate_response,
    LLMResponse,
)
from designlab_core.llm.exceptions import (
    LLMProviderError,
    LLMRetryExhausted,
    LLMTimeoutError,
)
from designlab_core.utilities.env import DesignLabEnv


def test_detect_provider():
    # Test Anthropic models
    assert _detect_provider("claude-3-5-sonnet-20241022") == "anthropic"
    assert _detect_provider("claude-3-haiku-20240307") == "anthropic"

    # Test OpenAI models
    assert _detect_provider("gpt-4o") == "openai"
    assert _detect_provider("gpt-4o-mini") == "openai"
    assert _detect_provider("o1-preview") == "openai"
    assert _detect_provider("o3-mini") == "openai"

    # Test unsupported provider
    with pytest.raises(LLMProviderError) as exc_info:
        _detect_provider("unsupported-model-id")
    assert "Cannot determine provider for model" in str(exc_info.value)


def test_is_retryable():
    # Anthropic retryable
    assert _is_retryable(anthropic.RateLimitError(message="rate limit", response=MagicMock(), body=None)) is True
    assert _is_retryable(anthropic.InternalServerError(message="internal error", response=MagicMock(), body=None)) is True
    assert _is_retryable(anthropic.APIConnectionError(message="conn error", request=MagicMock())) is True

    # Anthropic non-retryable
    assert _is_retryable(anthropic.AuthenticationError(message="auth error", response=MagicMock(), body=None)) is False
    assert _is_retryable(anthropic.BadRequestError(message="bad request", response=MagicMock(), body=None)) is False

    # OpenAI retryable
    assert _is_retryable(openai.RateLimitError(message="rate limit", response=MagicMock(), body=None)) is True
    assert _is_retryable(openai.InternalServerError(message="internal error", response=MagicMock(), body=None)) is True
    assert _is_retryable(openai.APIConnectionError(message="conn error", request=MagicMock())) is True

    # OpenAI non-retryable
    assert _is_retryable(openai.AuthenticationError(message="auth error", response=MagicMock(), body=None)) is False
    assert _is_retryable(openai.BadRequestError(message="bad request", response=MagicMock(), body=None)) is False

    # Generic exception
    assert _is_retryable(ValueError("generic error")) is False


@pytest.mark.asyncio
@patch("designlab_core.llm.client.anthropic.AsyncAnthropic")
@patch("designlab_core.llm.client.get_env")
async def test_generate_response_anthropic_success(mock_get_env, mock_async_anthropic):
    # Mock environment to return a test API key
    mock_env = MagicMock(spec=DesignLabEnv)
    mock_env.get_llm_key.return_value = "test-anthropic-key"
    mock_env.llm_timeout_seconds = 10
    mock_env.llm_max_retries = 3
    mock_env.llm_max_tokens = 4096
    mock_env.llm_retry_max_multiplier = 8
    mock_get_env.return_value = mock_env

    # Mock Anthropic client and response
    mock_client = MagicMock()
    mock_async_anthropic.return_value = mock_client

    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Hello from Claude!"

    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 20

    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_response.model = "claude-3-5-sonnet-20241022"
    mock_response.usage = mock_usage
    mock_response.stop_reason = "end_turn"

    mock_client.messages.create = AsyncMock(return_value=mock_response)

    # Call generate_response
    response = await generate_response(
        prompt="Hi Claude",
        model_name="claude-sonnet",
        system_prompt="You are a helpful assistant",
    )

    # Verify result
    assert isinstance(response, LLMResponse)
    assert response.content == "Hello from Claude!"
    assert response.model_used == "claude-3-5-sonnet-20241022"
    assert response.tokens_used == 30
    assert response.metadata["provider"] == "anthropic"

    # Verify mock calls
    mock_async_anthropic.assert_called_once_with(api_key="test-anthropic-key")
    mock_client.messages.create.assert_called_once_with(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{"role": "user", "content": "Hi Claude"}],
        system="You are a helpful assistant",
    )


@pytest.mark.asyncio
@patch("designlab_core.llm.client.openai.AsyncOpenAI")
@patch("designlab_core.llm.client.get_env")
async def test_generate_response_openai_success(mock_get_env, mock_async_openai):
    # Mock environment to return a test API key
    mock_env = MagicMock(spec=DesignLabEnv)
    mock_env.get_llm_key.return_value = "test-openai-key"
    mock_env.llm_timeout_seconds = 10
    mock_env.llm_max_retries = 3
    mock_env.llm_max_tokens = 2048
    mock_env.llm_retry_max_multiplier = 8
    mock_get_env.return_value = mock_env

    # Mock OpenAI client and response
    mock_client = MagicMock()
    mock_async_openai.return_value = mock_client

    mock_choice = MagicMock()
    mock_choice.message.content = "Hello from GPT!"
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.total_tokens = 45
    mock_usage.prompt_tokens = 15
    mock_usage.completion_tokens = 30

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o"
    mock_response.usage = mock_usage

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Call generate_response
    response = await generate_response(
        prompt="Hi GPT",
        model_name="gpt-4o",
        max_tokens=100,
    )

    # Verify result
    assert isinstance(response, LLMResponse)
    assert response.content == "Hello from GPT!"
    assert response.model_used == "gpt-4o"
    assert response.tokens_used == 45
    assert response.metadata["provider"] == "openai"

    # Verify mock calls
    mock_async_openai.assert_called_once_with(api_key="test-openai-key")
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hi GPT"}],
        max_tokens=100,
    )


@pytest.mark.asyncio
@patch("designlab_core.llm.client.anthropic.AsyncAnthropic")
@patch("designlab_core.llm.client.get_env")
async def test_generate_response_timeout(mock_get_env, mock_async_anthropic):
    # Mock environment to return a test API key and a very short timeout
    mock_env = MagicMock(spec=DesignLabEnv)
    mock_env.get_llm_key.return_value = "test-anthropic-key"
    mock_env.llm_timeout_seconds = 0.01  # extremely short timeout
    mock_env.llm_max_retries = 1
    mock_env.llm_max_tokens = 100
    mock_env.llm_retry_max_multiplier = 1
    mock_get_env.return_value = mock_env

    # Mock Anthropic client to sleep longer than the timeout
    mock_client = MagicMock()
    mock_async_anthropic.return_value = mock_client

    async def slow_call(*args, **kwargs):
        await asyncio.sleep(0.5)
        return MagicMock()

    mock_client.messages.create = AsyncMock(side_effect=slow_call)

    # Call generate_response and expect LLMTimeoutError
    with pytest.raises(LLMTimeoutError) as exc_info:
        await generate_response(
            prompt="Hi Claude",
            model_name="claude-sonnet",
        )
    assert "timed out after" in str(exc_info.value)


@pytest.mark.asyncio
@patch("designlab_core.llm.client.anthropic.AsyncAnthropic")
@patch("designlab_core.llm.client.get_env")
async def test_generate_response_retry_exhausted(mock_get_env, mock_async_anthropic):
    # Mock environment to return a test API key
    mock_env = MagicMock(spec=DesignLabEnv)
    mock_env.get_llm_key.return_value = "test-anthropic-key"
    mock_env.llm_timeout_seconds = 10
    mock_env.llm_max_retries = 2  # 2 attempts total
    mock_env.llm_max_tokens = 100
    mock_env.llm_retry_max_multiplier = 1
    mock_get_env.return_value = mock_env

    # Mock Anthropic client to raise a retryable error
    mock_client = MagicMock()
    mock_async_anthropic.return_value = mock_client

    # Create a dummy response for the exception
    mock_response = MagicMock()
    rate_limit_error = anthropic.RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body=None
    )
    mock_client.messages.create = AsyncMock(side_effect=rate_limit_error)

    # Call generate_response and expect LLMRetryExhausted
    with pytest.raises(LLMRetryExhausted) as exc_info:
        await generate_response(
            prompt="Hi Claude",
            model_name="claude-sonnet",
        )
    assert "retry attempts exhausted" in str(exc_info.value)
    # Ensure it was called 2 times
    assert mock_client.messages.create.call_count == 2


@pytest.mark.asyncio
@patch("designlab_core.llm.client.anthropic.AsyncAnthropic")
@patch("designlab_core.llm.client.get_env")
async def test_generate_response_non_retryable_error(mock_get_env, mock_async_anthropic):
    # Mock environment to return a test API key
    mock_env = MagicMock(spec=DesignLabEnv)
    mock_env.get_llm_key.return_value = "test-anthropic-key"
    mock_env.llm_timeout_seconds = 10
    mock_env.llm_max_retries = 3
    mock_env.llm_max_tokens = 100
    mock_env.llm_retry_max_multiplier = 1
    mock_get_env.return_value = mock_env

    # Mock Anthropic client to raise a non-retryable error (AuthenticationError)
    mock_client = MagicMock()
    mock_async_anthropic.return_value = mock_client

    mock_response = MagicMock()
    auth_error = anthropic.AuthenticationError(
        message="Invalid API Key",
        response=mock_response,
        body=None
    )
    mock_client.messages.create = AsyncMock(side_effect=auth_error)

    # Call generate_response and expect LLMProviderError
    with pytest.raises(LLMProviderError) as exc_info:
        await generate_response(
            prompt="Hi Claude",
            model_name="claude-sonnet",
        )
    assert "Authentication failed for provider" in str(exc_info.value)
    # Ensure it was called only once (no retries for auth error)
    assert mock_client.messages.create.call_count == 1
