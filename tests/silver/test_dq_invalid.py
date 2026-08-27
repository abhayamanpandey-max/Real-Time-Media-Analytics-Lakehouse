"""
tests/silver/test_dq_invalid.py

Proof that DQ Rule 3 works: invalid value rejection.

Negative audience_value is hard-dropped.
"""
import pytest
from pyspark.sql import Row
from jobs.silver.dq_rules import check_invalid_values, REASON_NEGATIVE_AUDIENCE_VALUE

pytestmark = pytest.mark.databricks

def test_negative_audience_value_hard_dropped(spark):
    df = spark.createDataFrame([
        Row(audience_value=-1000)
    ])
    clean_df, q_df = check_invalid_values(df, {})
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_NEGATIVE_AUDIENCE_VALUE

def test_zero_audience_value_passes(spark):
    df = spark.createDataFrame([
        Row(audience_value=0)
    ])
    clean_df, q_df = check_invalid_values(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 0

def test_large_positive_passes(spark):
    df = spark.createDataFrame([
        Row(audience_value=5000000)
    ])
    clean_df, q_df = check_invalid_values(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 0

def test_mixed_valid_and_negative(spark):
    df = spark.createDataFrame([
        Row(audience_value=-10),
        Row(audience_value=0),
        Row(audience_value=100)
    ])
    clean_df, q_df = check_invalid_values(df, {})
    
    assert clean_df.count() == 2
    assert q_df.count() == 1
