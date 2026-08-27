"""
jobs/gold/dim_property.py

Builds dim_property from distinct (property_id, property_name) in silver.
Table: <catalog>.gold.dim_property
Grain: one row per unique property_id
Update strategy: full refresh (truncate+overwrite) - idempotent, properties are stable
"""
from pyspark.sql.functions import current_timestamp, lit, row_number
from pyspark.sql.window import Window
from config.loader import load_config, get_full_table_name

def build_dim_property(spark, config) -> int:
    silver_table = get_full_table_name(config, 'silver', 'audience_events')
    gold_table = get_full_table_name(config, 'gold', 'dim_property')
    
    df = spark.read.table(silver_table)
    
    dim_df = df.select("property_id", "property_name").distinct()
    
    window_spec = Window.orderBy("property_id")
    
    dim_df = dim_df.withColumn("property_key", row_number().over(window_spec)) \
                   .withColumn("_effective_from", lit(current_timestamp())) \
                   .withColumn("_last_updated", lit(current_timestamp()))
                   
    dim_df = dim_df.select("property_key", "property_id", "property_name", "_effective_from", "_last_updated")
    
    dim_df.write.format("delta").mode("overwrite").saveAsTable(gold_table)
    
    return dim_df.count()
