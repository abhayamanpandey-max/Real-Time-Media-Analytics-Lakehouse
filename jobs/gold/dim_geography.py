"""
jobs/gold/dim_geography.py

Builds dim_geography from distinct (geography_id, geography_name) in silver.
Table: <catalog>.gold.dim_geography
Grain: one row per unique geography_id
Update strategy: full refresh (truncate+overwrite)
"""
from pyspark.sql.functions import col, current_timestamp, lit, row_number
from pyspark.sql.window import Window
from config.loader import load_config, get_full_table_name

def build_dim_geography(spark, config) -> int:
    silver_table = get_full_table_name(config, 'silver', 'audience_events')
    gold_table = get_full_table_name(config, 'gold', 'dim_geography')
    
    df = spark.read.table(silver_table)
    
    dim_df = df.filter(col("geography_id").isNotNull()).select("geography_id", "geography_name").distinct()
    
    window_spec = Window.orderBy("geography_id")
    
    # TODO: Add region_group column here to group geographies into macro-regions
    
    dim_df = dim_df.withColumn("geography_key", row_number().over(window_spec)) \
                   .withColumn("_effective_from", lit(current_timestamp())) \
                   .withColumn("_last_updated", lit(current_timestamp()))
                   
    dim_df = dim_df.select("geography_key", "geography_id", "geography_name", "_effective_from", "_last_updated")
    
    dim_df.write.format("delta").mode("overwrite").saveAsTable(gold_table)
    
    return dim_df.count()
