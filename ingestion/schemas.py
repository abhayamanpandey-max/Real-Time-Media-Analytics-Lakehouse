"""
ingestion/schemas.py

PySpark schema definitions for the Bronze layer.
Bronze is append-only and NEVER mutated after write.

The bronze schema stores raw API event fields as received,
plus three ingestion metadata columns added by bronze_writer.
Failed type coercions surface in Silver, not here - bronze stores
fields as permissive types where possible.
"""
from __future__ import annotations

from pyspark.sql.types import (
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Bronze Delta table schema.
# Mirrors AudienceEvent fields exactly, plus three ingestion metadata columns.
# Do NOT add derived or computed fields to bronze.
BRONZE_SCHEMA = StructType([
    # ── Event fields (as-received from API) ────────────────────────────────
    StructField("event_id",            StringType(),    nullable=False),
    StructField("property_id",         StringType(),    nullable=True),  # nullable: DQ enforced in Silver
    StructField("property_name",       StringType(),    nullable=True),
    StructField("geography_id",        StringType(),    nullable=True),
    StructField("geography_name",      StringType(),    nullable=True),
    StructField("platform",            StringType(),    nullable=True),
    StructField("category",            StringType(),    nullable=True),
    StructField("event_date",          StringType(),    nullable=True),  # String; cast to Date in Silver
    StructField("audience_value",      LongType(),      nullable=True),  # nullable: DQ enforced in Silver
    StructField("ingested_at",         StringType(),    nullable=True),
    # ── Ingestion metadata (added by bronze_writer) ─────────────────────────
    StructField("_source_api_page",    IntegerType(),   nullable=False),
    StructField("_bronze_ingested_at", TimestampType(), nullable=False),
    StructField("_bronze_run_id",      StringType(),    nullable=False),
])
