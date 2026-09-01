# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🥇 03 Build Gold Notebook
# MAGIC Thin entrypoint for the Gold Star Schema layer.
# MAGIC Reads parameters from dbutils.widgets and invokes jobs.gold.gold_run.main().

# COMMAND ----------
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("03_build_gold")

try:
    dbutils.widgets.text("env", "dev", "LAKEHOUSE_ENV")
except Exception:
    pass

try:
    env = dbutils.widgets.get("env")
except Exception:
    env = os.environ.get("LAKEHOUSE_ENV", "dev")

os.environ["LAKEHOUSE_ENV"] = env

logger.info(f"Starting Gold Build notebook [env={env}]")

from jobs.gold import gold_run

try:
    gold_run.main()
except SystemExit as e:
    if e.code != 0:
        raise RuntimeError(f"Gold build failed with exit code {e.code}")

logger.info("Gold Build notebook completed successfully.")
