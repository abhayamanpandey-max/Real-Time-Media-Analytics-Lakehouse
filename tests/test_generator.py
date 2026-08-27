"""
tests/test_generator.py

Tests for the synthetic event generator and Pydantic schemas.
Runs fully locally - no Kafka or Databricks required.
Kafka producer is mocked via pytest-mock.
"""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
import uuid

from generator.schemas import AudienceEvent, AudienceEventPage, ALLOWED_PLATFORMS, ALLOWED_CATEGORIES
from generator.synthetic_event_producer import produce_event

def get_valid_event_data():
    return {
        "event_id": str(uuid.uuid4()),
        "property_id": "PROP_001",
        "property_name": "Channel Alpha",
        "geography_id": "GEO_001",
        "geography_name": "North Region",
        "platform": "web",
        "category": "news",
        "event_date": "2023-10-01",
        "audience_value": 250000,
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }

def test_audience_event_schema_valid():
    data = get_valid_event_data()
    event = AudienceEvent(**data)
    assert event.platform == "web"

def test_audience_event_invalid_platform():
    data = get_valid_event_data()
    data["platform"] = "invalid_platform"
    with pytest.raises(ValidationError):
        AudienceEvent(**data)

def test_audience_event_invalid_category():
    data = get_valid_event_data()
    data["category"] = "invalid_category"
    with pytest.raises(ValidationError):
        AudienceEvent(**data)

def test_audience_event_negative_audience_value():
    data = get_valid_event_data()
    data["audience_value"] = -5
    with pytest.raises(ValidationError):
        AudienceEvent(**data)

def test_audience_event_invalid_date():
    data = get_valid_event_data()
    data["event_date"] = "10-01-2023"
    with pytest.raises(ValidationError):
        AudienceEvent(**data)

def test_platform_normalisation():
    data = get_valid_event_data()
    data["platform"] = " WEB "
    event = AudienceEvent(**data)
    assert event.platform == "web"

def test_category_normalisation():
    data = get_valid_event_data()
    data["category"] = " NEWS "
    event = AudienceEvent(**data)
    assert event.category == "news"

def test_audience_event_page_schema():
    data = get_valid_event_data()
    page = AudienceEventPage(
        page=1,
        page_size=10,
        total_events=1,
        has_next=False,
        events=[AudienceEvent(**data)]
    )
    assert page.page == 1

def test_producer_publishes_to_kafka(mocker):
    producer = mocker.MagicMock()
    topic = "test_topic"
    produce_event(producer, topic)
    assert producer.send.called
    assert producer.send.call_args[0][0] == topic

def test_producer_event_in_allowed_ranges(mocker):
    producer = mocker.MagicMock()
    for _ in range(50):
        event = produce_event(producer, "topic")
        assert 1000 <= event["audience_value"] <= 5_000_000
        assert event["platform"] in ALLOWED_PLATFORMS
