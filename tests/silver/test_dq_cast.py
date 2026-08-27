"""
tests/silver/test_dq_cast.py

Proof that DQ Rule 5 works: type cast validation.

Explicit casts with loud failure - no silent nulling.
cast failure -> hard drop -> quarantine with reason code.
"""
import pytest
from pyspark.sql import Row
from pyspark.sql.types import StructType, StructField, StringType, LongType, DateType
import datetime
from jobs.silver.dq_rules import check_casts, REASON_CAST_FAILURE_EVENT_DATE, REASON_CAST_FAILURE_AUDIENCE_VALUE

pytestmark = pytest.mark.databricks

def test_valid_date_string_cast_succeeds(spark):
    df = spark.createDataFrame([
        Row(event_date="2024-06-15", ingested_at="2024-06-15T12:00:00Z", audience_value=100)
    ])
    clean_df, q_df = check_casts(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 0
    assert isinstance(clean_df.first()["event_date"], datetime.date)

def test_invalid_date_string_quarantined(spark):
    df = spark.createDataFrame([
        Row(event_date="not-a-date", ingested_at="2024-06-15T12:00:00Z", audience_value=100)
    ])
    clean_df, q_df = check_casts(df, {})
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_CAST_FAILURE_EVENT_DATE

def test_wrong_date_format_quarantined(spark):
    df = spark.createDataFrame([
        Row(event_date="15/06/2024", ingested_at="2024-06-15T12:00:00Z", audience_value=100)
    ])
    clean_df, q_df = check_casts(df, {})
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_CAST_FAILURE_EVENT_DATE

def test_null_audience_value_quarantined(spark):
    schema = StructType([
        StructField("event_date", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("audience_value", LongType(), True)
    ])
    df = spark.createDataFrame([
        Row(event_date="2024-06-15", ingested_at="2024-06-15T12:00:00Z", audience_value=None)
    ], schema=schema)
    
    clean_df, q_df = check_casts(df, {})
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_CAST_FAILURE_AUDIENCE_VALUE

def test_valid_audience_value_passes(spark):
    df = spark.createDataFrame([
        Row(event_date="2024-06-15", ingested_at="2024-06-15T12:00:00Z", audience_value=500)
    ])
    clean_df, q_df = check_casts(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 0
