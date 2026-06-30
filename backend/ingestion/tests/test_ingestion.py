import pytest
from backend.ingestion.text_normalizer import TextNormalizer
from backend.ingestion.fingerprint import Fingerprint
from backend.ingestion.schemas import IngestionOutput

def test_text_normalization_whitespace():
    """
    Tests that double spacing and excessive line break gaps are removed.
    """
    raw = "Requirement  A  \n\n\n\n  Detail content."
    cleaned = TextNormalizer.clean(raw)
    assert cleaned == "Requirement A\n\nDetail content."

def test_language_detection():
    """
    Verifies that the heuristic language detector identifies English content.
    """
    english_text = "The user shall be able to log in to the business system using an email address."
    lang = TextNormalizer.detect_language(english_text)
    assert lang == "en"

def test_fingerprint_generation():
    """
    Asserts that SHA256 returns consistent 64 character hex strings.
    """
    text = "Unified functional requirement body."
    hash1 = Fingerprint.calculate(text)
    hash2 = Fingerprint.calculate(text)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_ingestion_output_keeps_raw_text():
    """Ingestion output should preserve the original raw text for downstream reuse."""
    output = IngestionOutput(
        confidence_score=1.0,
        raw_context="raw context",
        text="clean text",
        chunks=["clean text"],
        metadata={},
        fingerprint="abc123",
        language="en",
        source_type="txt",
        chunk_count=1,
        char_count=10,
        extraction_method="docling",
        raw_text="original raw text",
    )

    assert output.raw_text == "original raw text"

# INTEGRATION NOTE
# Run test suite using: pytest backend/ingestion/tests/
