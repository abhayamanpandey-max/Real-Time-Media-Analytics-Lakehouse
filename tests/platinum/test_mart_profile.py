"""
tests/platinum/test_mart_profile.py

Tests for mart_audience_profile.
Verify grain, within-property percentage sums, peak_date validity.

# Grain: property_name x report_period x report_period_type x platform x geography_name
"""
import pytest
from pyspark.sql import functions as F

pytestmark = pytest.mark.databricks

def test_profile_grain_is_unique(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_profile")
    dup_count = df.groupBy("property_name", "report_period", "report_period_type", "platform", "geography_name") \
                  .count().filter(F.col("count") > 1).count()
    assert dup_count == 0

def test_profile_contains_both_period_types(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_profile")
    period_types = [row["report_period_type"] for row in df.select("report_period_type").distinct().collect()]
    assert "MONTHLY" in period_types
    assert "WEEKLY" in period_types

def test_within_property_pct_sums_to_100(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_profile")
    sums = df.groupBy("property_name", "report_period", "report_period_type") \
             .agg(F.sum("audience_within_property_pct").alias("total_pct")).collect()
    
    for row in sums:
        assert abs(row["total_pct"] - 100.0) < 0.01

def test_peak_date_within_period(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_profile")
    
    monthly_df = df.filter(F.col("report_period_type") == "MONTHLY")
    if monthly_df.count() > 0:
        monthly_df = monthly_df.withColumn("peak_month", F.date_format(F.col("peak_date"), "yyyy-MM"))
        mismatches = monthly_df.filter(F.col("peak_month") != F.col("report_period")).count()
        assert mismatches == 0

def test_total_audience_non_negative(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_profile")
    neg_count = df.filter(F.col("total_audience") < 0).count()
    assert neg_count == 0

def test_unknown_geography_present_if_nulls_exist(spark, config):
    fact = spark.table(f"{config['catalog']}.gold.fact_audience")
    null_geo_count = fact.filter(F.col("geography_key").isNull()).count()
    
    if null_geo_count > 0:
        df = spark.table(f"{config['catalog']}.platinum.mart_audience_profile")
        unknown_count = df.filter(F.col("geography_name") == "Unknown").count()
        assert unknown_count > 0
