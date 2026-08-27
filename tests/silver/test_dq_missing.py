"""
tests/silver/test_dq_missing.py

Proof that DQ Rule 1 works: missing value handling.

Hard-drop rows with missing property_id or event_date.
Soft-log (quarantine but KEEP in clean) rows with missing geography_id.

These tests use Databricks Connect (spark fixture).
Run without Databricks: pytest -m 'not databricks'
"""
import pytest
from pyspark.sql import Row
from jobs.silver.dq_rules import check_missing_required, REASON_MISSING_PROPERTY_ID, REASON_MISSING_EVENT_DATE, REASON_MISSING_GEOGRAPHY_ID

pytestmark = pytest.mark.databricks

def test_missing_property_id_is_hard_dropped(spark):
    df = spark.createDataFrame([
        Row(property_id=None, event_date="2024-01-01", geography_id="US", other_col="a")
    ])
    clean_df, q_df = check_missing_required(df, {})
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_MISSING_PROPERTY_ID

def test_missing_event_date_is_hard_dropped(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", event_date=None, geography_id="US", other_col="a")
    ])
    clean_df, q_df = check_missing_required(df, {})
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_MISSING_EVENT_DATE

def test_missing_geography_id_soft_logged(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", event_date="2024-01-01", geography_id=None, other_col="a")
    ])
    clean_df, q_df = check_missing_required(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_MISSING_GEOGRAPHY_ID

def test_valid_row_passes_all_checks(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", event_date="2024-01-01", geography_id="US", other_col="a")
    ])
    clean_df, q_df = check_missing_required(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 0

def test_multiple_rows_mixed(spark):
    df = spark.createDataFrame([
        Row(property_id=None, event_date="2024-01-01", geography_id="US"),
        Row(property_id="P2", event_date=None, geography_id="US"),
        Row(property_id="P3", event_date="2024-01-01", geography_id=None),
        Row(property_id="P4", event_date="2024-01-01", geography_id="US"),
        Row(property_id="P5", event_date="2024-01-01", geography_id="US")
    ])
    clean_df, q_df = check_missing_required(df, {})
    
    assert clean_df.count() == 3
    assert q_df.count() == 3
