"""
jobs/platinum/mart_audience_profile.py

Builds mart_audience_profile from Gold tables.
Table: <catalog>.platinum.mart_audience_profile

# Grain: property_name x report_period x report_period_type x platform x geography_name
# One row = one property's audience for one platform+geography+period combination.
# Purpose: property-centric audience composition analysis.
# Answers: 'What is this property's audience breakdown by platform and geography in period X?'

# Metric definitions:
#   total_audience: SUM(audience_value) for property + period + platform + geography
#   audience_within_property_pct: total_audience / SUM(total_audience) per (property, period, period_type) * 100
#   peak_date: date with MAX(audience_value) for property + platform + geography + period

To run:
  LAKEHOUSE_ENV=dev python -m jobs.platinum.mart_audience_profile
"""
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from config.loader import load_config, get_full_table_name
import sys

def build_mart_audience_profile(spark, config) -> int:
    fact_audience_tbl = get_full_table_name(config, 'gold', 'fact_audience')
    dim_property_tbl = get_full_table_name(config, 'gold', 'dim_property')
    dim_geography_tbl = get_full_table_name(config, 'gold', 'dim_geography')
    dim_platform_tbl = get_full_table_name(config, 'gold', 'dim_platform')
    dim_category_tbl = get_full_table_name(config, 'gold', 'dim_category')
    dim_date_tbl = get_full_table_name(config, 'gold', 'dim_date')

    fact = spark.table(fact_audience_tbl)
    dim_prop = spark.table(dim_property_tbl)
    dim_geo = spark.table(dim_geography_tbl)
    dim_plat = spark.table(dim_platform_tbl)
    dim_cat = spark.table(dim_category_tbl)
    dim_date = spark.table(dim_date_tbl)

    df = fact.join(dim_prop, "property_key", "left") \
             .join(dim_geo, "geography_key", "left") \
             .join(dim_plat, "platform_key", "left") \
             .join(dim_cat, "category_key", "left") \
             .join(dim_date, "date_key", "left")

    df = df.withColumn("geography_name", F.coalesce(F.col("geography_name"), F.lit("Unknown")))

    monthly_detail = df.withColumn("report_period", F.col("month_period")) \
                       .withColumn("report_period_type", F.lit("MONTHLY"))
                       
    weekly_detail = df.withColumn("report_period", F.col("week_period")) \
                      .withColumn("report_period_type", F.lit("WEEKLY"))
                      
    union_detail = monthly_detail.unionByName(weekly_detail)
    
    peak_window = Window.partitionBy(
        "property_name", "property_id", "report_period", "report_period_type", 
        "platform", "platform_display_name", "geography_name", "category_display_name"
    ).orderBy(F.col("audience_value").desc())
    
    with_peak = union_detail.withColumn(
        "peak_date", F.first("full_date").over(peak_window)
    )

    agg_df = with_peak.groupBy(
        "property_name", "property_id", "report_period", "report_period_type",
        "platform", "platform_display_name", "geography_name", "category_display_name",
        "peak_date"
    ).agg(
        F.sum("audience_value").alias("total_audience")
    )
    
    prop_window = Window.partitionBy("property_name", "report_period", "report_period_type")
    
    mart_df = agg_df.withColumn(
        "audience_within_property_pct", 
        (F.col("total_audience") / F.sum("total_audience").over(prop_window)) * 100
    ).withColumn(
        "_platinum_processed_at", F.current_timestamp()
    )

    target_tbl = get_full_table_name(config, 'platinum', 'mart_audience_profile')
    mart_df.write.mode("overwrite").saveAsTable(target_tbl)

    return mart_df.count()

if __name__ == "__main__":
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("Build Mart Audience Profile").getOrCreate()
    config = load_config()
    build_mart_audience_profile(spark, config)
