# Task — Resilient scraping: `ScraperSource` + landing + first scraped source (~~HLTB~~ → Metacritic)

**Status:** 📋 planned · **Priority:** **P1**

> **⛔ 2026-07-18 — HLTB is legally blocked; first scraped source is now Metacritic.**
> HowLongToBeat (Ziff Davis) robots.txt prohibits automated retrieval outright and names
> AI/ML databases and dataset-sharing as prohibited uses — OGIP publishes ML-ready
> datasets, so this is disqualifying regardless of `publishable: false` (that protects
> the data, not the fetch). Evidence + verbatim quote:
> [`spec/sources/games/hltb_games.yaml`](../../spec/sources/games/hltb_games.yaml)
> (`do_not_fetch: true` — the probe returns FORBIDDEN without opening a connection).
> Metacritic — planned below as merely "next after" — is robots-permitted for `/game/`
> and its scrape contract is live-verified (JSON-LD, 6/6 fields):
> [`spec/sources/games/metacritic_game.yaml`](../../spec/sources/games/metacritic_game.yaml).
> SteamCharts (css markers) and OpenCritic (JSON-LD) are also probe-verified and ready.
> Game-length data needs a licensed or permissive substitute (licensing@ziffdavis.com, or
> IGDB/Wikidata fields) — tracked in the backlog. Everything else in this task
> (ScraperSource, landing, politeness, resilience) stands unchanged; only the target
> source swaps.

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
