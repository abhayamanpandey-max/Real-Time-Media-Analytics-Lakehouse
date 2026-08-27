"""
tests/gold/test_fact_audience.py

Tests for fact_audience.
Verify grain, no orphaned foreign keys, metric definition preserved.

# Grain: property_id x event_date x platform x geography_id
"""
import pytest
from pyspark.sql.functions import col

pytestmark = pytest.mark.databricks

def test_fact_grain_is_unique(spark, config):
    from jobs.gold.fact_audience import build_fact_audience
    from config.loader import get_full_table_name
    build_fact_audience(spark, config)
    table_name = get_full_table_name(config, 'gold', 'fact_audience')
    df = spark.read.table(table_name)
    duplicates = df.groupBy("property_key", "date_key", "platform_key", "geography_key").count().filter(col("count") > 1)
    assert duplicates.count() == 0

def test_no_orphaned_property_keys(spark, config):
    from config.loader import get_full_table_name
    fact = spark.read.table(get_full_table_name(config, 'gold', 'fact_audience'))
    dim = spark.read.table(get_full_table_name(config, 'gold', 'dim_property'))
    orphaned = fact.join(dim, "property_key", "left_anti")
    assert orphaned.count() == 0

def test_no_orphaned_platform_keys(spark, config):
    from config.loader import get_full_table_name
    fact = spark.read.table(get_full_table_name(config, 'gold', 'fact_audience'))
    dim = spark.read.table(get_full_table_name(config, 'gold', 'dim_platform'))
    orphaned = fact.join(dim, "platform_key", "left_anti")
    assert orphaned.count() == 0

def test_no_orphaned_date_keys(spark, config):
    from config.loader import get_full_table_name
    fact = spark.read.table(get_full_table_name(config, 'gold', 'fact_audience'))
    dim = spark.read.table(get_full_table_name(config, 'gold', 'dim_date'))
    orphaned = fact.join(dim, "date_key", "left_anti")
    assert orphaned.count() == 0

def test_audience_value_non_negative(spark, config):
    from config.loader import get_full_table_name
    fact = spark.read.table(get_full_table_name(config, 'gold', 'fact_audience'))
    negative_values = fact.filter(col("audience_value") < 0)
    assert negative_values.count() == 0

def test_fact_row_count_matches_silver(spark, config):
    from config.loader import get_full_table_name
    fact = spark.read.table(get_full_table_name(config, 'gold', 'fact_audience'))
    silver = spark.read.table(get_full_table_name(config, 'silver', 'audience_events'))
    assert fact.count() == silver.count()

def test_gold_processed_at_not_null(spark, config):
    from config.loader import get_full_table_name
    fact = spark.read.table(get_full_table_name(config, 'gold', 'fact_audience'))
    null_processed = fact.filter(col("_gold_processed_at").isNull())
    assert null_processed.count() == 0
