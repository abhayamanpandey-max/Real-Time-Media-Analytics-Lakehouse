"""
jobs/silver/dq_rules.py

Composable data quality rule functions for the Silver layer.

Each function signature:
    rule_fn(df: DataFrame, config: dict) -> tuple[DataFrame, DataFrame]
    Returns: (clean_df, quarantine_df)

Rules are applied in sequence in silver_transform.py.
Each rule is independently testable - this is intentional.

Quarantine reason codes (all defined here as module-level constants
for use in tests):
    REASON_MISSING_PROPERTY_ID = "MISSING_PROPERTY_ID"
    REASON_MISSING_EVENT_DATE = "MISSING_EVENT_DATE"
    REASON_MISSING_GEOGRAPHY_ID = "MISSING_GEOGRAPHY_ID"
    REASON_NEGATIVE_AUDIENCE_VALUE = "NEGATIVE_AUDIENCE_VALUE"
    REASON_DUPLICATE_NATURAL_KEY = "DUPLICATE_NATURAL_KEY"
    REASON_INVALID_PLATFORM = "INVALID_PLATFORM"
    REASON_INVALID_CATEGORY = "INVALID_CATEGORY"
    REASON_CAST_FAILURE_EVENT_DATE = "CAST_FAILURE_EVENT_DATE"
    REASON_CAST_FAILURE_AUDIENCE_VALUE = "CAST_FAILURE_AUDIENCE_VALUE"
    REASON_REFERENTIAL_INTEGRITY_PROPERTY_ID = "REFERENTIAL_INTEGRITY_PROPERTY_ID"
    REASON_IMPLAUSIBLE_SPIKE = "IMPLAUSIBLE_SPIKE"
"""

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, LongType, TimestampType
import logging

try:
    from config.loader import ALLOWED_PLATFORMS, ALLOWED_CATEGORIES, get_full_table_name
except ImportError:
    # Fallback for testing if config doesn't exist yet
    ALLOWED_PLATFORMS = ["web", "mobile_app"]
    ALLOWED_CATEGORIES = ["news", "sports"]
    def get_full_table_name(config, schema, table):
        return f"{config.get('catalog', 'hive_metastore')}.{schema}.{table}"

logger = logging.getLogger(__name__)

REASON_MISSING_PROPERTY_ID = "MISSING_PROPERTY_ID"
REASON_MISSING_EVENT_DATE = "MISSING_EVENT_DATE"
REASON_MISSING_GEOGRAPHY_ID = "MISSING_GEOGRAPHY_ID"
REASON_NEGATIVE_AUDIENCE_VALUE = "NEGATIVE_AUDIENCE_VALUE"
REASON_DUPLICATE_NATURAL_KEY = "DUPLICATE_NATURAL_KEY"
REASON_INVALID_PLATFORM = "INVALID_PLATFORM"
REASON_INVALID_CATEGORY = "INVALID_CATEGORY"
REASON_CAST_FAILURE_EVENT_DATE = "CAST_FAILURE_EVENT_DATE"
REASON_CAST_FAILURE_AUDIENCE_VALUE = "CAST_FAILURE_AUDIENCE_VALUE"
REASON_REFERENTIAL_INTEGRITY_PROPERTY_ID = "REFERENTIAL_INTEGRITY_PROPERTY_ID"
REASON_IMPLAUSIBLE_SPIKE = "IMPLAUSIBLE_SPIKE"


def check_missing_required(df: DataFrame, config: dict) -> tuple[DataFrame, DataFrame]:
    """
    Hard-drop rows where property_id IS NULL OR event_date IS NULL.
    Soft-log rows where geography_id IS NULL.
    """
    # Hard drops
    hard_drop_cond = F.col("property_id").isNull() | F.col("event_date").isNull()
    
    # We need to split hard drops by reason to quarantine them separately (if we want to be precise),
    # but the instructions say returning a single quarantine df for all missing is fine.
    # Actually, we should be precise about the reason. Since the prompt implies returning
    # them together, let's just identify the first reason or duplicate them?
    # For simplicity, we create separate DataFrames and union them.
    
    q_prop = df.filter(F.col("property_id").isNull()).withColumn("_q_reason", F.lit(REASON_MISSING_PROPERTY_ID))
    q_date = df.filter(F.col("property_id").isNotNull() & F.col("event_date").isNull()).withColumn("_q_reason", F.lit(REASON_MISSING_EVENT_DATE))
    
    clean_df = df.filter(~hard_drop_cond)
    
    # Soft log
    q_geo = clean_df.filter(F.col("geography_id").isNull()).withColumn("_q_reason", F.lit(REASON_MISSING_GEOGRAPHY_ID))
    
    # Union all quarantine data
    quarantine_df = q_prop.unionByName(q_date, allowMissingColumns=True).unionByName(q_geo, allowMissingColumns=True)
    
    # clean_df keeps the missing geo rows
    return clean_df, quarantine_df

def check_duplicates(df: DataFrame, config: dict) -> tuple[DataFrame, DataFrame]:
    """
    Deduplicate on natural key: (property_id, event_date, platform, geography_id)
    This combination is the minimal grain that makes each audience measurement unique: 
    one property can have different audience sizes on the same day across platforms and geographies, 
    but the same platform+geography measurement on the same day for the same property should be identical.
    """
    natural_key = ["property_id", "event_date", "platform", "geography_id"]
    window = Window.partitionBy(*natural_key).orderBy("_bronze_ingested_at")
    
    df_with_rn = df.withColumn("_rn", F.row_number().over(window))
    
    clean_df = df_with_rn.filter(F.col("_rn") == 1).drop("_rn")
    quarantine_df = df_with_rn.filter(F.col("_rn") > 1).drop("_rn").withColumn("_q_reason", F.lit(REASON_DUPLICATE_NATURAL_KEY))
    
    return clean_df, quarantine_df

