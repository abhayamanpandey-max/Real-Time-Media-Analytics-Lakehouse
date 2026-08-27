"""
jobs/gold/dim_category.py

Builds dim_category from the ALLOWED_CATEGORIES constant.
This is a static dimension - it is always rebuilt from the constant, never from silver data.
Adding a new category = add it to ALLOWED_CATEGORIES in config/loader.py, then re-run this job.
Table: <catalog>.gold.dim_category
Grain: one row per category value
"""
from pyspark.sql.functions import monotonically_increasing_id
from config.loader import load_config, get_full_table_name, ALLOWED_CATEGORIES

def build_dim_category(spark, config) -> int:
    gold_table = get_full_table_name(config, 'gold', 'dim_category')
    
    category_mapping = {
        "news": "News",
        "sports": "Sports",
        "entertainment": "Entertainment",
        "lifestyle": "Lifestyle",
        "documentary": "Documentary",
        "kids": "Kids & Family",
        "finance": "Finance",
        "tech": "Technology"
    }
    
    data = [(c, category_mapping.get(c, c)) for c in ALLOWED_CATEGORIES]
    schema = ["category", "category_display_name"]
    
    df = spark.createDataFrame(data, schema=schema)
    df = df.withColumn("category_key", monotonically_increasing_id())
    
    df = df.select("category_key", "category", "category_display_name")
    
    df.write.format("delta").mode("overwrite").saveAsTable(gold_table)
    
    return df.count()
