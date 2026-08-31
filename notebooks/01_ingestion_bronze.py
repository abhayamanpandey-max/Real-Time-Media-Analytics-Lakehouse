# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🥉 Layer 1 & 2: Ingestion & Bronze Delta Table Creation
# MAGIC **Real-Time Media Analytics Lakehouse**
# MAGIC 
# MAGIC Ingests raw telemetry events from the AWS EC2 source API endpoint into the immutable Bronze Delta table (`analytics_dev.bronze.audience_events`).

# COMMAND ----------
import os
import sys
import uuid
import time
import logging
from pyspark.sql import functions as F

# Add project root to sys.path
sys.path.append("/Workspace/Users/abhay.aman.pandey@gmail.com/.bundle/real-time-media-analytics-lakehouse/dev/files")

from config.loader import load_config, get_full_table_name
from ingestion.api_client import fetch_all_events
from ingestion.bronze_writer import write_bronze

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 1: Load Environment Configuration

# COMMAND ----------
env = os.environ.get("LAKEHOUSE_ENV", "dev")
config = load_config(env)
config["api"]["base_url"] = "http://13.201.159.64:8000"

print(f"Target Catalog: {config['databricks']['catalog']}")
print(f"Target Schema:  {config['databricks']['schemas']['bronze']}")
print(f"API Base URL:   {config['api']['base_url']}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 2: Fetch Events from Ingestion Endpoint & Append to Bronze

# COMMAND ----------
run_id = str(uuid.uuid4())
start_time = time.time()

events, fallback_used = fetch_all_events(config)
print(f"Fetched {len(events)} events (FALLBACK_USED={fallback_used})")

rows_written = write_bronze(spark, events, config, run_id)
duration = time.time() - start_time

print(f"✅ Ingestion Complete! Wrote {rows_written} rows to Bronze Delta table in {duration:.2f}s.")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Step 3: Audit Bronze Delta Table Contents

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT 
# MAGIC     event_id, property_name, geography_name, platform, category, 
# MAGIC     event_date, audience_value, _ingestion_source, _bronze_ingested_at, _bronze_run_id
# MAGIC FROM analytics_dev.bronze.audience_events
# MAGIC ORDER BY _bronze_ingested_at DESC
# MAGIC LIMIT 10;
