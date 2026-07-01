import os

import pytest

from backend.config import Settings
from backend.shared.llm_client import LLMClient


def test_gemini_key_resolution_prefers_google_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_PRIMARY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_FALLBACK", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    settings = Settings(_env_file=None)
    client = LLMClient.__new__(LLMClient)
    client.groq_primary_key = settings.GROQ_API_KEY_PRIMARY or settings.GROQ_API_KEY
    client.groq_fallback_key = settings.GROQ_API_KEY_FALLBACK
    client.gemini_primary_key = settings.GEMINI_API_KEY_PRIMARY or settings.GEMINI_API_KEY or getattr(settings, "GOOGLE_API_KEY", None)
    client.gemini_fallback_key = settings.GEMINI_API_KEY_FALLBACK or getattr(settings, "GOOGLE_API_KEY_FALLBACK", None)

    assert client.gemini_primary_key == "test-google-key"
