# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🥇 Layer 4: Gold Dimensional Star Schema
# MAGIC **Real-Time Media Analytics Lakehouse**
# MAGIC 
# MAGIC Populates the Kimball Star Schema:
# MAGIC - 5 Dimension Tables (`dim_property`, `dim_geography`, `dim_platform`, `dim_category`, `dim_date`)
# MAGIC - Central Fact Table (`fact_audience`)

# COMMAND ----------
import os
import sys
from pyspark.sql import functions as F

sys.path.append("/Workspace/Users/abhay.aman.pandey@gmail.com/.bundle/real-time-media-analytics-lakehouse/dev/files")

from config.loader import load_config, get_full_table_name
from jobs.gold.gold_build import build_gold_dimensions, build_gold_fact

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 1: Load Silver Clean Data

# COMMAND ----------
env = os.environ.get("LAKEHOUSE_ENV", "dev")
config = load_config(env)

silver_table = get_full_table_name(config, "silver", "silver_events")
df_silver = spark.read.table(silver_table)
print(f"Loaded {df_silver.count()} clean Silver records.")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 2: Build & Refresh 5 Dimension Tables

# COMMAND ----------
build_gold_dimensions(spark, df_silver, config)
print("✅ Refreshed 5 Dimension tables: dim_property, dim_geography, dim_platform, dim_category, dim_date.")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 3: Populate Central Fact Table (`fact_audience`)

# COMMAND ----------
fact_count = build_gold_fact(spark, df_silver, config)
print(f"✅ Populated fact_audience with {fact_count} fact rows.")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 4: Audit Star Schema Joins

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT 
# MAGIC     p.property_name,
# MAGIC     g.geography_name,
# MAGIC     pl.platform_name,
# MAGIC     c.category_name,
# MAGIC     d.calendar_date,
# MAGIC     d.quarter_period,
# MAGIC     f.audience_value
# MAGIC FROM analytics_dev.gold.fact_audience f
# MAGIC JOIN analytics_dev.gold.dim_property p ON f.property_id = p.property_id
# MAGIC JOIN analytics_dev.gold.dim_geography g ON f.geography_id = g.geography_id
# MAGIC JOIN analytics_dev.gold.dim_platform pl ON f.platform_id = pl.platform_id
# MAGIC JOIN analytics_dev.gold.dim_category c ON f.category_id = c.category_id
# MAGIC JOIN analytics_dev.gold.dim_date d ON f.date_id = d.date_id
# MAGIC LIMIT 10;
