"""
conftest.py — pytest configuration for the ingestion module test suite.

Adds the repo root and backend root to sys.path so that
`from ingestion.xxx import ...` and `from shared.xxx import ...`
resolve correctly without needing an editable install.
"""

import sys
import os
from pathlib import Path

# ── Resolve paths ──────────────────────────────────────────────────────────────
# This file lives at: backend/ingestion/tests/conftest.py
_tests_dir   = Path(__file__).resolve().parent          # backend/ingestion/tests
_ingestion   = _tests_dir.parent                         # backend/ingestion
_backend     = _ingestion.parent                         # backend/
_repo_root   = _backend.parent                           # repo root
_framework   = _repo_root / "framework"                  # framework/

# ── Add to sys.path ────────────────────────────────────────────────────────────
for p in (_backend, _repo_root, _framework):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

# ── Optional: load .env for tests ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv

    env_file = _repo_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
except ImportError:
    pass  # python-dotenv not required for unit tests

import pytest

@pytest.fixture(autouse=False)
def clear_env_cache():
    """
    Clear the get_env() lru_cache between tests that modify environment variables.
    Usage: include `clear_env_cache` in your test signature.
    """
    try:
        from designlab_core.utilities.env import get_env
        get_env.cache_clear()
    except Exception:
        pass
    yield
    try:
        from designlab_core.utilities.env import get_env
        get_env.cache_clear()
    except Exception:
        pass
