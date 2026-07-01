from backend.shared.llm_client import LLMClient


def test_extract_json_candidate_from_wrapped_text() -> None:
    client = LLMClient.__new__(LLMClient)
    wrapped_payload = 'Here is the response:\n```json\n{"epics": [], "features": []}\n```\n'

    parsed = client._extract_json_candidate(wrapped_payload)

    assert parsed == '{"epics": [], "features": []}'
