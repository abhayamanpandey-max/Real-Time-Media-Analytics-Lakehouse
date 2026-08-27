"""
jobs/silver/quarantine.py

Writes rejected rows to the Silver quarantine Delta table.
Every row that fails a DQ check gets written here with a quarantine_reason.

Quarantine table: <catalog>.silver.audience_quarantine
Schema: all bronze columns + quarantine_reason (string) + quarantine_timestamp (timestamp)

IMPORTANT: The quarantine table uses APPEND mode. Rows are never deleted
from quarantine - it is a permanent audit log of all DQ failures.
"""

from pyspark.sql import SparkSession, DataFrame
import pyspark.sql.functions as F
import logging
from config.loader import get_full_table_name

logger = logging.getLogger(__name__)

def write_quarantine(
    spark: SparkSession,
    quarantine_df: DataFrame,
    config: dict,
    reason: str,
) -> int:
    """Append a batch of rejected rows to the quarantine Delta table.
    Adds quarantine_reason and quarantine_timestamp columns.
    Returns row count written (0 if quarantine_df is empty)."""
    
    count = quarantine_df.count()
    if count == 0:
        return 0

    df_to_write = quarantine_df \
        .withColumn("quarantine_reason", F.lit(reason)) \
        .withColumn("quarantine_timestamp", F.current_timestamp())

    table_name = get_full_table_name(config, 'silver', 'silver_quarantine')

    logger.info(f"Writing {count} rows to quarantine with reason {reason}")

    df_to_write.write \
        .format("delta") \
        .mode("append") \
        .saveAsTable(table_name)
        
    return count

def get_quarantine_summary(spark: SparkSession, config: dict) -> DataFrame:
    """Read quarantine table and return counts by reason code. Useful for monitoring."""
    table_name = get_full_table_name(config, 'silver', 'silver_quarantine')
    return spark.read.table(table_name).groupBy("quarantine_reason").count()
