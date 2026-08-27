"""
jobs/gold/fact_audience.py

Builds fact_audience by joining silver events to all dimension tables.
Table: <catalog>.gold.fact_audience

# Grain: property_id x event_date x platform x geography_id
# One row = the measured audience for one property, on one date,
# on one platform, in one geography.
# To get 'total property audience for a period', SUM audience_value
# GROUP BY property, aggregating across all platforms and geographies.
# Never assume a single row per property per day.

Metric definition:
  audience_value: The count of unique audience members measured for this
    property x date x platform x geography combination. This is the ONLY
    definition of audience_value used in this pipeline. Never redefine it
    differently in gold, platinum, or semantic layers.
"""
from pyspark.sql.functions import col, current_timestamp, date_format, monotonically_increasing_id
from config.loader import load_config, get_full_table_name
import logging

logger = logging.getLogger(__name__)

def build_fact_audience(spark, config) -> int:
    silver_table = get_full_table_name(config, 'silver', 'audience_events')
    gold_fact = get_full_table_name(config, 'gold', 'fact_audience')
    
    dim_property = get_full_table_name(config, 'gold', 'dim_property')
    dim_geography = get_full_table_name(config, 'gold', 'dim_geography')
    dim_platform = get_full_table_name(config, 'gold', 'dim_platform')
    dim_category = get_full_table_name(config, 'gold', 'dim_category')
    dim_date = get_full_table_name(config, 'gold', 'dim_date')
    
    events = spark.read.table(silver_table)
    
    d_prop = spark.read.table(dim_property)
    d_geo = spark.read.table(dim_geography)
    d_plat = spark.read.table(dim_platform)
    d_cat = spark.read.table(dim_category)
    d_date = spark.read.table(dim_date)
    
    events_count = events.count()
    
    # Generate date_key for join
    events = events.withColumn("date_key", date_format(col("event_date"), "yyyyMMdd").cast("int"))
    
    # Joins
    fact = events.join(d_prop, on="property_id", how="inner") \
                 .join(d_plat, on="platform", how="inner") \
                 .join(d_cat, on="category", how="inner") \
                 .join(d_date, on="date_key", how="inner") \
                 .join(d_geo, on="geography_id", how="left")
                 
    fact_count = fact.count()
    if fact_count < events_count:
        logger.warning(f"Rows lost in fact build! Silver rows: {events_count}, Fact rows: {fact_count}")
        
    fact = fact.withColumn("fact_key", monotonically_increasing_id()) \
               .withColumn("_gold_processed_at", current_timestamp())
               
    fact = fact.select(
        "fact_key",
        "property_key",
        "geography_key",
        "platform_key",
        "category_key",
        "date_key",
        "audience_value",
        col("_is_spike_flagged"),
        col("_bronze_run_id").alias("_source_bronze_run_id"),
        col("_silver_processed_at"),
        "_gold_processed_at"
    )
    
    fact.write.format("delta").mode("overwrite").saveAsTable(gold_fact)
    
    return fact_count