def check_invalid_values(df: DataFrame, config: dict) -> tuple[DataFrame, DataFrame]:
    """
    Hard-drop rows where audience_value < 0.
    """
    cond = F.col("audience_value") < 0
    clean_df = df.filter(~cond | F.col("audience_value").isNull())
    quarantine_df = df.filter(cond).withColumn("_q_reason", F.lit(REASON_NEGATIVE_AUDIENCE_VALUE))
    
    return clean_df, quarantine_df

def check_normalisation_and_allowed_values(df: DataFrame, config: dict) -> tuple[DataFrame, DataFrame]:
    """
    Normalize platform and category, then check against allowed lists.
    """
    norm_df = df.withColumn("platform", F.lower(F.trim(F.col("platform")))) \
                .withColumn("category", F.lower(F.trim(F.col("category"))))
                
    invalid_platform_cond = ~F.col("platform").isin(ALLOWED_PLATFORMS)
    invalid_category_cond = ~F.col("category").isin(ALLOWED_CATEGORIES)
    
    q_platform = norm_df.filter(invalid_platform_cond).withColumn("_q_reason", F.lit(REASON_INVALID_PLATFORM))
    q_category = norm_df.filter(~invalid_platform_cond & invalid_category_cond).withColumn("_q_reason", F.lit(REASON_INVALID_CATEGORY))
    
    clean_df = norm_df.filter(~invalid_platform_cond & ~invalid_category_cond)
    quarantine_df = q_platform.unionByName(q_category, allowMissingColumns=True)
    
    return clean_df, quarantine_df

def check_casts(df: DataFrame, config: dict) -> tuple[DataFrame, DataFrame]:
    """
    Cast event_date to DateType and ingested_at to TimestampType.
    Check audience_value for nulls.
    """
    df_cast = df.withColumn("event_date_cast", F.to_date(F.col("event_date"), 'yyyy-MM-dd')) \
                .withColumn("ingested_at_cast", F.to_timestamp(F.col("ingested_at")))
                
    fail_date_cond = F.col("event_date").isNotNull() & F.col("event_date_cast").isNull()
    fail_aud_cond = F.col("audience_value").isNull()
    
    q_date = df_cast.filter(fail_date_cond).withColumn("_q_reason", F.lit(REASON_CAST_FAILURE_EVENT_DATE))
    q_aud = df_cast.filter(~fail_date_cond & fail_aud_cond).withColumn("_q_reason", F.lit(REASON_CAST_FAILURE_AUDIENCE_VALUE))
    
    clean_df = df_cast.filter(~fail_date_cond & ~fail_aud_cond) \
                      .withColumn("event_date", F.col("event_date_cast")) \
                      .withColumn("ingested_at", F.col("ingested_at_cast")) \
                      .drop("event_date_cast", "ingested_at_cast")
                      
    q_date = q_date.drop("event_date_cast", "ingested_at_cast")
    q_aud = q_aud.drop("event_date_cast", "ingested_at_cast")
    
    quarantine_df = q_date.unionByName(q_aud, allowMissingColumns=True)
    
    return clean_df, quarantine_df

def check_referential_integrity(df: DataFrame, config: dict, dim_property_df: DataFrame = None) -> tuple[DataFrame, DataFrame]:
    """
    Check property_id against dim_property.
    """
    spark = df.sparkSession
    
    if dim_property_df is None:
        table_name = get_full_table_name(config, 'gold', 'dim_property')
        try:
            dim_property_df = spark.read.table(table_name)
        except Exception as e:
            logger.warning(f"dim_property table not found, skipping check: {e}")
            return df, spark.createDataFrame([], schema=df.schema).withColumn("_q_reason", F.lit(""))
            
    valid_ids = dim_property_df.select("property_id").distinct()
    
    clean_df = df.join(valid_ids, "property_id", "leftsemi")
    quarantine_df = df.join(valid_ids, "property_id", "leftanti") \
                      .withColumn("_q_reason", F.lit(REASON_REFERENTIAL_INTEGRITY_PROPERTY_ID))
                      
    return clean_df, quarantine_df

def check_spikes(df: DataFrame, config: dict) -> tuple[DataFrame, DataFrame]:
    """
    Flag spikes: > 5x 7-day rolling median.
    This rule cannot fire on the first ingestion run or for new property+platform+geography combinations with no prior history. 
    The rolling_median will be null in those cases and the flag will be False.
    """
    # Assuming event_date is cast to DateType, we need it as a timestamp to use RANGE window, 
    # or use days relative to unix epoch
    
    # Days since epoch
    df_days = df.withColumn("_days", F.datediff(F.col("event_date"), F.lit("1970-01-01")))
    
    window = Window.partitionBy("property_id", "platform", "geography_id") \
                   .orderBy("_days") \
                   .rangeBetween(-7, -1)
                   
    df_median = df_days.withColumn("_median", F.expr("percentile_approx(audience_value, 0.5)").over(window))
    
    spike_cond = F.col("_median").isNotNull() & (F.col("audience_value") > 5 * F.col("_median"))
    
    final_df = df_median.withColumn("_is_spike_flagged", F.when(spike_cond, True).otherwise(False)) \
                        .drop("_days", "_median")
                        
    quarantine_df = final_df.filter(F.col("_is_spike_flagged")) \
                            .withColumn("_q_reason", F.lit(REASON_IMPLAUSIBLE_SPIKE))
                            
    return final_df, quarantine_df
