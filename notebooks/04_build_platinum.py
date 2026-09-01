# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 💎 04 Build Platinum Notebook
# MAGIC Thin entrypoint for the Platinum analytical marts layer.
# MAGIC Reads parameters from dbutils.widgets and invokes jobs.platinum.platinum_run.main().

# COMMAND ----------
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("04_build_platinum")

try:
    dbutils.widgets.text("env", "dev", "LAKEHOUSE_ENV")
except Exception:
    pass

try:
    env = dbutils.widgets.get("env")
except Exception:
    env = os.environ.get("LAKEHOUSE_ENV", "dev")

os.environ["LAKEHOUSE_ENV"] = env

logger.info(f"Starting Platinum Build notebook [env={env}]")

from jobs.platinum import platinum_run

try:
    platinum_run.main()
except SystemExit as e:
    if e.code != 0:
        raise RuntimeError(f"Platinum build failed with exit code {e.code}")

logger.info("Platinum Build notebook completed successfully.")
