"""
tests/silver/test_dq_normalization.py

Proof that DQ Rule 4 works: normalisation and allowed value set validation.

Normalisation: strip whitespace + lowercase on platform and category.
Validation: after normalisation, value must be in ALLOWED_PLATFORMS / ALLOWED_CATEGORIES.
"""
import pytest
from pyspark.sql import Row
from jobs.silver.dq_rules import check_normalisation_and_allowed_values, REASON_INVALID_PLATFORM, REASON_INVALID_CATEGORY

pytestmark = pytest.mark.databricks

# Mock config for tests
mock_config = {}

def test_platform_whitespace_normalised(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    monkeypatch.setattr(dq, "ALLOWED_PLATFORMS", ["web"])
    monkeypatch.setattr(dq, "ALLOWED_CATEGORIES", ["news"])
    
    df = spark.createDataFrame([
        Row(platform=" WEB ", category="news")
    ])
    clean_df, q_df = dq.check_normalisation_and_allowed_values(df, mock_config)
    
    assert clean_df.count() == 1
    assert clean_df.first()["platform"] == "web"
    assert q_df.count() == 0

def test_platform_uppercase_normalised(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    monkeypatch.setattr(dq, "ALLOWED_PLATFORMS", ["mobile_app"])
    monkeypatch.setattr(dq, "ALLOWED_CATEGORIES", ["news"])
    
    df = spark.createDataFrame([
        Row(platform="MOBILE_APP", category="news")
    ])
    clean_df, q_df = dq.check_normalisation_and_allowed_values(df, mock_config)
    
    assert clean_df.count() == 1
    assert clean_df.first()["platform"] == "mobile_app"

def test_category_normalised(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    monkeypatch.setattr(dq, "ALLOWED_PLATFORMS", ["web"])
    monkeypatch.setattr(dq, "ALLOWED_CATEGORIES", ["news"])
    
    df = spark.createDataFrame([
        Row(platform="web", category=" NEWS ")
    ])
    clean_df, q_df = dq.check_normalisation_and_allowed_values(df, mock_config)
    
    assert clean_df.count() == 1
    assert clean_df.first()["category"] == "news"

def test_invalid_platform_after_normalisation_hard_dropped(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    monkeypatch.setattr(dq, "ALLOWED_PLATFORMS", ["web", "mobile_app"])
    monkeypatch.setattr(dq, "ALLOWED_CATEGORIES", ["news"])
    
    df = spark.createDataFrame([
        Row(platform="television", category="news")
    ])
    clean_df, q_df = dq.check_normalisation_and_allowed_values(df, mock_config)
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_INVALID_PLATFORM

def test_invalid_category_after_normalisation_hard_dropped(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    monkeypatch.setattr(dq, "ALLOWED_PLATFORMS", ["web"])
    monkeypatch.setattr(dq, "ALLOWED_CATEGORIES", ["news", "sports"])
    
    df = spark.createDataFrame([
        Row(platform="web", category="movies")
    ])
    clean_df, q_df = dq.check_normalisation_and_allowed_values(df, mock_config)
    
    assert clean_df.count() == 0
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_INVALID_CATEGORY

def test_all_allowed_platforms_pass(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    allowed_platforms = ["web", "mobile_app", "smart_tv"]
    monkeypatch.setattr(dq, "ALLOWED_PLATFORMS", allowed_platforms)
    monkeypatch.setattr(dq, "ALLOWED_CATEGORIES", ["news"])
    
    rows = [Row(platform=p, category="news") for p in allowed_platforms]
    df = spark.createDataFrame(rows)
    clean_df, q_df = dq.check_normalisation_and_allowed_values(df, mock_config)
    
    assert clean_df.count() == len(allowed_platforms)
    assert q_df.count() == 0

def test_all_allowed_categories_pass(spark, monkeypatch):
    import jobs.silver.dq_rules as dq
    allowed_categories = ["news", "sports", "entertainment"]
    monkeypatch.setattr(dq, "ALLOWED_PLATFORMS", ["web"])
    monkeypatch.setattr(dq, "ALLOWED_CATEGORIES", allowed_categories)
    
    rows = [Row(platform="web", category=c) for c in allowed_categories]
    df = spark.createDataFrame(rows)
    clean_df, q_df = dq.check_normalisation_and_allowed_values(df, mock_config)
    
    assert clean_df.count() == len(allowed_categories)
    assert q_df.count() == 0
