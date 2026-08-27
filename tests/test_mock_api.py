"""
tests/test_mock_api.py

Tests for the Mock API (FastAPI).
Runs fully locally. Kafka consumer is mocked - no Docker required.
Uses FastAPI TestClient.
"""
import pytest
from starlette.testclient import TestClient
from unittest.mock import patch, MagicMock
from fastapi import Depends

# Mock KafkaConsumer before importing app
with patch('kafka.KafkaConsumer', MagicMock()):
    from mock_api.app import app, event_buffer, buffer_lock
    from mock_api.auth import get_config

def override_get_config():
    return {"api": {"token": "test-token"}}

app.dependency_overrides[get_config] = override_get_config

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_buffer():
    with buffer_lock:
        event_buffer.clear()
    yield

def get_valid_event(i):
    return {
        "event_id": f"event_{i}",
        "property_id": "PROP_001",
        "property_name": "Channel Alpha",
        "geography_id": "GEO_001",
        "geography_name": "North Region",
        "platform": "web",
        "category": "news",
        "event_date": "2023-10-01",
        "audience_value": 250000,
        "ingested_at": "2023-10-01T12:00:00Z"
    }

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_events_requires_auth():
    response = client.get("/events")
    assert response.status_code == 401

def test_events_wrong_token():
    response = client.get("/events", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401

def test_events_valid_auth_empty_buffer():
    response = client.get("/events", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json()["events"] == []

def test_events_pagination_first_page():
    with buffer_lock:
        for i in range(250):
            event_buffer.append(get_valid_event(i))
            
    response = client.get("/events?page=1&page_size=100", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 100
    assert data["has_next"] is True

def test_events_last_page():
    with buffer_lock:
        for i in range(250):
            event_buffer.append(get_valid_event(i))
            
    response = client.get("/events?page=3&page_size=100", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 50
    assert data["has_next"] is False

def test_events_count():
    with buffer_lock:
        for i in range(42):
            event_buffer.append(get_valid_event(i))
            
    response = client.get("/events/count", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json()["total"] == 42

def test_event_schema_valid():
    with buffer_lock:
        event_buffer.append(get_valid_event(1))
        
    response = client.get("/events", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    # Will raise error if invalid due to response_model in app
    assert len(response.json()["events"]) == 1
