"""
jobs/platinum/mart_audience_rankings.py

Builds mart_audience_rankings from Gold tables.
Table: <catalog>.platinum.mart_audience_rankings

# Grain: report_period x report_period_type x platform x geography_name x property_name
# One row = one property's total audience within one period, platform, and geography.
# 'audience_rank' is ranked WITHIN (period, period_type, platform, geography),
# not across all platforms and geographies combined.

# Metric definitions (authoritative - do not redefine elsewhere):
#   total_audience: SUM(audience_value) grouped by property + period + platform + geography
#   audience_rank: dense_rank() within partition descending by total_audience
#   audience_share_pct: total_audience / SUM(total_audience) in partition * 100

# Both MONTHLY and WEEKLY periods are included in the same table.
# Filter by report_period_type to get one or the other.

To run:
  LAKEHOUSE_ENV=dev python -m jobs.platinum.mart_audience_rankings
"""
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from config.loader import load_config, get_full_table_name
import sys

def build_mart_audience_rankings(spark, config) -> int:
    fact_audience_tbl = get_full_table_name(config, 'gold', 'fact_audience')
    dim_property_tbl = get_full_table_name(config, 'gold', 'dim_property')
    dim_geography_tbl = get_full_table_name(config, 'gold', 'dim_geography')
    dim_platform_tbl = get_full_table_name(config, 'gold', 'dim_platform')
    dim_date_tbl = get_full_table_name(config, 'gold', 'dim_date')

    fact = spark.table(fact_audience_tbl)
    dim_prop = spark.table(dim_property_tbl)
    dim_geo = spark.table(dim_geography_tbl)
    dim_plat = spark.table(dim_platform_tbl)
    dim_date = spark.table(dim_date_tbl)

    df = fact.join(dim_prop, "property_key", "left") \
             .join(dim_geo, "geography_key", "left") \
             .join(dim_plat, "platform_key", "left") \
             .join(dim_date, "date_key", "left")

    df = df.withColumn("geography_name", F.coalesce(F.col("geography_name"), F.lit("Unknown")))

    monthly_df = df.groupBy(
        F.col("month_period").alias("report_period"),
        F.lit("MONTHLY").alias("report_period_type"),
        F.col("platform"),
        F.col("platform_display_name"),
        F.col("geography_name"),
        F.col("property_name"),
        F.col("property_id")
    ).agg(
        F.sum("audience_value").alias("total_audience")
    )

    weekly_df = df.groupBy(
        F.col("week_period").alias("report_period"),
        F.lit("WEEKLY").alias("report_period_type"),
        F.col("platform"),
        F.col("platform_display_name"),
        F.col("geography_name"),
        F.col("property_name"),
        F.col("property_id")
    ).agg(
        F.sum("audience_value").alias("total_audience")
    )

    combined_df = monthly_df.unionByName(weekly_df)

    partition_cols = ["report_period", "report_period_type", "platform", "geography_name"]
    rank_window = Window.partitionBy(*partition_cols).orderBy(F.col("total_audience").desc())
    share_window = Window.partitionBy(*partition_cols)

    mart_df = combined_df.withColumn(
        "audience_rank", F.dense_rank().over(rank_window)
    ).withColumn(
        "audience_share_pct", (F.col("total_audience") / F.sum("total_audience").over(share_window)) * 100
    ).withColumn(
        "_platinum_processed_at", F.current_timestamp()
    )

    target_tbl = get_full_table_name(config, 'platinum', 'mart_audience_rankings')
    mart_df.write.mode("overwrite").saveAsTable(target_tbl)

    return mart_df.count()

if __name__ == "__main__":
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("Build Mart Audience Rankings").getOrCreate()
    config = load_config()
    build_mart_audience_rankings(spark, config)
