# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🥈 02 Silver Transform Notebook
# MAGIC Thin entrypoint for the Silver DQ transformation layer.
# MAGIC Reads parameters from dbutils.widgets and invokes jobs.silver.silver_transform.run().

# COMMAND ----------
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("02_silver_transform")

try:
    dbutils.widgets.text("env", "dev", "LAKEHOUSE_ENV")
except Exception:
    pass

try:
    env = dbutils.widgets.get("env")
except Exception:
    env = os.environ.get("LAKEHOUSE_ENV", "dev")

os.environ["LAKEHOUSE_ENV"] = env

logger.info(f"Starting Silver Transform notebook [env={env}]")

from jobs.silver import silver_transform

try:
    silver_transform.run()
except SystemExit as e:
    if e.code != 0:
        raise RuntimeError(f"Silver transform failed with exit code {e.code}")

logger.info("Silver Transform notebook completed successfully.")
