import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.mark.anyio
async def test_get_job_history_not_found():
    response = client.get("/api/v1/validation/jobs/nonexistent-job-id/history")
    # Should return empty versions list or 200 with empty list
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "nonexistent-job-id"
    assert len(data["versions"]) == 0

@pytest.mark.anyio
async def test_get_job_version_not_found():
    response = client.get("/api/v1/validation/jobs/nonexistent-job-id/version/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["requirements"]) == 0
    assert len(data["stories"]) == 0
    assert data["validation"] is None
