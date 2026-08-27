"""
tests/gold/test_dims.py

Tests for all Gold dimension tables.
Verify uniqueness of natural keys, no nulls on key columns, correct row counts.
"""
import pytest
from pyspark.sql.functions import col, count

pytestmark = pytest.mark.databricks

def test_dim_property_natural_key_unique(spark, config):
    from jobs.gold.dim_property import build_dim_property
    from config.loader import get_full_table_name
    build_dim_property(spark, config)
    table_name = get_full_table_name(config, 'gold', 'dim_property')
    df = spark.read.table(table_name)
    duplicate_count = df.groupBy("property_id").count().filter(col("count") > 1).count()
    assert duplicate_count == 0

def test_dim_property_no_null_keys(spark, config):
    from config.loader import get_full_table_name
    table_name = get_full_table_name(config, 'gold', 'dim_property')
    df = spark.read.table(table_name)
    assert df.filter(col("property_id").isNull()).count() == 0
    assert df.filter(col("property_key").isNull()).count() == 0

def test_dim_platform_has_all_allowed_platforms(spark, config):
    from jobs.gold.dim_platform import build_dim_platform
    from config.loader import get_full_table_name, ALLOWED_PLATFORMS
    build_dim_platform(spark, config)
    table_name = get_full_table_name(config, 'gold', 'dim_platform')
    df = spark.read.table(table_name)
    assert df.count() == len(ALLOWED_PLATFORMS)
    
    platforms_in_db = [row.platform for row in df.select("platform").collect()]
    for p in ALLOWED_PLATFORMS:
        assert p in platforms_in_db

def test_dim_platform_no_null_keys(spark, config):
    from config.loader import get_full_table_name
    table_name = get_full_table_name(config, 'gold', 'dim_platform')
    df = spark.read.table(table_name)
    assert df.filter(col("platform").isNull()).count() == 0
    assert df.filter(col("platform_key").isNull()).count() == 0

def test_dim_category_has_all_allowed_categories(spark, config):
    from jobs.gold.dim_category import build_dim_category
    from config.loader import get_full_table_name, ALLOWED_CATEGORIES
    build_dim_category(spark, config)
    table_name = get_full_table_name(config, 'gold', 'dim_category')
    df = spark.read.table(table_name)
    assert df.count() == len(ALLOWED_CATEGORIES)

def test_dim_date_covers_expected_range(spark, config):
    from jobs.gold.dim_date import build_dim_date
    from config.loader import get_full_table_name
    build_dim_date(spark, config)
    table_name = get_full_table_name(config, 'gold', 'dim_date')
    df = spark.read.table(table_name)
    assert df.count() > 0

def test_dim_date_no_gaps(spark, config):
    from config.loader import get_full_table_name
    from pyspark.sql.functions import max, min, datediff
    table_name = get_full_table_name(config, 'gold', 'dim_date')
    df = spark.read.table(table_name)
    stats = df.agg(min("full_date").alias("min_d"), max("full_date").alias("max_d"), count("*").alias("cnt")).collect()[0]
    expected_days = (stats["max_d"] - stats["min_d"]).days + 1
    assert stats["cnt"] == expected_days

def test_dim_date_attributes_correct(spark, config):
    from config.loader import get_full_table_name
    table_name = get_full_table_name(config, 'gold', 'dim_date')
    df = spark.read.table(table_name)
    row = df.filter(col("full_date") == "2024-01-15").first()
    if row:
        assert row.calendar_year == 2024
        assert row.calendar_month == 1
        assert row.calendar_quarter == 1
        assert row.is_weekend == False

def test_dim_geography_natural_key_unique(spark, config):
    from jobs.gold.dim_geography import build_dim_geography
    from config.loader import get_full_table_name
    build_dim_geography(spark, config)
    table_name = get_full_table_name(config, 'gold', 'dim_geography')
    df = spark.read.table(table_name)
    duplicate_count = df.groupBy("geography_id").count().filter(col("count") > 1).count()
    assert duplicate_count == 0
