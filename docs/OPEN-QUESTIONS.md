# OGIP — Open requirement questions

Requirement unknowns that shape architecture choices but cannot be settled from inside the
repo — they need numbers or intent from the data consumers (DS/ML team) or the data owner.
Each entry records what we know, what is open, the **current default** (we build this until
told otherwise), and the **decision trigger** that reopens it. A settled entry graduates
into an [ADR](adr/) and is struck through here.

_Added 2026-07-17, alongside the scraping/R2 reprioritization ([ROADMAP](ROADMAP.md))._

## 1. Scraping requirements — and whether dlt/ingestr cover them

**Known.** Roughly half of the planned sources are scraped/parsed rather than clean APIs
(HLTB, Metacritic; regional price sweeps are API-shaped but volume-hostile). The landing
pattern is fixed: scrapers write to the Postgres `landing` schema, dlt loads landing → raw
Parquet ([ADR-0006](adr/ADR-0006-dlt-default-ingestion-postgres-landing.md) ·
[ADR-0014](adr/ADR-0014-resilient-scraping-concurrency.md)).

**Open.**

- How hostile are the real targets — JS-rendered pages? anti-bot (TLS fingerprinting,
  challenge walls)? Where on the escalation ladder (httpx → curl_cffi → Playwright) does
  each source sit?
- Required freshness/cadence per source, and page volume per refresh — this drives the
  concurrency budget and politeness limits.
- ToS/robots posture per source: what may be fetched, stored, and republished at all?
- Is plain **dlt** enough on the *fetch* side (its REST source / scrapy helper), or do
  heavy sources justify a dedicated framework? **ingestr is not a scraper** — its role
  stays loading/CDC (landing → lake), per the staged `comparisons/dlt-vs-ingestr.md`
  _(Phase 9)_.

**Current default.** [ADR-0014](adr/ADR-0014-resilient-scraping-concurrency.md): async
httpx with bounded per-domain concurrency inside `ScraperSource`; at-least-once fetch +
idempotent landing upsert; no Scrapy, no browser automation until a concrete source
demands it.

**Decision trigger.** First source that fails the httpx path (JS wall / bot wall) →
escalate per-source: curl_cffi, then Playwright. More than ~3 hostile sources on the
ladder → revisit Scrapy/managed alternatives as a fleet decision.

## 2. Data volume — today and growth (Iceberg/DuckLake? Trino/Spark?)

**Known.** Today the lake is sample-scale: the M0 slice runs single-node DuckDB over local
Parquet. The target is catalog-scale (~10⁵ games) × time series (reviews, prices, player
counts), which still fits a single beefy node for a long while.

**Open.**

- Actual volume now (GB, file counts, rows per source) and growth per refresh cadence.
- Rebuild budget: how long may a full rebuild take before incremental-only is mandatory?
- Concurrency: how many writers (parallel flows) and readers (DS sessions) touch the lake
  at once?

**Current default.** Plain Parquet + DuckDB
([ADR-0002](adr/ADR-0002-duckdb-analytical-engine.md) ·
[ADR-0003](adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md)); one writer per dataset;
R2 as cloud of record.

**Decision trigger** (any of):

- Hot lake beyond a few hundred GB, or full rebuild exceeding its window → **DuckLake or
  Iceberg** for snapshots/compaction/ACID (ADR-0003 already stages that comparison).
- Concurrent writers to one table, or DS demanding time travel → same.
- Joins spilling past one node, or several engines needing the same tables concurrently →
  **Trino** (federated SQL over the lake) before **Spark** (only if heavy Python/ML
  transforms must run *inside* the lake engine). Either is a consumer swap, not a lake
  rewrite — Parquet(/Iceberg) stays the contract.

## 3. Storage format & data-management tooling — FS / semantic / fast serving

**Known.** The product is **files** (ML-ready Parquet), not an app backend and not BI
([ADR-0009](adr/ADR-0009-ml-outputs-feature-store.md)). Feature store = SQL-as-FS
(`fs_*`); semantic definitions are engine-agnostic data in `spec/`
([spec-semantic-layer](../.ai/tasks/spec-semantic-layer.md)); frameworks live in
`experimental/` only.

**Open.**

- Does any consumer need **low-latency serving** (an app, an API, live dashboards)? Files
  answer batch DS; they do not answer 100-ms queries. If yes → a serving engine
  (**ClickHouse / StarRocks**) fed *from* the marts — never replacing the lake.
- Does any consumer need **online features** or stricter point-in-time training sets than
  SQL-as-FS provides? If yes → a dedicated FS tool (Feast/Featureform) — adoption analysis
  staged as `comparisons/feature-store-tools.md` _(Phase 9)_.
- Will non-SQL metric consumers (BI, self-serve) appear? If yes → a semantic engine
  (**Cube / MetricFlow**) reading the `spec/` semantic definitions; until then the
  definitions stay data and the engines stay demos.
- Table-format management (schema evolution, retention, compaction): at what point does
  hand-rolled Parquet hygiene justify DuckLake/Iceberg? (Ties to §2.)

**Current default.** Files + SQL-as-FS + spec-level semantics; no serving engine, no FS
framework, no semantic engine on the prod path.

**Decision trigger.** A *named consumer* with a latency / online / self-serve-metrics
requirement — never a tooling preference on its own.

## 4. Mixing SQL and Python in transforms

**Known.** The transform layer is SQL-first on DuckDB via SQLMesh
([ADR-0004](adr/ADR-0004-sqlmesh-default-transform-engine.md)). But market modeling —
cross-source entity resolution, fuzzy matching, feature engineering, anything
statistical — will eventually fight pure SQL.

**Open.**

- What share of the analytical layer needs Python, and where: pre-landing parsing (already
  Python), staging cleanup, or *inside* the modeled DAG?
- If inside the DAG, engine support becomes the deciding axis:
  - **SQLMesh** — Python models are first-class citizens (same DAG, lineage, audits) —
    the current default keeps working;
  - **dbt** — Python models effectively require a warehouse runtime
    (Snowflake/Databricks); a dead end on DuckDB;
  - **OpenDBT** — patches exactly that dbt gap (local Python models); relevant only if
    dbt compatibility ever becomes a requirement;
  - **Bruin** — runs Python assets natively next to SQL; strengthens the existing
    alt-profile story.
- DataFrame engine for those models: **Polars** (typed, lazy, Arrow-native — default
  candidate) vs Pandas (ubiquity, notebooks) vs **PySpark** (only with cluster scale —
  ties to §2).

**Current default.** SQL in SQLMesh. A transform that fights SQL becomes a **SQLMesh
Python model** using Polars over Arrow; Pandas stays at notebook/demo level; no Spark.

**Decision trigger.** First production model whose SQL version is unreadable or slower
than its Python equivalent → implement as a SQLMesh Python model and record the pattern.
If such models grow into a majority, revisit the engine choice (Bruin/OpenDBT) in the
Phase-9 comparison docs.
