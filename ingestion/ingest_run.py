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

def get_spark():
    try:
        from pyspark.sql import SparkSession
        return SparkSession.builder.appName("Bronze Ingestion").getOrCreate()
    except Exception:
        from databricks.connect import DatabricksSession
        return DatabricksSession.builder.getOrCreate()


def main():
    try:
        start_time = time.time()
        env = os.environ.get("LAKEHOUSE_ENV", "dev")
        config = load_config(env)

        spark = get_spark()
        run_id = str(uuid.uuid4())

        logger.info(f"Starting ingestion run_id={run_id} env={env}")

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
