"""
ingestion/ingest_run.py

Main ingestion entrypoint. This script is what the Databricks Workflow runs.

Pipeline:
  1. Read config (LAKEHOUSE_ENV env var)
  2. Create Spark session via Databricks Connect
  3. Fetch all events from the API (paginated)
  4. Write each page batch to Bronze Delta table
  5. Log run summary

To run manually:
  LAKEHOUSE_ENV=dev python -m ingestion.ingest_run
"""

import logging
import os
import sys
import time
import uuid

from config.loader import load_config
from ingestion.api_client import fetch_all_events
from ingestion.bronze_writer import write_bronze

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_spark():
    try:
        from pyspark.sql import SparkSession
        return SparkSession.builder.appName("Bronze Ingestion").getOrCreate()
    except Exception:
        from databricks.connect import DatabricksSession
        return DatabricksSession.builder.getOrCreate()


def get_api_base_url(config: dict) -> str:
    # 1. Try environment variable
    env_url = os.environ.get("API_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    # 2. Try dbutils widget parameter
    try:
        from pyspark.dbutils import DBUtils
        spark = get_spark()
        dbutils = DBUtils(spark)
        param_url = dbutils.widgets.get("API_BASE_URL")
        if param_url:
            return param_url.rstrip("/")
    except Exception:
        pass

    # 3. Read config base_url
    config_url = config.get("api", {}).get("base_url", "")
    if config_url and "YOUR_EC2_PUBLIC_IP" not in config_url and "localhost" not in config_url:
        return config_url.rstrip("/")

    # Default fallback to live EC2 host
    return "http://13.201.159.64:8000"


def main():
    try:
        start_time = time.time()
        env = os.environ.get("LAKEHOUSE_ENV", "dev")
        config = load_config(env)
        config["api"]["base_url"] = get_api_base_url(config)

        spark = get_spark()
        run_id = str(uuid.uuid4())

        logger.info(f"Starting ingestion run_id={run_id} env={env} api_base_url={config['api']['base_url']}")

        events = fetch_all_events(config)
        rows_written = 0

        if events:
            rows_written = write_bronze(spark, events, config, run_id)

        duration_seconds = time.time() - start_time
        logger.info(f"Run summary: run_id={run_id} env={env} events_fetched={len(events)} rows_written={rows_written} duration_seconds={duration_seconds:.2f}")

        sys.exit(0)
    except Exception as e:
        logger.error(f"Ingestion run failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
