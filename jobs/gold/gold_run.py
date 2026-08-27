"""
jobs/gold/gold_run.py

Orchestrates the full Gold layer build.
Runs all dimension and fact jobs in dependency order.
This script is what the Databricks Workflow runs for the Gold layer.

To run:
  LAKEHOUSE_ENV=dev python -m jobs.gold.gold_run
"""
import os
from pyspark.sql import SparkSession
from config.loader import load_config
from jobs.gold.dim_platform import build_dim_platform
from jobs.gold.dim_category import build_dim_category
from jobs.gold.dim_property import build_dim_property
from jobs.gold.dim_geography import build_dim_geography
from jobs.gold.dim_date import build_dim_date
from jobs.gold.fact_audience import build_fact_audience

def main():
    spark = SparkSession.builder.appName("GoldLayerBuild").getOrCreate()
    env = os.environ.get("LAKEHOUSE_ENV", "dev")
    config = load_config(env)
    
    print("Building Gold Layer...")
    
    print("1. dim_platform...")
    build_dim_platform(spark, config)
    
    print("2. dim_category...")
    build_dim_category(spark, config)
    
    print("3. dim_property...")
    build_dim_property(spark, config)
    
    print("4. dim_geography...")
    build_dim_geography(spark, config)
    
    print("5. dim_date...")
    build_dim_date(spark, config)
    
    print("6. fact_audience...")
    build_fact_audience(spark, config)
    
    print("Gold Layer build complete.")

if __name__ == "__main__":
    main()
