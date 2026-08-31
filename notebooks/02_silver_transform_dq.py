# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🥈 Layer 3: Silver Data Quality & Quarantine Pipeline
# MAGIC **Real-Time Media Analytics Lakehouse**
# MAGIC 
# MAGIC Reads from Bronze Delta table, executes **7 Data Quality (DQ) Rules**, cleans/standardizes fields, routes rejected rows to `silver.audience_quarantine`, and merges clean records into `analytics_dev.silver.audience_events`.

# COMMAND ----------
import os
import sys
from pyspark.sql import functions as F

sys.path.append("/Workspace/Users/abhay.aman.pandey@gmail.com/.bundle/real-time-media-analytics-lakehouse/dev/files")

from config.loader import load_config, get_full_table_name
from jobs.silver.dq_rules import (
    check_casts,
    check_missing_required,
    check_normalisation_and_allowed_values,
    check_invalid_values,
    check_duplicates,
    check_spikes,
    check_referential_integrity,
)
from jobs.silver.quarantine import write_quarantine

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 1: Read Raw Bronze Delta Table

# COMMAND ----------
env = os.environ.get("LAKEHOUSE_ENV", "dev")
config = load_config(env)

bronze_table = get_full_table_name(config, "bronze", "bronze_events")
silver_table = get_full_table_name(config, "silver", "silver_events")

df_bronze = spark.read.table(bronze_table)
print(f"Read {df_bronze.count()} raw rows from Bronze: {bronze_table}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 2: Apply 7 Data Quality Rules in Sequence

# COMMAND ----------
# Rule 1: Type Casts
clean_df, q1 = check_casts(df_bronze, config)
write_quarantine(spark, q1, config, "CAST_FAILURE")

# Rule 2: Missing Required Values
clean_df, q2 = check_missing_required(clean_df, config)
write_quarantine(spark, q2, config, "MISSING_REQUIRED_FIELD")

# Rule 3: Normalization & Enum Validation
clean_df, q3 = check_normalisation_and_allowed_values(clean_df, config)
write_quarantine(spark, q3, config, "INVALID_ENUM_VALUE")

# Rule 4: Invalid Numeric Values
clean_df, q4 = check_invalid_values(clean_df, config)
write_quarantine(spark, q4, config, "NEGATIVE_AUDIENCE_VALUE")

# Rule 5: Deduplication on Natural Key
clean_df, q5 = check_duplicates(clean_df, config)
write_quarantine(spark, q5, config, "DUPLICATE_NATURAL_KEY")

# Rule 6: Spike Detection (7-day Rolling Median)
clean_df, q6 = check_spikes(clean_df, config)
write_quarantine(spark, q6, config, "IMPLAUSIBLE_SPIKE")

# Rule 7: Referential Integrity
clean_df, q7 = check_referential_integrity(clean_df, config)
write_quarantine(spark, q7, config, "REFERENTIAL_INTEGRITY_PROPERTY_ID")

print(f"Clean Silver Rows Remaining: {clean_df.count()}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 3: Write Clean Rows to Silver Delta Table

# COMMAND ----------
clean_df = clean_df.withColumn("_silver_processed_at", F.current_timestamp())
clean_df.write.format("delta").mode("append").partitionBy("event_date").saveAsTable(silver_table)
print(f"✅ Successfully wrote clean Silver records to {silver_table}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 4: Quarantine Breakdown Audit

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT 
# MAGIC     quarantine_reason, 
# MAGIC     COUNT(*) AS total_quarantined_rows,
# MAGIC     MAX(quarantine_timestamp) AS latest_failure
# MAGIC FROM analytics_dev.silver.audience_quarantine
# MAGIC GROUP BY quarantine_reason
# MAGIC ORDER BY total_quarantined_rows DESC;
