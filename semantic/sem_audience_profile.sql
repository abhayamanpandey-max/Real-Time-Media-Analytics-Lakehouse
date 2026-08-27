-- semantic/sem_audience_profile.sql
--
-- Semantic view: sem_audience_profile
-- Source: ${catalog}.platinum.mart_audience_profile
--
-- PURPOSE: Property audience profile by category, platform, and region.
-- This view is designed for Genie and business users ONLY.
-- Do not add technical columns, internal IDs, or processing metadata here.
--
-- GRAIN: property x period x period_type x platform x region x category
-- One row = one property's audience profile segment in a given period.
--
-- GENIE USE CASES ANSWERED BY THIS VIEW:
--   - "What is Channel Alpha's audience breakdown by platform this month?"
--   - "Which platform drives the most audience for Stream Beta?"
--   - "What percentage of Vision Theta's audience comes from mobile?"
--   - "Show me the audience profile for Network Delta in January 2024"
--   - "What was the peak viewership date for Studio Zeta on Connected TV?"
--
-- COLUMN GUIDE:
--   property      : Media property name (e.g. 'Channel Alpha')
--   property_id   : Media property ID
--   period        : Time period. Format 'YYYY-MM' (monthly) or 'YYYY-WNN' (weekly)
--   period_type   : 'MONTHLY' or 'WEEKLY'
--   platform      : Human-readable platform name (e.g. 'Connected TV', 'Web Browser')
--   platform_code : Machine-readable platform code (e.g. 'connected_tv', 'web')
--   region        : Geography name (e.g. 'North Region', 'Metro Core')
--   category      : Audience category display name
--   total_audience: Total measured audience for this property in this segment and period
--   audience_share_within_property_pct: Audience as % of total property audience
--   peak_date     : Date of peak viewership

CREATE OR REPLACE VIEW ${catalog}.semantic.sem_audience_profile AS
SELECT
    property_name           AS property,
    property_id             AS property_id,
    report_period           AS period,
    report_period_type      AS period_type,
    platform_display_name   AS platform,
    platform                AS platform_code,
    geography_name          AS region,
    category_display_name   AS category,
    total_audience,
    ROUND(audience_within_property_pct, 4) AS audience_share_within_property_pct,
    peak_date
FROM ${catalog}.platinum.mart_audience_profile;
