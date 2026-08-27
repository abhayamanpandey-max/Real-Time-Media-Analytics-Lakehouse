"""
tests/silver/test_dq_duplicates.py

Proof that DQ Rule 2 works: deduplication on natural key.

Natural key: (property_id, event_date, platform, geography_id)
First occurrence (by _bronze_ingested_at) is kept; rest go to quarantine.
"""
import pytest
from pyspark.sql import Row
from jobs.silver.dq_rules import check_duplicates, REASON_DUPLICATE_NATURAL_KEY

pytestmark = pytest.mark.databricks

def test_exact_duplicate_quarantined(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:00:00Z"),
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:05:00Z")
    ])
    clean_df, q_df = check_duplicates(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_DUPLICATE_NATURAL_KEY

def test_non_duplicate_passes(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:00:00Z"),
        Row(property_id="P1", event_date="2024-01-01", platform="mobile", geography_id="US", _bronze_ingested_at="2024-01-02T10:05:00Z")
    ])
    clean_df, q_df = check_duplicates(df, {})
    
    assert clean_df.count() == 2
    assert q_df.count() == 0

def test_first_occurrence_kept_by_timestamp(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:05:00Z", val="second"),
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:00:00Z", val="first")
    ])
    clean_df, q_df = check_duplicates(df, {})
    
    assert clean_df.count() == 1
    assert clean_df.first()["val"] == "first"

def test_three_duplicates_two_quarantined(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:00:00Z"),
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:05:00Z"),
        Row(property_id="P1", event_date="2024-01-01", platform="web", geography_id="US", _bronze_ingested_at="2024-01-02T10:10:00Z")
    ])
    clean_df, q_df = check_duplicates(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 2

def test_natural_key_explanation_in_docstring():
    assert "natural key" in check_duplicates.__doc__.lower()
