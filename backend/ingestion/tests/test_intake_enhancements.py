import os
import pytest
from pathlib import Path
from backend.ingestion.docling_loader import load_from_file
from backend.ingestion.summary_generator import InputSummaryGenerator

@pytest.mark.asyncio
async def test_extract_text_from_email(tmp_path):
    """
    Verifies that plain text is correctly extracted from a .eml email file.
    """
    eml_file = tmp_path / "test_email.eml"
    eml_content = (
        "Subject: Urgent Leave Policy Update\n"
        "From: hr@enterprise.com\n"
        "To: all@enterprise.com\n\n"
        "Please implement the new leave request approval workflow. "
        "All requests must be approved by a manager within 24 hours."
    )
    eml_file.write_text(eml_content, encoding="utf-8")

    result = await load_from_file(str(eml_file))
    assert "text" in result
    assert "Urgent Leave Policy Update" in result["text"]
    assert "hr@enterprise.com" in result["text"]
    assert result["metadata"]["extraction_method"] == "email_parser"


@pytest.mark.asyncio
async def test_extract_text_from_csv(tmp_path):
    """
    Verifies that text is correctly extracted from a .csv file and formatted as rows.
    """
    csv_file = tmp_path / "test_reqs.csv"
    csv_content = (
        "ReqID,Content,Actor\n"
        "REQ-001,Submit leave request,Employee\n"
        "REQ-002,Approve leave request,Manager"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    result = await load_from_file(str(csv_file))
    assert "text" in result
    assert "REQ-001 | Submit leave request | Employee" in result["text"]
    assert "REQ-002 | Approve leave request | Manager" in result["text"]
    assert result["metadata"]["extraction_method"] == "csv_parser"


@pytest.mark.asyncio
async def test_extract_text_from_audio_fallback(tmp_path):
    """
    Verifies that the audio extractor gracefully falls back to mock text when no Groq key is present.
    """
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"RIFFmockwavheaderanddatacontent")

    result = await load_from_file(str(audio_file))
    assert "text" in result
    assert "Mock Audio Transcription" in result["text"]
    assert result["metadata"]["extraction_method"] == "whisper_audio"


@pytest.mark.asyncio
async def test_extract_text_from_image_fallback(tmp_path):
    """
    Verifies that the image extractor gracefully falls back to mock text when no Groq key is present.
    """
    image_file = tmp_path / "screenshot.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\nmockpngheader")

    result = await load_from_file(str(image_file))
    assert "text" in result
    assert "Mock OCR Extraction" in result["text"]
    assert result["metadata"]["extraction_method"] == "vision_ocr"


@pytest.mark.asyncio
async def test_input_summary_generation():
    """
    Verifies that the InputSummaryGenerator produces a valid structured summary.
    """
    raw_text = (
        "Employee Leave Management System BRD.\n"
        "The objective is to automate leave requests.\n"
        "Employees can submit requests, and Managers can approve them.\n"
        "System must be secure and send email notifications."
    )
    
    generator = InputSummaryGenerator()
    summary = await generator.generate_summary(raw_text)
    
    assert "business_objective" in summary
    assert "functional_requirements" in summary
    assert "non_functional_requirements" in summary
    assert "business_rules" in summary
    assert "actors" in summary
    assert "systems" in summary
    assert "detected_domain" in summary
    assert "summary" in summary
