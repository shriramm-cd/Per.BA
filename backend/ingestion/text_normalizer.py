"""
=== FILE: backend/ingestion/text_normalizer.py ===

Text normalization, language detection, and chunking utilities.
Implements spec requirements:
  - Unicode NFKC normalization
  - Boilerplate removal (Page X of Y, DRAFT, Confidential, repeated headers/footers)
  - langdetect-based language detection (fallback: "unknown")
  - Sentence-aware chunking (512 chars, 50 char overlap)
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from designlab_core.utilities.logger import get_logger, log_warning

logger = get_logger("ingestion.text_normalizer")

# ── langdetect (optional dependency guard) ────────────────────────────────────
try:
    from langdetect import detect as _langdetect_detect
    from langdetect import DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException

    DetectorFactory.seed = 42          # reproducible results
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    log_warning("langdetect not installed — language detection will return 'unknown'.")


# ── Boilerplate patterns ───────────────────────────────────────────────────────

_BOILERPLATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bpage\s+\d+\s+of\s+\d+\b"),          # Page X of Y
    re.compile(r"(?i)\bconfidential\b"),                     # Confidential
    re.compile(r"(?i)\bdraft\b"),                            # DRAFT
    re.compile(r"(?i)^[-─═_*]{3,}\s*$", re.MULTILINE),      # Horizontal rules
    re.compile(r"\f"),                                        # Form feeds (page breaks)
]

# Detect repeated short lines (headers / footers repeated ≥ 3 times)
_MIN_HEADER_REPEATS = 3
_MAX_HEADER_LEN = 120


def _remove_repeated_header_footer(text: str) -> str:
    """Remove lines that appear ≥ 3 times and are ≤ 120 characters (header/footer heuristic)."""
    lines = text.split("\n")
    from collections import Counter
    line_counts: Counter[str] = Counter(
        line.strip() for line in lines if line.strip() and len(line.strip()) <= _MAX_HEADER_LEN
    )
    repeated = {line for line, count in line_counts.items() if count >= _MIN_HEADER_REPEATS}
    if repeated:
        logger.debug(f"Removing {len(repeated)} repeated header/footer pattern(s).")
    filtered = [line for line in lines if line.strip() not in repeated]
    return "\n".join(filtered)


# ── Public functions ───────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """
    Full normalization pipeline:
      1. Unicode NFKC normalization
      2. Boilerplate pattern removal
      3. Repeated header/footer removal
      4. Collapse consecutive blank lines to a single blank line
      5. Strip leading/trailing whitespace
      6. Collapse intra-line multi-spaces/tabs to a single space

    Args:
        text: Raw extracted text.

    Returns:
        Cleaned, normalized text.
    """
    if not text:
        return ""

    # 1. Unicode NFKC — converts ligatures, non-breaking spaces, etc.
    text = unicodedata.normalize("NFKC", text)

    # 2. Boilerplate removal
    for pattern in _BOILERPLATE_PATTERNS:
        text = pattern.sub(" ", text)

    # 3. Repeated headers/footers
    text = _remove_repeated_header_footer(text)

    # 4. Collapse consecutive blank lines (3+ → 1 blank line)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Collapse intra-line whitespace (tabs + multiple spaces → single space)
    text = re.sub(r"[ \t]+", " ", text)

    # 6. Strip each line individually
    text = "\n".join(line.strip() for line in text.split("\n"))

    return text.strip()


def detect_language(text: str) -> str:
    """
    Detect the language of the given text using langdetect.
    Returns an ISO 639-1 code (e.g. "en", "fr") or "unknown" on failure.

    Args:
        text: Normalized text sample.

    Returns:
        Language code string.
    """
    if not _LANGDETECT_AVAILABLE:
        return "unknown"

    sample = text[:5000] if len(text) > 5000 else text
    if not sample.strip():
        return "unknown"

    try:
        lang = _langdetect_detect(sample)
        logger.debug(f"Language detected: {lang}")
        return lang
    except LangDetectException as exc:
        log_warning(f"Language detection failed: {exc}")
        return "unknown"
    except Exception as exc:
        log_warning(f"Unexpected error in language detection: {exc}")
        return "unknown"


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping chunks of approximately `chunk_size` characters.

    Strategy:
      - If text ≤ chunk_size, return [text] directly.
      - Prefer to break at sentence boundaries (". "), then paragraph boundaries ("\\n\\n"),
        then line boundaries ("\\n"), then word boundaries (" ").
      - Overlap of `overlap` characters is preserved between consecutive chunks.

    Args:
        text:       Normalized input text.
        chunk_size: Target maximum characters per chunk (default 512).
        overlap:    Number of characters to re-include at the start of the next chunk (default 50).

    Returns:
        List of non-empty text chunks. Guaranteed to contain at least one item.
    """
    if not text:
        return [""]

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        if end == text_len:
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            break

        # ── Find best split boundary ──────────────────────────────────────────
        # Search backward from `end` within a window to find a clean boundary.
        search_start = max(start, end - overlap - 1)

        # 1. Sentence end: ". " or ".\n"
        boundary = _rfind_any(text, [". ", ".\n", "? ", "! "], search_start, end)

        # 2. Paragraph break
        if boundary == -1:
            boundary = text.rfind("\n\n", search_start, end)

        # 3. Line break
        if boundary == -1:
            boundary = text.rfind("\n", search_start, end)

        # 4. Word space
        if boundary == -1:
            boundary = text.rfind(" ", search_start, end)

        if boundary != -1 and boundary > start:
            chunk_end = boundary + 1  # include the separator character
        else:
            chunk_end = end           # hard cut

        chunk = text[start:chunk_end].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward with overlap
        start = max(chunk_end - overlap, chunk_end)

    # Safety: always return at least one chunk
    if not chunks:
        chunks = [text.strip()]

    logger.debug(f"chunk_text produced {len(chunks)} chunks from {text_len} chars.")
    return chunks


class TextNormalizer:
    """Compatibility wrapper for the text normalizer API."""

    clean = staticmethod(normalize)
    detect_language = staticmethod(detect_language)
    chunk_text = staticmethod(chunk_text)


# ── Private helper ─────────────────────────────────────────────────────────────

def _rfind_any(text: str, needles: list[str], start: int, end: int) -> int:
    """
    Find the rightmost occurrence of any needle within text[start:end].
    Returns the starting index of the match, or -1 if none found.
    """
    best = -1
    for needle in needles:
        pos = text.rfind(needle, start, end)
        if pos > best:
            best = pos
    return best


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : normalize()       → clean str   consumed by run_ingestion()
#            detect_language() → lang str     stored in IngestionOutput.language
#            chunk_text()      → list[str]    stored in IngestionOutput.chunks
# Consumed : ingestion/__init__.py  run_ingestion()
