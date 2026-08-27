"""
jobs/silver/silver_transform.py

Silver layer transformation job.
Runs on Databricks (use DatabricksSession or cluster session).

Pipeline:
  1. Read from Bronze Delta table
  2. Apply DQ rules in sequence (each returns clean_df + quarantine_df)
  3. Accumulate all quarantine rows
  4. Write clean rows to Silver Delta table (MERGE/overwrite by date partition)
  5. Write all quarantine rows to Quarantine table
  6. Log run summary

To run:
  LAKEHOUSE_ENV=dev python -m jobs.silver.silver_transform
"""

import sys
import logging
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

try:
    from config.loader import load_config, get_full_table_name
except ImportError:
    def load_config(): return {"catalog": "hive_metastore"}
    def get_full_table_name(config, schema, table): return f"{config['catalog']}.{schema}.{table}"

from jobs.silver.dq_rules import (
    check_casts, check_missing_required, check_normalisation_and_allowed_values,
    check_invalid_values, check_duplicates, check_spikes, check_referential_integrity
)
from jobs.silver.quarantine import write_quarantine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def run():
    try:
        from databricks.connect import DatabricksSession
        spark = DatabricksSession.builder.getOrCreate()
    except ImportError:
        spark = SparkSession.builder.appName("SilverTransform").getOrCreate()

    config = load_config()
    
    bronze_table = get_full_table_name(config, 'bronze', 'audience_bronze')
    silver_table = get_full_table_name(config, 'silver', 'audience_silver')
    
    try:
        df = spark.read.table(bronze_table)
    except Exception as e:
        logger.error(f"Failed to read bronze table {bronze_table}: {e}")
        sys.exit(1)
        
    initial_count = df.count()
    logger.info(f"Read {initial_count} rows from Bronze.")
    
    rules = [
        check_casts,
        check_missing_required,
        check_normalisation_and_allowed_values,
        check_invalid_values,
        check_duplicates,
        check_spikes,
        check_referential_integrity
    ]
    
    all_quarantine_dfs = []
    
    for rule in rules:
        df, q_df = rule(df, config)
        if "_q_reason" in q_df.columns:
            # write_quarantine expects a reason parameter, but our dq_rules return the reason in the df.
            # We can map it by taking distinct reasons and writing them, or adapting quarantine.py.
            # Let's collect them all and write them at the end.
            all_quarantine_dfs.append(q_df)
            
    df = df.withColumn("_silver_processed_at", F.current_timestamp())
    
    clean_count = df.count()
    logger.info(f"Clean rows ready for Silver: {clean_count}")
    
    # Write clean data
    df.write.format("delta").mode("append").partitionBy("event_date").saveAsTable(silver_table)
    
    # Process quarantine
    total_q_count = 0
    if all_quarantine_dfs:
        combined_q = all_quarantine_dfs[0]
        for q in all_quarantine_dfs[1:]:
            combined_q = combined_q.unionByName(q, allowMissingColumns=True)
            
        q_count = combined_q.count()
        if q_count > 0:
            # We must call write_quarantine. write_quarantine takes reason as param.
            # We have reason in _q_reason column. We can adapt by writing per distinct reason.
            distinct_reasons = [r["_q_reason"] for r in combined_q.select("_q_reason").distinct().collect()]
            for reason in distinct_reasons:
                q_subset = combined_q.filter(F.col("_q_reason") == reason).drop("_q_reason")
                write_quarantine(spark, q_subset, config, reason)
                
            total_q_count = q_count
            
            # Log breakdown
            logger.info("Quarantine breakdown:")
            breakdown = combined_q.groupBy("_q_reason").count().collect()
            for row in breakdown:
                logger.info(f"  {row['_q_reason']}: {row['count']}")
                
    logger.info(f"Run complete. Read: {initial_count}, Clean: {clean_count}, Quarantined: {total_q_count}")
    sys.exit(0)

if __name__ == "__main__":
    run()
