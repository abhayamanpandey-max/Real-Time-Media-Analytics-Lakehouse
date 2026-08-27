"""
jobs/platinum/platinum_run.py

Orchestrates the full Platinum layer build.
Runs both analytical mart jobs.
This script is what the Databricks Workflow runs for the Platinum layer.

Dependency: Gold layer must be current before running this.

To run:
  LAKEHOUSE_ENV=dev python -m jobs.platinum.platinum_run
"""
from pyspark.sql import SparkSession
import logging
import sys
from config.loader import load_config
from jobs.platinum.mart_audience_rankings import build_mart_audience_rankings
from jobs.platinum.mart_audience_profile import build_mart_audience_profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    spark = SparkSession.builder.appName("Platinum Layer Run").getOrCreate()
    config = load_config()
    
    logger.info("Starting Platinum layer build...")
    
    try:
        rankings_count = build_mart_audience_rankings(spark, config)
        logger.info(f"Successfully built mart_audience_rankings: {rankings_count} rows.")
        
        profile_count = build_mart_audience_profile(spark, config)
        logger.info(f"Successfully built mart_audience_profile: {profile_count} rows.")
        
        logger.info("Platinum layer build completed successfully.")
        
    except Exception as e:
        logger.error(f"Error building Platinum layer: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
