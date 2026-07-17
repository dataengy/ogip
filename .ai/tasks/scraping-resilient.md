# Task — Resilient scraping: `ScraperSource` + landing + first scraped source (HLTB)

**Status:** 📋 planned · **Priority:** **P1**

Lane: `ingestion` (claim the lock object before writing). Scope:
`ingestion/base/scraper_source.py`, `ingestion/common/{http,throttle,cache,watermark}.py`,
`ingestion/sources/hltb.py`, landing DDL, tests. Decision record:
[ADR-0014](../../docs/adr/ADR-0014-resilient-scraping-concurrency.md) · landing pattern:
[ADR-0006](../../docs/adr/ADR-0006-dlt-default-ingestion-postgres-landing.md) · open
questions: [OPEN-QUESTIONS §1](../../docs/OPEN-QUESTIONS.md).

## Why

Half of the planned sources are scraped/parsed, and resilient scraping is the single
biggest gap between the declared architecture (PLAN A6) and shipped code — M0 covers only
a clean API. This slice makes the `scrape → Postgres landing → dlt → raw Parquet` half of
the pipeline real, with the full resilience pattern every later scraped source reuses.

## Deliverables

- [ ] **`ScraperSource` (async)** — `httpx.AsyncClient`; global + per-domain bounded
      concurrency from the config SSoT (`scraping.max_connections` · `scraping.per_domain`).
- [ ] **Politeness** — per-domain token-bucket throttle; tenacity backoff with jitter,
      honoring `Retry-After`; identifying User-Agent; robots/ToS note recorded in the
      source contract.
- [ ] **Resilience** — timeouts on every call; retry budget per URL; per-domain circuit
      breaker (cooldown, run continues degraded); DLQ table `landing.fetch_failures`
      (url, attempts, last_error, fetched_at) + a replay path.
- [ ] **Effectively-once landing** — idempotent upsert on natural key + content hash
      (`ON CONFLICT` update); watermark checkpoints so interrupted sweeps resume.
- [ ] **Opt-in CPU parse pool** — pure parse functions; `ProcessPoolExecutor` behind
      `scraping.parse_workers` (default `0` = inline).
- [ ] **Observability** — structured fetch events in the JSON log stream; per-source
      counters (fetched · retried · failed · rate-limited · breaker-open); freshness +
      failure-rate alert hooks (`Notifier`).
- [ ] **`ingestion/sources/hltb.py`** — entity discovery (game ids already in raw) →
      fetch → parse (main / extra / completionist hours) → landing.
- [ ] **dlt load** — landing → raw `hltb__games` Parquet (merge/dedupe on natural key).
- [ ] **spec follow-through** — ODCS contract + `stg_hltb__games` model.
- [ ] **Tests** — unit on fixtures, no live HTTP in CI (throttle, backoff, breaker,
      idempotent upsert: same page twice → one row); one recorded-response integration
      test; e2e: flow runs scrape (fixtures) → landing → raw → stg green in CI.

## Acceptance

- `make run` (HLTB enabled on fixtures) green end to end; re-running duplicates nothing
  in landing or raw.
- Kill a run mid-sweep → the next run resumes from the watermark, no duplicates.
- A domain forced to fail N times opens the breaker; the run completes and reports the
  domain degraded instead of crashing.
- `make check` green; CI green.

## Next after this

Metacritic as the second scraped source (same pattern; first check on the hostile-site
ladder), then regional price sweeps (API-shaped, volume-hostile) — see
[sources-backlog.md](sources-backlog.md).
