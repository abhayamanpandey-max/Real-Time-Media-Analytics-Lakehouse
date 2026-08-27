"""
tests/platinum/test_mart_rankings.py

Tests for mart_audience_rankings.
Verify grain, ranking correctness, share percentage sums, period types.

# Grain: report_period x report_period_type x platform x geography_name x property_name
"""
import pytest
from pyspark.sql import functions as F

pytestmark = pytest.mark.databricks

def test_rankings_grain_is_unique(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_rankings")
    dup_count = df.groupBy("report_period", "report_period_type", "platform", "geography_name", "property_name") \
                  .count().filter(F.col("count") > 1).count()
    assert dup_count == 0

def test_rankings_contains_both_period_types(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_rankings")
    period_types = [row["report_period_type"] for row in df.select("report_period_type").distinct().collect()]
    assert "MONTHLY" in period_types
    assert "WEEKLY" in period_types

def test_audience_rank_starts_at_1(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_rankings")
    min_ranks = df.groupBy("report_period", "report_period_type", "platform", "geography_name") \
                  .agg(F.min("audience_rank").alias("min_rank")).collect()
    for row in min_ranks:
        assert row["min_rank"] == 1

def test_audience_rank_is_dense(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_rankings")
    stats = df.groupBy("report_period", "report_period_type", "platform", "geography_name") \
              .agg(F.max("audience_rank").alias("max_rank"), 
                   F.countDistinct("audience_rank").alias("dist_ranks")).collect()
    for row in stats:
        assert row["max_rank"] == row["dist_ranks"]

def test_highest_audience_gets_rank_1(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_rankings")
    rank_1_df = df.filter(F.col("audience_rank") == 1)
    
    max_audience_df = df.groupBy("report_period", "report_period_type", "platform", "geography_name") \
                        .agg(F.max("total_audience").alias("max_audience"))
                        
    joined = rank_1_df.join(max_audience_df, 
                            ["report_period", "report_period_type", "platform", "geography_name"])
    
    mismatches = joined.filter(F.col("total_audience") != F.col("max_audience")).count()
    assert mismatches == 0

def test_share_pct_sums_to_100_within_partition(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_rankings")
    sums = df.groupBy("report_period", "report_period_type", "platform", "geography_name") \
             .agg(F.sum("audience_share_pct").alias("total_share")).collect()
    
    for row in sums:
        assert abs(row["total_share"] - 100.0) < 0.01

def test_total_audience_non_negative(spark, config):
    df = spark.table(f"{config['catalog']}.platinum.mart_audience_rankings")
    neg_count = df.filter(F.col("total_audience") < 0).count()
    assert neg_count == 0
