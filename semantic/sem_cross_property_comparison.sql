-- semantic/sem_cross_property_comparison.sql
--
-- Semantic view: sem_cross_property_comparison
-- Source: ${catalog}.platinum.mart_audience_rankings
--
-- PURPOSE: Compare audience performance pairwise between properties.
-- This view is designed for Genie and business users ONLY.
-- Do not add technical columns, internal IDs, or processing metadata here.
--
-- GRAIN: period x period_type x platform x region x property_a x property_b
-- One row = a comparison between two properties in a specific segment.
--
-- HONEST LIMITATION: This view generates all pairwise combinations of properties within each segment. Row count grows quadratically with number of properties. With 20 properties, each segment will have up to 190 pairs (20 choose 2). Monitor size when adding properties.
--
-- GENIE USE CASES ANSWERED BY THIS VIEW:
--   - "How does Channel Alpha compare to Stream Beta on web in January 2024?"
--   - "Which property had more audience - Network Delta or Media Gamma - last month?"
--   - "Show me the audience index of Channel Alpha vs all other properties on Connected TV"
--
-- COLUMN GUIDE:
--   period        : Time period. Format 'YYYY-MM' (monthly) or 'YYYY-WNN' (weekly)
--   period_type   : 'MONTHLY' or 'WEEKLY'
--   platform      : Human-readable platform name
--   region        : Geography name
--   property_a    : First media property name
--   total_audience_a: Total audience for property_a
--   rank_a        : Audience rank for property_a
--   property_b    : Second media property name
--   total_audience_b: Total audience for property_b
--   rank_b        : Audience rank for property_b
--   audience_index: audience_index > 100: property_a has more audience than property_b. audience_index = 100: equal. audience_index < 100: property_a has less audience. Null if property_b has 0 audience.

CREATE OR REPLACE VIEW ${catalog}.semantic.sem_cross_property_comparison AS
SELECT
    a.report_period           AS period,
    a.report_period_type      AS period_type,
    a.platform_display_name   AS platform,
    a.geography_name          AS region,
    a.property_name           AS property_a,
    a.total_audience          AS total_audience_a,
    a.audience_rank           AS rank_a,
    b.property_name           AS property_b,
    b.total_audience          AS total_audience_b,
    b.audience_rank           AS rank_b,
    (a.total_audience * 100.0 / NULLIF(b.total_audience, 0)) AS audience_index
FROM ${catalog}.platinum.mart_audience_rankings a
INNER JOIN ${catalog}.platinum.mart_audience_rankings b
  ON a.report_period = b.report_period
 AND a.report_period_type = b.report_period_type
 AND a.platform = b.platform
 AND a.geography_name = b.geography_name
 AND a.property_name < b.property_name;
