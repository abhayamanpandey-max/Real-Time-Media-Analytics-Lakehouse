# Semantic Layer — Question-to-Asset Mapping

## Purpose
Document which semantic view answers which business questions.
This is the reference for configuring Genie's example questions and instructions.

## Rule: Genie queries only these 3 views.
No other tables or views are accessible to Genie.

## View 1: sem_audience_rankings
| Example Question | Expected SQL pattern | Period filter needed? |
| :--- | :--- | :--- |
| Which property had the highest audience last month? | `SELECT property FROM sem_audience_rankings WHERE rank = 1` | Yes |
| What are the top 5 properties on Connected TV in the North Region? | `SELECT property, rank FROM sem_audience_rankings WHERE platform_code = 'connected_tv' AND region = 'North Region' ORDER BY rank LIMIT 5` | Yes |
| Show me the weekly rankings for web platform in Q1 2024 | `SELECT property, rank FROM sem_audience_rankings WHERE platform_code = 'web' AND period_type = 'WEEKLY'` | Yes |
| What share of total audience did Channel Alpha have in January 2024? | `SELECT audience_share_pct FROM sem_audience_rankings WHERE property = 'Channel Alpha'` | Yes |
| Who ranked second overall last week? | `SELECT property FROM sem_audience_rankings WHERE rank = 2 AND period_type = 'WEEKLY'` | Yes |

## View 2: sem_audience_profile
| Example Question | Expected SQL pattern | Period filter needed? |
| :--- | :--- | :--- |
| What is Channel Alpha's audience breakdown by platform this month? | `SELECT platform, audience_share_within_property_pct FROM sem_audience_profile WHERE property = 'Channel Alpha'` | Yes |
| Which platform drives the most audience for Stream Beta? | `SELECT platform FROM sem_audience_profile WHERE property = 'Stream Beta' ORDER BY total_audience DESC LIMIT 1` | Yes |
| What percentage of Vision Theta's audience comes from mobile? | `SELECT audience_share_within_property_pct FROM sem_audience_profile WHERE property = 'Vision Theta' AND platform_code = 'mobile'` | Yes |
| Show me the audience profile for Network Delta in January 2024 | `SELECT * FROM sem_audience_profile WHERE property = 'Network Delta'` | Yes |
| What was the peak viewership date for Studio Zeta on Connected TV? | `SELECT peak_date FROM sem_audience_profile WHERE property = 'Studio Zeta' AND platform_code = 'connected_tv'` | Yes |

## View 3: sem_cross_property_comparison
| Example Question | Expected SQL pattern | Period filter needed? |
| :--- | :--- | :--- |
| How does Channel Alpha compare to Stream Beta on web in January 2024? | `SELECT audience_index FROM sem_cross_property_comparison WHERE property_a = 'Channel Alpha' AND property_b = 'Stream Beta'` | Yes |
| Which property had more audience - Network Delta or Media Gamma - last month? | `SELECT CASE WHEN audience_index > 100 THEN property_a ELSE property_b END FROM sem_cross_property_comparison WHERE property_a = 'Network Delta' AND property_b = 'Media Gamma'` | Yes |
| Show me the audience index of Channel Alpha vs all other properties on Connected TV | `SELECT property_b, audience_index FROM sem_cross_property_comparison WHERE property_a = 'Channel Alpha'` | Yes |
| What is the rank of Stream Beta when Channel Alpha is rank 1? | `SELECT rank_b FROM sem_cross_property_comparison WHERE property_a = 'Channel Alpha' AND rank_a = 1 AND property_b = 'Stream Beta'` | Yes |
| Did Media Gamma perform better than Network Delta? | `SELECT audience_index > 100 FROM sem_cross_property_comparison WHERE property_a = 'Media Gamma' AND property_b = 'Network Delta'` | Yes |

## Column name rationale
- `report_period` -> `period`: Simplified to be more intuitive for business users.
- `report_period_type` -> `period_type`: Removed redundant "report_" prefix.
- `platform_display_name` -> `platform`: Business users typically mean the display name when asking for "platform".
- `geography_name` -> `region`: "Region" is a more common business term than "geography".
- `property_name` -> `property`: Matches standard terminology for "Media Property".
- `audience_rank` -> `rank`: Removed redundant "audience_" prefix.
- `category_display_name` -> `category`: Standardized display name to generic concept.
- `audience_within_property_pct` -> `audience_share_within_property_pct`: Clarified what the percentage represents.
- Excluded `_id` and internal keys: The semantic layer abstracts away implementation details so users do not query primary keys directly or mistake them for metrics. (Kept `property_id` for potential dashboard integrations but abstracted away most pipeline IDs).

## What NOT to expose in the semantic layer
- `_platinum_processed_at`: Internal data pipeline metadata; irrelevant to business queries and could cause confusion.
- Pipeline specific keys and audit columns.
