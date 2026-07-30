# ADR-0014 — Resilient scraping: async-first concurrency, effectively-once landing

- **Status:** Proposed
- **Date:** 2026-07-17
- **Relates to:** PLAN A6 · D11 · [ADR-0006](ADR-0006-dlt-default-ingestion-postgres-landing.md) ·
  [OPEN-QUESTIONS §1](../OPEN-QUESTIONS.md)

## Context

Roughly half of OGIP's planned sources are scraped or parsed rather than fetched from
clean APIs (HLTB, Metacritic; regional price sweeps are API-shaped but volume-hostile).
ADR-0006 fixes *where* scraped data lands (Postgres `landing` → dlt → raw Parquet) but not
*how* the fetch side behaves. The fetch side needs: resilient retrieval (retries, failure
isolation, resumability), source politeness (rate limits, robots/ToS), duplicate-free
landing under redelivery, full observability, and a concurrency model that scales from one
page to catalog-scale sweeps without a rewrite.

## Decision

`ScraperSource` implements **one scraping pattern**, reused by every scraped source:

1. **Concurrency — async-first.** Fetching is I/O-bound, so `httpx.AsyncClient` + asyncio
   with **bounded concurrency**: a global connection cap and a per-domain semaphore, both
   read from the config SSoT (`scraping.max_connections` · `scraping.per_domain`). Threads
   are not used for fetching. **Processes are opt-in for the parse stage only** — a
   `ProcessPoolExecutor` behind `scraping.parse_workers` (default `0` = inline), enabled
   when profiling shows CPU-bound parsing dominates; parse functions stay pure so the pool
   is a drop-in.
2. **Politeness.** Per-domain token-bucket rate limit; jittered exponential backoff
   (tenacity) honoring `Retry-After`; an identifying User-Agent; robots.txt/ToS review
   recorded per source in its contract; HTTP caching (ETag / conditional GET) where the
   source supports it.
3. **Resilience.** Timeouts on every call; a retry budget per URL; a per-domain **circuit
   breaker** (N consecutive failures → cooldown; the run continues with the domain marked
   degraded); failed fetches recorded to a DLQ table — `landing.fetch_failures` (url,
   attempts, last error, fetched_at) — for later replay. A partial run is a normal run,
   not a crash.
4. **Effectively-once, not "exactly-once".** Transport is honestly **at-least-once**
   (retries can refetch); the landing upsert is **idempotent** (natural key + content
   hash, `ON CONFLICT` update), so downstream observes exactly-once *effect*. Watermark
   checkpoints per entity batch (`ingestion/common/watermark.py`) make interrupted sweeps
   resumable.
5. **Observability.** Structured loguru events per fetch (url, status, attempt, latency,
   bytes) in the pipeline's JSON log stream; per-source counters (fetched · retried ·
   failed · rate-limited · breaker-open) exported as metrics; freshness and failure-rate
   alerts via the `Notifier`.
6. **Escalation ladder** for hostile targets, decided per source and documented in its
   contract: plain httpx (default) → `curl_cffi` (TLS-fingerprint parity) → Playwright
   (JS rendering). Nothing above httpx enters the prod path until a concrete source
   needs it.

## Consequences

- One resilience/politeness implementation serves every scraped source; per-source code
  shrinks to: entity discovery, URL construction, parse.
- `ScraperSource`'s API becomes async (async generators); the Prefect task wraps it in
  `asyncio.run`, so flow code stays sync.
- Two more landing artifacts to maintain (DLQ table, watermark store) — the price of
  resumability and replay.
- Delivery-guarantee claims are testable, not oversold: fetching the same page twice must
  yield one landing row.
- No multiprocessing complexity by default; the parse pool exists only where measured.

## Alternatives considered

- **Scrapy** — mature, but brings its own event loop, middleware stack, and project
  layout; duplicates what `BaseSource` + dlt already own (scheduling, dedupe, export).
  Rejected for the prod path; reconsidered only if >3 heavy sources strain the httpx
  ladder ([OPEN-QUESTIONS §1](../OPEN-QUESTIONS.md)).
- **Thread-pool fetching** — workable, but worse backpressure and cancellation than
  asyncio at high fan-out, with no GIL win for network waits. Rejected as the default.
- **Multiprocessing-first fetching** — memory ×N and IPC complexity with zero I/O
  benefit. Kept only as the opt-in parse-stage pool.
- **Managed scraping services (Zyte, Apify)** — hosted dependency and per-request cost;
  contradicts the open, self-hosted stack. Out.
