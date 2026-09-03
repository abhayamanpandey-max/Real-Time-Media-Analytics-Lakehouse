"""
tests/test_supervisor.py

Integration tests for the Supervisor FastAPI application endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from supervisor.app import app

client = TestClient(app)


def test_health_endpoint():
    """Verifies public GET /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "supervisor"}


def test_index_endpoint():
    """Verifies GET / index single-page HTML endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "TENETIC" in response.text


@patch("supervisor.app.DATABRICKS_HOST", "dbc-test.cloud.databricks.com")
@patch("supervisor.app.DATABRICKS_TOKEN", "test_token")
@patch("supervisor.app.GENIE_SPACE_IDS", {"audience_reach": "space_123"})
@patch("supervisor.app.ask_genie", new_callable=AsyncMock)
def test_ask_endpoint_success(mock_ask_genie):
    """Verifies successful question routing and Genie MCP response returning domain and answer."""
    mock_ask_genie.return_value = "Property Alpha had the highest total audience last month."

    payload = {"question": "Which property had the highest total audience last month?"}

    response = client.post("/ask", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["domain"] == "audience_reach"
    assert data["answer"] == "Property Alpha had the highest total audience last month."

    mock_ask_genie.assert_called_once_with(
        space_id="space_123",
        question="Which property had the highest total audience last month?",
        host="dbc-test.cloud.databricks.com",
        token="test_token",
    )
