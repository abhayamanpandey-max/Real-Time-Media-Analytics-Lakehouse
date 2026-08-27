"""
tests/silver/test_dq_referential.py

Proof that DQ Rule 6 works: referential integrity against dim_property.

Every property_id in silver must exist in dim_property.
Violations are hard-dropped to quarantine with REFERENTIAL_INTEGRITY_PROPERTY_ID.

If dim_property table does not exist (first run), the check is skipped with a warning.
"""
import pytest
from pyspark.sql import Row
from jobs.silver.dq_rules import check_referential_integrity, REASON_REFERENTIAL_INTEGRITY_PROPERTY_ID

pytestmark = pytest.mark.databricks

def test_valid_property_id_passes(spark):
    dim_property_df = spark.createDataFrame([Row(property_id="P1")])
    df = spark.createDataFrame([Row(property_id="P1", val=100)])
    
    clean_df, q_df = check_referential_integrity(df, {}, dim_property_df=dim_property_df)
    
    assert clean_df.count() == 1
    assert q_df.count() == 0

def test_unknown_property_id_quarantined(spark):
    dim_property_df = spark.createDataFrame([Row(property_id="P1")])
    df = spark.createDataFrame([Row(property_id="PROP_999", val=100)])
    
    clean_df, q_df = check_referential_integrity(df, {}, dim_property_df=dim_property_df)
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_REFERENTIAL_INTEGRITY_PROPERTY_ID

def test_missing_dim_property_table_skips_check(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    
    def mock_get_full_table_name(config, schema, table):
        return "non_existent_table"
        
    monkeypatch.setattr(dq, "get_full_table_name", mock_get_full_table_name)
    
    df = spark.createDataFrame([Row(property_id="PROP_999", val=100)])
    
    # Should skip the check and not raise exception
    clean_df, q_df = dq.check_referential_integrity(df, {})
    
    assert clean_df.count() == 1
    assert q_df.count() == 0

def test_partial_match_mixed_results(spark):
    dim_property_df = spark.createDataFrame([Row(property_id="P1"), Row(property_id="P2")])
    df = spark.createDataFrame([
        Row(property_id="P1", val=100),
        Row(property_id="P2", val=200),
        Row(property_id="P3", val=300)
    ])
    
    clean_df, q_df = check_referential_integrity(df, {}, dim_property_df=dim_property_df)
    
    assert clean_df.count() == 2
    assert q_df.count() == 1
    assert q_df.first()["property_id"] == "P3"
