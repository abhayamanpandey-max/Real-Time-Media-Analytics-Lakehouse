"""
tests/conftest.py

Shared pytest fixtures.

FIXTURE NOTES:
  spark  - Uses Databricks Connect. Requires a running cluster.
            Requires env vars: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_CLUSTER_ID
            Mark tests using this fixture with @pytest.mark.databricks.
            Run without Databricks: pytest -m 'not databricks'

  config - Loads dev config. Pure Python, no Databricks required.

  mock_config - Minimal hardcoded config for unit tests.

  sample_events - List of 5 valid raw event dicts for ingestion tests.
"""
import pytest

from config.loader import load_config


@pytest.fixture(scope="session")
def config():
    return load_config("dev")


@pytest.fixture(scope="session")
def mock_config():
    return {
        "env": "dev",
        "api": {
            "base_url": "http://testserver",
            "token": "test-token",
            "page_size": 10,
            "max_pages": 5,
        },
        "kafka": {
            "bootstrap_servers": "localhost:9092",
            "topic": "test-topic",
            "group_id": "test-group",
        },
        "databricks": {
            "catalog": "test_catalog",
            "schemas": {
                "bronze": "bronze",
                "silver": "silver",
                "gold": "gold",
                "platinum": "platinum",
                "semantic": "semantic",
            },
            "tables": {
                "bronze_events": "audience_events",
                "silver_events": "audience_events",
                "silver_quarantine": "audience_quarantine",
                "dim_property": "dim_property",
                "dim_geography": "dim_geography",
                "dim_platform": "dim_platform",
                "dim_category": "dim_category",
                "dim_date": "dim_date",
                "fact_audience": "fact_audience",
                "mart_rankings": "mart_audience_rankings",
                "mart_profile": "mart_audience_profile",
            },
        },
        "spike_detection": {"window_days": 7, "multiplier": 5},
    }


@pytest.fixture(scope="session")
def spark(request):
    """Databricks Connect session. Skips if DATABRICKS env vars not set."""
    import os
    if not os.environ.get("DATABRICKS_HOST"):
        pytest.skip("DATABRICKS_HOST not set - skipping Databricks Connect tests")
    from databricks.connect import DatabricksSession
    session = DatabricksSession.builder.getOrCreate()
    yield session


@pytest.fixture(scope="function")
def sample_events():
    """Five valid raw event dicts matching AudienceEvent schema."""
    return [
        {
            "event_id": f"evt-{i:04d}-test",
            "property_id": f"PROP_{i:03d}",
            "property_name": f"Test Property {i}",
            "geography_id": f"GEO_{i:03d}",
            "geography_name": f"Test Region {i}",
            "platform": "web",
            "category": "news",
            "event_date": "2024-06-15",
            "audience_value": 100_000 * i,
            "ingested_at": "2024-06-15T12:00:00Z",
        }
        for i in range(1, 6)
    ]
