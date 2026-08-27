"""
tests/silver/test_dq_spikes.py

Proof that DQ Rule 7 works: implausible spike detection.

Spike: audience_value > 5x rolling 7-day median for same property+platform+geography.
Spike rows stay in clean_df with _is_spike_flagged=True AND are written to quarantine.
Rows with no history (null rolling median) are NOT flagged.

Honest limitation documented: cannot fire on first ingestion run.
"""
import pytest
from pyspark.sql import Row
from datetime import date, timedelta
from jobs.silver.dq_rules import check_spikes, REASON_IMPLAUSIBLE_SPIKE

pytestmark = pytest.mark.databricks

def test_spike_flagged_and_kept_in_clean(spark):
    start_date = date(2024, 1, 1)
    rows = []
    for i in range(7):
        rows.append(Row(property_id="P1", platform="web", geography_id="US", event_date=start_date + timedelta(days=i), audience_value=100000))
    # Spike day
    rows.append(Row(property_id="P1", platform="web", geography_id="US", event_date=start_date + timedelta(days=7), audience_value=1000000))
    
    df = spark.createDataFrame(rows)
    clean_df, q_df = check_spikes(df, {})
    
    spike_row = clean_df.filter(clean_df.event_date == (start_date + timedelta(days=7))).first()
    assert spike_row["_is_spike_flagged"] is True
    
    assert q_df.count() == 1
    assert q_df.first()["_q_reason"] == REASON_IMPLAUSIBLE_SPIKE

def test_normal_value_not_flagged(spark):
    start_date = date(2024, 1, 1)
    rows = []
    for i in range(7):
        rows.append(Row(property_id="P1", platform="web", geography_id="US", event_date=start_date + timedelta(days=i), audience_value=100000))
    # Normal day (1.5x)
    rows.append(Row(property_id="P1", platform="web", geography_id="US", event_date=start_date + timedelta(days=7), audience_value=150000))
    
    df = spark.createDataFrame(rows)
    clean_df, q_df = check_spikes(df, {})
    
    normal_row = clean_df.filter(clean_df.event_date == (start_date + timedelta(days=7))).first()
    assert normal_row["_is_spike_flagged"] is False
    assert q_df.count() == 0

def test_no_history_not_flagged(spark):
    df = spark.createDataFrame([
        Row(property_id="P1", platform="web", geography_id="US", event_date=date(2024, 1, 1), audience_value=100000)
    ])
    clean_df, q_df = check_spikes(df, {})
    
    assert clean_df.first()["_is_spike_flagged"] is False
    assert q_df.count() == 0

def test_spike_threshold_is_5x(spark):
    start_date = date(2024, 1, 1)
    rows = []
    for i in range(7):
        rows.append(Row(property_id="P1", platform="web", geography_id="US", event_date=start_date + timedelta(days=i), audience_value=100))
        
    rows.append(Row(property_id="P1", platform="web", geography_id="US", event_date=start_date + timedelta(days=7), audience_value=500)) # exactly 5x
    rows.append(Row(property_id="P1", platform="web", geography_id="US", event_date=start_date + timedelta(days=8), audience_value=510)) # > 5x
    
    df = spark.createDataFrame(rows)
    clean_df, q_df = check_spikes(df, {})
    
    exactly_5x = clean_df.filter(clean_df.audience_value == 500).first()
    assert exactly_5x["_is_spike_flagged"] is False
    
    over_5x = clean_df.filter(clean_df.audience_value == 510).first()
    assert over_5x["_is_spike_flagged"] is True
