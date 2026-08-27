"""
tests/test_ingestion.py

Tests for the ingestion layer (api_client + bronze_writer).
API is mocked with the 'responses' library - no real server needed.
bronze_writer tests use a mock SparkSession - no Databricks required for unit tests.
Integration tests (actual Delta write) require Databricks Connect.
"""

from unittest.mock import MagicMock

import pytest
import responses

from config.loader import get_full_table_name
from ingestion.api_client import ApiClientError, fetch_all_events
from ingestion.bronze_writer import write_bronze


@responses.activate
def test_fetch_all_events_single_page(mock_config):
    responses.add(
        responses.GET,
        "http://testserver/events?page=1&page_size=10",
        json={"events": [{"id": 1}, {"id": 2}, {"id": 3}], "has_next": False},
        status=200,
    )

    events = fetch_all_events(mock_config)
    assert len(events) == 3


@responses.activate
def test_fetch_all_events_multiple_pages(mock_config):
    responses.add(
        responses.GET,
        "http://testserver/events?page=1&page_size=10",
        json={"events": [{"id": i} for i in range(10)], "has_next": True},
        status=200,
    )
    responses.add(
        responses.GET,
        "http://testserver/events?page=2&page_size=10",
        json={"events": [{"id": i} for i in range(10, 20)], "has_next": True},
        status=200,
    )
    responses.add(
        responses.GET,
        "http://testserver/events?page=3&page_size=10",
        json={"events": [{"id": i} for i in range(20, 30)], "has_next": False},
        status=200,
    )

    events = fetch_all_events(mock_config)
    assert len(events) == 30


@responses.activate
def test_fetch_all_events_stops_at_max_pages(mock_config):
    mock_config["api"]["max_pages"] = 2
    responses.add(
        responses.GET,
        "http://testserver/events?page=1&page_size=10",
        json={"events": [{"id": i} for i in range(10)], "has_next": True},
        status=200,
    )
    responses.add(
        responses.GET,
        "http://testserver/events?page=2&page_size=10",
        json={"events": [{"id": i} for i in range(10, 20)], "has_next": True},
        status=200,
    )

    events = fetch_all_events(mock_config)
    assert len(events) == 20


@responses.activate
def test_fetch_all_events_raises_on_401(mock_config):
    responses.add(
        responses.GET,
        "http://testserver/events?page=1&page_size=10",
        status=401,
    )

    with pytest.raises(ApiClientError):
        fetch_all_events(mock_config)


@responses.activate
def test_fetch_all_events_retries_on_500(mock_config, mocker):
    mocker.patch("time.sleep", return_value=None)
    responses.add(
        responses.GET,
        "http://testserver/events?page=1&page_size=10",
        status=500,
    )
    responses.add(
        responses.GET,
        "http://testserver/events?page=1&page_size=10",
        json={"events": [{"id": 1}], "has_next": False},
        status=200,
    )

    events = fetch_all_events(mock_config)
    assert len(events) == 1


@responses.activate
def test_fetch_all_events_auth_header(mock_config):
    responses.add(
        responses.GET,
        "http://testserver/events?page=1&page_size=10",
        json={"events": [], "has_next": False},
        status=200,
        match=[responses.matchers.header_matcher({"Authorization": "Bearer test-token"})],
    )

    fetch_all_events(mock_config)


def test_write_bronze_mode_is_always_append(sample_events, mock_config):
    mock_spark = MagicMock()
    mock_df = MagicMock()
    mock_spark.createDataFrame.return_value = mock_df
    mock_df.withColumn.return_value = mock_df
    mock_df.write.format.return_value.mode.return_value.saveAsTable = MagicMock()

    write_bronze(mock_spark, sample_events, mock_config, "test-run-id")

    mock_df.write.format.assert_called_with("delta")
    mock_df.write.format.return_value.mode.assert_called_with("append")


def test_write_bronze_adds_metadata_columns(sample_events, mock_config):
    mock_spark = MagicMock()
    write_bronze(mock_spark, sample_events, mock_config, "test-run-id", source_page=5)

    for event in sample_events:
        assert event["_bronze_run_id"] == "test-run-id"
        assert event["_source_api_page"] == 5


def test_write_bronze_returns_row_count(sample_events, mock_config):
    mock_spark = MagicMock()
    mock_df = MagicMock()
    mock_spark.createDataFrame.return_value = mock_df
    mock_df.withColumn.return_value = mock_df

    count = write_bronze(mock_spark, sample_events, mock_config, "test-run-id")
    assert count == 5


def test_write_bronze_raises_on_empty_events(mock_config):
    mock_spark = MagicMock()
    with pytest.raises(ValueError, match="Cannot write empty events list"):
        write_bronze(mock_spark, [], mock_config, "test-run-id")


def test_get_full_table_name(mock_config):
    name = get_full_table_name(mock_config, "bronze", "bronze_events")
    assert name == "test_catalog.bronze.audience_events"
