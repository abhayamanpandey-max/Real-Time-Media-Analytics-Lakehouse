# Media/Audience Analytics Lakehouse — Build Brief for Codex / Antigravity
## v2 — updated architecture

This is my own independent project — a generalized, end-to-end streaming
analytics lakehouse with natural-language querying via Databricks Genie.
It is NOT tied to any specific client or real-world data source. Use a
generic media/audience analytics domain (properties, audience, platform,
geography, category) — do not use household/TV-panel-specific concepts.

I do not have access to any proprietary data source. This build uses a
synthetic, swappable data source so the pipeline is provably correct on
its own.

---

## 1. Problem this project solves

Business users want to ask questions in plain language ("which property
had the highest audience last quarter?") but getting a CORRECT answer
secretly depends on consistent definitions of entities, metrics, time
periods, grain, and aggregation rules. Inconsistent definitions produce
inconsistent answers and erode trust. This project's job is to make that
gap disappear — not just wire up an NL interface, but make the data
underneath it trustworthy enough that the NL interface can be accurate.

## 2. Final architecture (six layers — do not collapse this back to three)

Single ingestion flow, in order:

1. **Python generator script** — produces synthetic audience events
   (property, geography, platform, category, date, audience_value)
2. **Kafka** — dev-only stream, fed by the generator
3. **Mock API layer** (FastAPI) — reads off the Kafka topic, re-serves it
   as a REST API shaped like a plausible real-world analytics API
   (paginated, bearer-token auth, JSON). This exists so the ingestion
   code never has to change when a real API is swapped in later.
4. **PySpark ingestion job** — scheduled via Databricks Workflows, pulls
   from the API (mock now, real later — config-driven, same code path)
5. **Bronze layer** (Delta) — raw ingest, append-only, minimal
   transformation, UNCHANGED once written (do not mutate bronze)
6. **Silver layer** — cleaned, standardized, deduplicated. Data quality
   rules only — no business logic, no aggregation, no Genie-specific
   shaping. (See section 4.)
7. **Gold layer** — business-focused dimensional model: a handful of
   tables with clear business meaning, built with PySpark / Databricks
   SQL only (no dbt — hard constraint). This is where dimensions and
   facts live, and where related raw entities get joined into
   business-meaningful tables. (See section 3.)
8. **Platinum layer** — analytical marts. Pre-aggregated, purpose-built
   tables for the specific questions the business actually asks (e.g.
   rankings, propensity/index-style comparative metrics). Built from
   Gold, not from Silver directly.
9. **Semantic layer** — 2-3 GOVERNED, Genie-facing assets only.
   Business-friendly column names, only the fields a business user's
   question would ever need, nothing technical. This is intentionally
   the ONLY layer Genie is allowed to query. The goal is to keep Genie's
   discovery surface small and unambiguous — this is the main lever for
   answer accuracy, more than any prompt engineering on Genie itself.
10. **Databricks Genie** — reads only from the semantic layer
11. **Business user** — asks a question, gets a validated answer

Orchestration: Databricks Workflows. Deployment: Databricks Asset
Bundles (`databricks.yml`), INCLUDING a properly filled-in
`resources/genie.yml` defining the Genie space as code — do not leave
this as a placeholder/empty file. Version control: Git.

**Explicitly excluded:** dbt, Airflow (unless there's a concrete reason
ingestion needs to reach outside Databricks — flag it as a question
rather than assuming), any tool not in this list.

## 3. Gold layer — star schema requirements

At minimum:
- `dim_property`, `dim_geography`, `dim_platform`, `dim_category`,
  `dim_date`
- `fact_audience` at an explicit, documented grain (confirm the real
  grain against the silver data — don't assume — likely property × date
  × platform × geography)

Document the grain of every gold and platinum table directly in the code
as a comment, the way a senior engineer's reference implementation I
reviewed does it — e.g. `# Grain: report_period_id + market_id +
station_id` — this made their design far easier to reason about, keep
that discipline here.

Every metric (audience, reach, growth, share, ranking) gets ONE written
definition, documented alongside the model, never reimplemented
differently in different queries.

## 4. Silver layer data quality rules (implement all)

- Missing values: hard-drop rows missing `property_id` or `event_date`;
  soft-log rows missing `geography_id`
- Duplicates: dedup on `(property_id, event_date, platform,
  geography_id)` — document why this is the natural key
- Invalid values: hard-drop negative `audience_value`; soft-log
  implausible spikes, don't auto-drop
- Inconsistent values: normalize casing/whitespace on `platform` and
  `category` BEFORE validating against an allowed value set
- Type differences: explicit casts on ingest, fail loudly on cast
  failure rather than silently nulling
- Referential integrity: every `property_id` downstream must exist in
  `dim_property` — route violations to quarantine, never let joins
  silently drop rows with no trace
- Quarantine table: every rejected row goes to a
  `silver_quarantine` table with a `quarantine_reason` column

## 5. Platinum layer — analytical marts

Design 1-2 marts that answer the platform's core use cases directly
(e.g. a ranking/comparison mart, an audience-profile mart). Each should:
- Be built from Gold tables, joined and pre-aggregated to exactly the
  shape a business question needs
- Have an explicit, documented grain
- Avoid being a dumping ground — purpose-built for specific question
  patterns, not "everything joined together"

## 6. Semantic layer — the Genie-facing layer

- Exactly 2-3 assets, built from Platinum, not from Gold or Silver
  directly
- Business-friendly column names (no `_id` suffixes where a name will
  do, no technical jargon)
- Genie's configured instructions/example questions should map directly
  to these assets — write out the mapping explicitly (which questions
  map to which semantic asset) as documentation

## 7. Genie validation framework

Do not target "100% accuracy" — that's not an honest or achievable goal
for any NL-to-SQL system. Instead build:
- A test suite of ~20-30 business questions with known-correct expected
  answers, covering the platform's core use cases
- Multiple phrasings of the same question, to test consistency, not
  just correctness
- An automated comparison of Genie's answer + generated SQL against
  expected results, logging pass/fail and the actual query used
- A regression check to re-run whenever the semantic layer or Genie's
  instructions change
- Track accuracy as a measurable, improving number over time — this is
  the honest framing for the meeting and the README

## 8. What I need from you

1. Propose a full implementation plan and file/folder structure first.
   Ask clarifying questions on anything ambiguous before writing code —
   especially grain, key definitions, and allowed value sets.
2. Build incrementally, layer by layer, each one runnable and testable
   before moving to the next: generator → Kafka → mock API → PySpark
   ingestion → bronze → silver (with tests) → gold → platinum → semantic
   → genie.yml → validation harness.
3. Write tests for the section 4 data quality rules — I want proof each
   rule works, not just trust that it does.
4. Config-driven dev/prod split (API base URL, auth) so swapping to a
   real data source later is a config change, not a rewrite.
5. Generate a professional, portfolio-ready `README.md` reflecting this
   architecture, once the pipeline is scaffolded.
6. Flag any point where full coverage isn't realistic, or where a design
   decision trades off completeness for correctness — tell me the honest
   limitation rather than hiding it.
