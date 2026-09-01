# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🧠 05 Semantic Views Notebook
# MAGIC Thin entrypoint for the Semantic layer.
# MAGIC Reads parameters from dbutils.widgets and runs the three semantic/*.sql files via spark.sql().

# COMMAND ----------
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("05_semantic_views")

try:
    dbutils.widgets.text("env", "dev", "LAKEHOUSE_ENV")
except Exception:
    pass

try:
    env = dbutils.widgets.get("env")
except Exception:
    env = os.environ.get("LAKEHOUSE_ENV", "dev")

os.environ["LAKEHOUSE_ENV"] = env

from config.loader import load_config
from pyspark.sql import SparkSession

try:
    from databricks.connect import DatabricksSession
    spark = DatabricksSession.builder.getOrCreate()
except Exception:
    spark = SparkSession.builder.appName("SemanticViews").getOrCreate()

config = load_config(env)
catalog = config["databricks"]["catalog"]

logger.info(f"Starting Semantic Views notebook [env={env}, catalog={catalog}]")

# Ensure semantic schema exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.semantic")

# Find semantic SQL directory
possible_dirs = [
    Path(__file__).parent.parent / "semantic",
    Path("semantic"),
    Path("../semantic"),
    Path("/Workspace") / "semantic",
]

sql_dir = None
for d in possible_dirs:
    if d.exists() and d.is_dir():
        sql_dir = d
        break

if not sql_dir:
    raise FileNotFoundError("Could not find 'semantic' SQL directory.")

sql_files = [
    "sem_audience_profile.sql",
    "sem_audience_rankings.sql",
    "sem_cross_property_comparison.sql",
]

for sql_file_name in sql_files:
    sql_file_path = sql_dir / sql_file_name
    if not sql_file_path.exists():
        raise FileNotFoundError(f"Semantic SQL file not found: {sql_file_path}")

    with open(sql_file_path, "r", encoding="utf-8") as f:
        raw_sql = f.read()

    # Substitute ${catalog} token
    formatted_sql = raw_sql.replace("${catalog}", catalog)
    
    logger.info(f"Executing semantic view SQL: {sql_file_name}...")
    spark.sql(formatted_sql)

logger.info(f"Semantic Views notebook completed successfully for catalog '{catalog}'.")
