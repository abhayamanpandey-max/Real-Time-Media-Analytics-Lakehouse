# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC # 🧠 Layer 6: Semantic Layer & Databricks Genie AI Views
# MAGIC **Real-Time Media Analytics Lakehouse**
# MAGIC 
# MAGIC Exposes 3 curated, business-friendly SQL views that restrict Databricks Genie's query surface area to guarantee 100% NL-to-SQL accuracy.

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS analytics_dev.semantic;

# COMMAND ----------
# MAGIC %md
# MAGIC ### View 1: `sem_audience_rankings`
# MAGIC Answers ranking, market share, and leaderboard prompts across media properties.

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW analytics_dev.semantic.sem_audience_rankings AS
# MAGIC SELECT 
# MAGIC     report_period_type AS period_type,
# MAGIC     report_period AS period,
# MAGIC     property_name AS property,
# MAGIC     total_audience,
# MAGIC     audience_rank,
# MAGIC     audience_share_pct
# MAGIC FROM analytics_dev.platinum.mart_audience_rankings;

# COMMAND ----------
# MAGIC %md
# MAGIC ### View 2: `sem_audience_profile`
# MAGIC Answers platform composition, category, and regional audience breakdown prompts.

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW analytics_dev.semantic.sem_audience_profile AS
# MAGIC SELECT 
# MAGIC     report_period_type AS period_type,
# MAGIC     report_period AS period,
# MAGIC     property_name AS property,
# MAGIC     platform_name AS platform,
# MAGIC     category_name AS category,
# MAGIC     geography_name AS region,
# MAGIC     total_audience,
# MAGIC     peak_audience_date
# MAGIC FROM analytics_dev.platinum.mart_audience_profile;

# COMMAND ----------
# MAGIC %md
# MAGIC ### View 3: `sem_cross_property_comparison`
# MAGIC Answers head-to-head comparison and audience index prompts between media properties.

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW analytics_dev.semantic.sem_cross_property_comparison AS
# MAGIC SELECT 
# MAGIC     a.report_period_type AS period_type,
# MAGIC     a.report_period AS period,
# MAGIC     a.property_name AS property_a,
# MAGIC     b.property_name AS property_b,
# MAGIC     a.platform_name AS platform,
# MAGIC     a.geography_name AS region,
# MAGIC     a.total_audience AS audience_property_a,
# MAGIC     b.total_audience AS audience_property_b,
# MAGIC     ROUND(a.total_audience / NULLIF(b.total_audience, 0), 2) AS audience_index_ratio
# MAGIC FROM analytics_dev.platinum.mart_audience_profile a
# MAGIC JOIN analytics_dev.platinum.mart_audience_profile b
# MAGIC   ON a.report_period_type = b.report_period_type
# MAGIC  AND a.report_period = b.report_period
# MAGIC  AND a.platform_name = b.platform_name
# MAGIC  AND a.geography_name = b.geography_name
# MAGIC  AND a.category_name = b.category_name
# MAGIC  AND a.property_name != b.property_name;

# COMMAND ----------
# MAGIC %md
# MAGIC ### Test Query on Semantic View

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Test query for Genie AI prompt: "Which property had the highest audience last quarter?"
# MAGIC SELECT 
# MAGIC     property,
# MAGIC     SUM(total_audience) AS total_quarterly_audience,
# MAGIC     ROUND(AVG(audience_share_pct), 2) AS avg_share_pct
# MAGIC FROM analytics_dev.semantic.sem_audience_rankings
# MAGIC WHERE period_type = 'QUARTERLY' AND period = '2026-Q2'
# MAGIC GROUP BY property
# MAGIC ORDER BY total_quarterly_audience DESC
# MAGIC LIMIT 1;
