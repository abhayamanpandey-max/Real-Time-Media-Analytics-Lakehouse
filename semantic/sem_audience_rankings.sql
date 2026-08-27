-- semantic/sem_audience_rankings.sql
--
-- Semantic view: sem_audience_rankings
-- Source: ${catalog}.platinum.mart_audience_rankings
--
-- PURPOSE: Property audience rankings by period, platform, and region.
-- This view is designed for Genie and business users ONLY.
-- Do not add technical columns, internal IDs, or processing metadata here.
--
-- GRAIN: period x period_type x platform x region x property
-- One row = one property's ranked audience position in one segment.
--
-- GENIE USE CASES ANSWERED BY THIS VIEW:
--   - "Which property had the highest audience last month?"
--   - "What are the top 5 properties on Connected TV in the North Region?"
--   - "Show me the weekly rankings for web platform in Q1 2024"
--   - "What share of total audience did Channel Alpha have in January 2024?"
--
-- COLUMN GUIDE:
--   period        : Time period. Format 'YYYY-MM' (monthly) or 'YYYY-WNN' (weekly)
--   period_type   : 'MONTHLY' or 'WEEKLY'
--   platform      : Human-readable platform name (e.g. 'Connected TV', 'Web Browser')
--   platform_code : Machine-readable platform code (e.g. 'connected_tv', 'web')
--   region        : Geography name (e.g. 'North Region', 'Metro Core')
--   property      : Media property name (e.g. 'Channel Alpha')
--   total_audience: Total measured audience for this property in this segment and period
--   rank          : Audience rank (1 = highest audience) within this period+platform+region
--   audience_share_pct: This property's audience as % of all properties in this segment

CREATE OR REPLACE VIEW ${catalog}.semantic.sem_audience_rankings AS
SELECT
    report_period           AS period,
    report_period_type      AS period_type,
    platform_display_name   AS platform,
    platform                AS platform_code,
    geography_name          AS region,
    property_name           AS property,
    property_id,
    total_audience,
    audience_rank           AS rank,
    ROUND(audience_share_pct, 4) AS audience_share_pct
FROM ${catalog}.platinum.mart_audience_rankings;
