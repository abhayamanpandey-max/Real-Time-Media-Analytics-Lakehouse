# IMMUTABILITY CONTRACT: Bronze is append-only.
# Never use mode('overwrite') or execute DELETE/UPDATE on this table.
# If a row turns out to be bad, Silver rejects it to quarantine.
# The raw bronze record stays forever as audit evidence.
"""
ingestion/bronze_writer.py

Writes raw API event dicts to the Bronze Delta table.
Designed to run on Databricks (PySpark from Databricks Connect or cluster session).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

from pyspark.sql import functions as F

from config.loader import get_full_table_name
from ingestion.schemas import BRONZE_SCHEMA

logger = logging.getLogger(__name__)


def write_bronze(
    spark: "SparkSession",
    events: list[dict],
    config: dict,
    run_id: str,
    source_page: int = 0,
) -> int:
    """
    Write raw events to the Bronze Delta table.

    Args:
        spark: Active SparkSession (Databricks Connect or cluster session).
        events: List of raw event dicts from the API client.
        config: Loaded config dict.
        run_id: UUID string identifying this ingestion run (groups one batch).
        source_page: API page number this batch came from (for lineage).

    Returns:
        Number of rows written.

    IMPORTANT: Write mode is always 'append'. This function will raise
    ValueError if called with an empty events list to prevent empty appends.
    """
    if not events:
        raise ValueError("Cannot write empty events list to bronze.")

    for event in events:
        event["_source_api_page"] = source_page
        event["_bronze_run_id"] = run_id
        # _bronze_ingested_at will be added by spark as current_timestamp

    df = spark.createDataFrame(events, schema=BRONZE_SCHEMA)
    df = df.withColumn("_bronze_ingested_at", F.current_timestamp())

    full_table_name = get_full_table_name(config, "bronze", "bronze_events")
    
    df.write.format("delta").mode("append").saveAsTable(full_table_name)
    
    logger.info(f"Wrote {len(events)} rows to {full_table_name}")
    
    return len(events)
