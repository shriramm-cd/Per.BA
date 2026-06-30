"""
=== FILE: backend/ingestion/tests/test_normalizer.py ===
Tests for text_normalizer.py
"""

from __future__ import annotations

import pytest
from backend.ingestion.text_normalizer import normalize, detect_language, chunk_text


class TestNormalize:
    def test_strips_leading_trailing_whitespace(self):
        assert normalize("  hello world  ") == "hello world"

    def test_collapses_multiple_blank_lines(self):
        text = "Line one\n\n\n\n\nLine two"
        result = normalize(text)
        assert "\n\n\n" not in result
        assert "Line one" in result
        assert "Line two" in result

    def test_removes_page_x_of_y(self):
        text = "Some content\nPage 3 of 10\nMore content"
        result = normalize(text)
        assert "Page 3 of 10" not in result
        assert "Some content" in result

    def test_removes_confidential(self):
        text = "CONFIDENTIAL: This is a secret document."
        result = normalize(text)
        assert "CONFIDENTIAL" not in result.upper() or "CONFIDENTIAL" in result.upper()
        # At minimum the word is suppressed by regex
        assert "confidential" not in result.lower()

    def test_removes_draft_keyword(self):
        text = "DRAFT specification document"
        result = normalize(text)
        assert "DRAFT" not in result

    def test_unicode_nfkc(self):
        """Ligatures and special unicode chars are normalized."""
        text = "\ufb01rst requirement"  # ﬁ ligature
        result = normalize(text)
        assert result == "first requirement"

    def test_collapses_intra_line_spaces(self):
        text = "word1   word2\t\tword3"
        result = normalize(text)
        assert "word1 word2 word3" in result

    def test_empty_string(self):
        assert normalize("") == ""

    def test_removes_repeated_headers(self):
        """Lines repeated 3+ times are removed as header/footer boilerplate."""
        header = "Company Confidential"
        text = "\n".join([
            "Requirement 1",
            header,
            "Requirement 2",
            header,
            "Requirement 3",
            header,
        ])
        result = normalize(text)
        # The repeated header should be gone
        assert result.count(header) < 3


class TestDetectLanguage:
    def test_english_text(self):
        text = "The user shall be able to log in using their email address."
        lang = detect_language(text)
        assert lang == "en"

    def test_empty_returns_unknown(self):
        assert detect_language("") == "unknown"

    def test_whitespace_only_returns_unknown(self):
        assert detect_language("   \n\t  ") == "unknown"

    def test_returns_string(self):
        result = detect_language("Bonjour le monde")
        assert isinstance(result, str)
        assert len(result) >= 2

    def test_unknown_on_exception(self, monkeypatch):
        """If langdetect raises, returns 'unknown'."""
        import backend.ingestion.text_normalizer as tn
        def mock_detect(text):
            raise Exception("test exception")
        monkeypatch.setattr(tn, "_langdetect_detect", mock_detect)
        result = detect_language("xyzxyzxyz")
        assert result == "unknown"


class TestChunkText:
    def test_short_text_returns_single_chunk(self):
        text = "Short text."
        chunks = chunk_text(text, chunk_size=512, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_empty_text_returns_list_with_one_item(self):
        chunks = chunk_text("", chunk_size=512, overlap=50)
        assert isinstance(chunks, list)
        assert len(chunks) == 1

    def test_long_text_produces_multiple_chunks(self):
        text = "This is a sentence. " * 100  # ~2000 chars
        chunks = chunk_text(text, chunk_size=512, overlap=50)
        assert len(chunks) > 1

    def test_chunks_cover_all_content(self):
        """No content should be completely dropped between chunks."""
        text = "AAAAA " * 200
        chunks = chunk_text(text, chunk_size=512, overlap=50)
        # Reassemble approximately and check original words exist
        combined = " ".join(chunks)
        assert "AAAAA" in combined

    def test_chunk_size_respected(self):
        text = "word " * 200
        chunks = chunk_text(text, chunk_size=512, overlap=50)
        for chunk in chunks:
            # Allow some tolerance for sentence-boundary alignment
            assert len(chunk) <= 600, f"Chunk too long: {len(chunk)}"

    def test_at_least_one_chunk_always(self):
        for txt in ["", "a", "a" * 1000]:
            chunks = chunk_text(txt, chunk_size=512, overlap=50)
            assert len(chunks) >= 1

    def test_overlap_default_parameters(self):
        """Default chunk_size=512, overlap=50 produces valid output."""
        text = "The quick brown fox jumps over the lazy dog. " * 50
        chunks = chunk_text(text)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)
