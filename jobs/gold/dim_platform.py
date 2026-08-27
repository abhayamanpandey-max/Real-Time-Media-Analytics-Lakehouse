"""
jobs/gold/dim_platform.py

Builds dim_platform from the ALLOWED_PLATFORMS constant.
This is a static dimension - it is always rebuilt from the constant, never from silver data.
Adding a new platform = add it to ALLOWED_PLATFORMS in config/loader.py, then re-run this job.
Table: <catalog>.gold.dim_platform
Grain: one row per platform value
"""
from pyspark.sql.functions import monotonically_increasing_id
from config.loader import load_config, get_full_table_name, ALLOWED_PLATFORMS

def build_dim_platform(spark, config) -> int:
    gold_table = get_full_table_name(config, 'gold', 'dim_platform')
    
    platform_mapping = {
        "web": "Web Browser",
        "mobile_app": "Mobile App",
        "connected_tv": "Connected TV",
        "smart_tv": "Smart TV",
        "streaming_device": "Streaming Device",
        "desktop_app": "Desktop App"
    }
    
    data = [(p, platform_mapping.get(p, p)) for p in ALLOWED_PLATFORMS]
    schema = ["platform", "platform_display_name"]
    
    df = spark.createDataFrame(data, schema=schema)
    df = df.withColumn("platform_key", monotonically_increasing_id())
    
    df = df.select("platform_key", "platform", "platform_display_name")
    
    df.write.format("delta").mode("overwrite").saveAsTable(gold_table)
    
    return df.count()
