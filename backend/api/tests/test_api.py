import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check_endpoint():
    """
    Tests that the open health check endpoint returns 200.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK", "version": "1.0.0"}

def test_protected_routes_unauthorized():
    """
    Ensures secure endpoints reject requests without api key headers.
    """
    response = client.get("/audit/logs")
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]

# INTEGRATION NOTE
# Set test configuration X-API-KEY during automated CI runs.
