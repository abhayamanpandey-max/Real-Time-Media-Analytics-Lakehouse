"""
tests/silver/test_quarantine.py

Proof that the quarantine table has the correct structure.

Verifies:
- quarantine_reason column always present
- quarantine_timestamp column always present and not null
- All original bronze columns preserved
- Row count matches what was rejected
"""
import pytest
from pyspark.sql import Row
from jobs.silver.quarantine import write_quarantine
from jobs.silver.dq_rules import REASON_MISSING_PROPERTY_ID
import tempfile
import os
import pyspark.sql.functions as F

pytestmark = pytest.mark.databricks

@pytest.fixture
def temp_delta_table(spark, monkeypatch):
    temp_dir = tempfile.mkdtemp()
    table_path = os.path.join(temp_dir, "quarantine_table")
    
    import jobs.silver.quarantine as qu
    def mock_get_full_table_name(config, schema, table):
        return f"delta.`{table_path}`"
        
    monkeypatch.setattr(qu, "get_full_table_name", mock_get_full_table_name)
    yield table_path

def test_quarantine_has_reason_column(spark, temp_delta_table):
    df = spark.createDataFrame([Row(property_id="P1", val=100)])
    write_quarantine(spark, df, {}, REASON_MISSING_PROPERTY_ID)
    
    q_table = spark.read.format("delta").load(temp_delta_table)
    assert "quarantine_reason" in q_table.columns

def test_quarantine_has_timestamp_column(spark, temp_delta_table):
    df = spark.createDataFrame([Row(property_id="P1", val=100)])
    write_quarantine(spark, df, {}, REASON_MISSING_PROPERTY_ID)
    
    q_table = spark.read.format("delta").load(temp_delta_table)
    assert "quarantine_timestamp" in q_table.columns
    assert q_table.filter(F.col("quarantine_timestamp").isNull()).count() == 0

def test_quarantine_reason_matches_input(spark, temp_delta_table):
    df = spark.createDataFrame([Row(property_id="P1", val=100)])
    write_quarantine(spark, df, {}, REASON_MISSING_PROPERTY_ID)
    
    q_table = spark.read.format("delta").load(temp_delta_table)
    assert q_table.first()["quarantine_reason"] == REASON_MISSING_PROPERTY_ID

def test_quarantine_preserves_original_columns(spark, temp_delta_table):
    df = spark.createDataFrame([Row(col_a="a", col_b="b")])
    write_quarantine(spark, df, {}, "REASON")
    
    q_table = spark.read.format("delta").load(temp_delta_table)
    assert "col_a" in q_table.columns
    assert "col_b" in q_table.columns

def test_quarantine_is_append_only(spark, temp_delta_table):
    df1 = spark.createDataFrame([Row(val=1), Row(val=2), Row(val=3)])
    write_quarantine(spark, df1, {}, "REASON_1")
    
    df2 = spark.createDataFrame([Row(val=4), Row(val=5)])
    write_quarantine(spark, df2, {}, "REASON_2")
    
    q_table = spark.read.format("delta").load(temp_delta_table)
    assert q_table.count() == 5

def test_all_reason_codes_are_valid_strings():
    import jobs.silver.dq_rules as dq
    
    reasons = [
        dq.REASON_MISSING_PROPERTY_ID,
        dq.REASON_MISSING_EVENT_DATE,
        dq.REASON_MISSING_GEOGRAPHY_ID,
        dq.REASON_NEGATIVE_AUDIENCE_VALUE,
        dq.REASON_DUPLICATE_NATURAL_KEY,
        dq.REASON_INVALID_PLATFORM,
        dq.REASON_INVALID_CATEGORY,
        dq.REASON_CAST_FAILURE_EVENT_DATE,
        dq.REASON_CAST_FAILURE_AUDIENCE_VALUE,
        dq.REASON_REFERENTIAL_INTEGRITY_PROPERTY_ID,
        dq.REASON_IMPLAUSIBLE_SPIKE
    ]
    
    for r in reasons:
        assert isinstance(r, str)
        assert len(r) > 0
