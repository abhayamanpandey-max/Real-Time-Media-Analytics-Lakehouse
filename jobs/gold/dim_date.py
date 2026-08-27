"""
jobs/gold/dim_date.py

Builds dim_date as a date spine from min(event_date) in silver to max(event_date) + 365 days.
This is a generated dimension - no source data needed beyond the date range in silver.
Table: <catalog>.gold.dim_date
Grain: one row per calendar date
Update strategy: full refresh - cheap to regenerate and ensures completeness
"""
from pyspark.sql.functions import col, min, max, explode, date_format, year, month, quarter, weekofyear, dayofweek, concat_ws, lpad, when
from config.loader import load_config, get_full_table_name

def build_dim_date(spark, config) -> int:
    silver_table = get_full_table_name(config, 'silver', 'audience_events')
    gold_table = get_full_table_name(config, 'gold', 'dim_date')
    
    try:
        silver_df = spark.read.table(silver_table)
        date_range = silver_df.agg(min("event_date").alias("min_date"), max("event_date").alias("max_date")).collect()[0]
        start_date = date_range["min_date"]
        end_date = date_range["max_date"]
    except Exception:
        start_date = "2020-01-01"
        end_date = "2020-01-01"
        
    if not start_date:
        start_date = "2020-01-01"
    if not end_date:
        end_date = "2020-01-01"
        
    df = spark.sql(f"SELECT sequence(to_date('{start_date}'), date_add(to_date('{end_date}'), 365), interval 1 day) as date_array")
    df = df.select(explode(col("date_array")).alias("full_date"))
    
    # PySpark dayofweek returns 1=Sunday, 2=Monday... 7=Saturday
    df = df.withColumn("pyspark_dow", dayofweek(col("full_date")))
    
    df = df.withColumn("date_key", date_format(col("full_date"), "yyyyMMdd").cast("int")) \
           .withColumn("calendar_year", year(col("full_date"))) \
           .withColumn("calendar_month", month(col("full_date"))) \
           .withColumn("calendar_month_name", date_format(col("full_date"), "MMMM")) \
           .withColumn("calendar_quarter", quarter(col("full_date"))) \
           .withColumn("iso_week", weekofyear(col("full_date"))) \
           .withColumn("iso_week_year", year(col("full_date"))) \
           .withColumn("day_of_week", when(col("pyspark_dow") == 1, 7).otherwise(col("pyspark_dow") - 1)) \
           .withColumn("day_of_week_name", date_format(col("full_date"), "EEEE")) \
           .withColumn("month_period", date_format(col("full_date"), "yyyy-MM")) \
           .withColumn("quarter_period", concat_ws("-Q", year(col("full_date")), quarter(col("full_date")))) \
           .withColumn("week_period", concat_ws("-W", year(col("full_date")), lpad(weekofyear(col("full_date")).cast("string"), 2, "0"))) \
           .withColumn("is_weekend", when(col("day_of_week").isin([6, 7]), True).otherwise(False))
           
    df = df.select("date_key", "full_date", "calendar_year", "calendar_month", "calendar_month_name", 
                   "calendar_quarter", "quarter_period", "iso_week", "iso_week_year", "day_of_week", "day_of_week_name", 
                   "month_period", "week_period", "is_weekend")
                   
    df.write.format("delta").mode("overwrite").saveAsTable(gold_table)
    
    return df.count()
