# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🥉 01 Ingest Bronze Notebook
# MAGIC Thin entrypoint for the Bronze ingestion layer.
# MAGIC Reads parameters from dbutils.widgets and invokes ingestion.ingest_run.main().

# COMMAND ----------
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("01_ingest_bronze")

# Define widgets with sensible defaults
try:
    dbutils.widgets.text("env", "dev", "LAKEHOUSE_ENV")
    dbutils.widgets.text("API_BASE_URL", "http://13.201.159.64:8000", "API_BASE_URL")
except Exception:
    pass

try:
    env = dbutils.widgets.get("env")
except Exception:
    env = os.environ.get("LAKEHOUSE_ENV", "dev")

try:
    api_base_url = dbutils.widgets.get("API_BASE_URL")
except Exception:
    api_base_url = os.environ.get("API_BASE_URL", "http://13.201.159.64:8000")

os.environ["LAKEHOUSE_ENV"] = env
os.environ["API_BASE_URL"] = api_base_url

logger.info(f"Starting Bronze Ingestion notebook [env={env}, API_BASE_URL={api_base_url}]")

from ingestion import ingest_run

try:
    ingest_run.main()
except SystemExit as e:
    if e.code != 0:
        raise RuntimeError(f"Ingestion failed with exit code {e.code}")

logger.info("Bronze Ingestion notebook completed successfully.")
