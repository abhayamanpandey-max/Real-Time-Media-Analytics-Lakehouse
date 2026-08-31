# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 💎 Layer 5: Platinum Multi-Period Analytical Marts
# MAGIC **Real-Time Media Analytics Lakehouse**
# MAGIC 
# MAGIC Pre-aggregates audience metrics across **MONTHLY**, **WEEKLY**, and **QUARTERLY** reporting periods into high-performance analytical marts (`mart_audience_rankings` & `mart_audience_profile`).

# COMMAND ----------
import os
import sys
from pyspark.sql import functions as F

sys.path.append("/Workspace/Users/abhay.aman.pandey@gmail.com/.bundle/real-time-media-analytics-lakehouse/dev/files")

from config.loader import load_config, get_full_table_name
from jobs.platinum.platinum_build import build_platinum_marts

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 1: Build & Refresh Platinum Multi-Period Marts

# COMMAND ----------
env = os.environ.get("LAKEHOUSE_ENV", "dev")
config = load_config(env)

rankings_count, profile_count = build_platinum_marts(spark, config)
print(f"✅ Refreshed Platinum Marts: mart_audience_rankings ({rankings_count} rows), mart_audience_profile ({profile_count} rows).")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 2: Audit Quarterly Rankings Mart

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT 
# MAGIC     report_period,
# MAGIC     property_name,
# MAGIC     total_audience,
# MAGIC     audience_rank,
# MAGIC     audience_share_pct
# MAGIC FROM analytics_dev.platinum.mart_audience_rankings
# MAGIC WHERE report_period_type = 'QUARTERLY'
# MAGIC ORDER BY report_period DESC, audience_rank ASC
# MAGIC LIMIT 10;
