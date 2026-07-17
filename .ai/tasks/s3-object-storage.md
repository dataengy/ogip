# Task — S3 object storage (the `minio` / `s3` / `r2` lake profiles)

**Status:** 🚧 in progress — the seam, the MinIO stack, tests and docs are shipped and verified
green against a real MinIO; every remaining call site is blocked on the `core-pipeline` lane
(see _Blocked on_ — 4 items, of which Layer-0 is the real one). `local` remains the default,
so nothing existing changed behaviour.

Lane: `s3` (parallel-session lock object). Scope: `src/ogip/storage.py`, MinIO in
`deploy/docker-compose.yml`, the `storage-*` Makefile targets, storage tests and docs.
Decisions: [ADR-0003](../../docs/adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md) (Parquet
lake) · D2 (storage profiles) · architecture:
[storage.md](../../docs/architecture/storage.md).

## Why

`config/config.yml → storage.backend` declared `local | minio | s3 | r2` and
`config/.env-render.py` already rendered `OGIP_STORAGE_BACKEND` into `.env` — but **nothing
read either**. `ingestion/base/base_source.py` hardcoded the dlt destination to the local
filesystem (`bucket_url=data_dir.resolve().as_uri()`). D2 was documentation, not behaviour:
there was no way to run OGIP against object storage.

## Delivered

- **`src/ogip/storage.py`** — the single seam resolving backend → bucket URL + credentials:
  - `StorageSettings` — `OGIP_STORAGE_BACKEND`, default read from the SSoT (no duplicated value).
  - `raw_bucket_url(data_dir)` — `file://…` for `local`, else `s3://<raw_bucket>`. Pure.
  - `dlt_filesystem_destination(data_dir)` — the dlt destination with credentials attached.
  - `configure_duckdb_s3(con)` — loads `httpfs`, registers the S3 secret using **bound
    parameters** (credentials never reach SQL text). No-op on `local`; idempotent.
  - Fails early naming the exact missing variable rather than surfacing a cryptic 403.
  - MinIO → path-style URLs (it has no DNS-style bucket hosts); empty endpoint → real AWS.
- **`deploy/docker-compose.yml`** — the base stack the Makefile already referenced but which
  had never existed (`make up` was broken): Postgres + Prefect, plus `minio` + `minio-init`
  (bucket bootstrap) behind the `storage` profile. Declares the `ogip` network `deploy/obs/`
  expects and satisfies `deploy/vps/deploy.sh`'s preflight.
- **`make storage-up` / `make storage-down`**; `deploy/README.md`.
- **Tests** — 11 unit (backend resolution, URL style, credential errors, `local` no-op) + a
  MinIO **round-trip** integration test: dlt writes Parquet to `s3://ogip-raw`, DuckDB reads
  every row back via `httpfs`, and nothing leaks to the local FS.
- **`docs/architecture/storage.md`** — the one-code-path model, config layering, local dev.

## Security note

MinIO's root credentials (`MINIO_ROOT_*`) are deliberately **separate** from OGIP's client
slots (`OGIP_S3_*`). The client slots may hold a real AWS/R2 key, and wiring a real key into a
local container as its root password is a footgun. For the `minio` profile the two must match;
they ship as throwaway dev literals (`ogipminio` / `ogipminio123`) — never secrets.

## Blocked on

Every remaining call site lives in the **`core-pipeline`** lane, held by a parallel session
(lock expires 2026-07-17 16:00). Apply in this order once it releases:

1. **`ingestion/base/base_source.py`** — swap the hardcoded local destination for
   `dlt_filesystem_destination(data_dir)`; `run()` returns the dataset **URL** (`str`) rather
   than a `Path`. Its only caller (`pipelines/flows/main.py:41`) already does `str(out)`, so
   the flow and its `file://ogip/raw/rawg__games` asset key are unaffected.
2. **`spec/sql/raw/*.sql` + the spec compiler** — ⚠️ **the real end-to-end blocker.** Layer-0
   hardcodes a local literal:
   `select * from read_parquet('.run/data/raw/rawg__games/*.parquet')`. Object storage needs
   the lake root **injected by the compiler** (e.g. a `@lake_root` variable) instead of a
   literal path — otherwise SQLMesh keeps reading the local FS no matter what dlt writes.
   This is a spec-compiler concern (D0/D5) and is the reason `backend: minio` cannot yet run
   `make run` end to end.
3. **`transform/sqlmesh/config.yaml`** — the DuckDB gateway needs S3 access. SQLMesh supports
   this natively (`DuckDBConnectionConfig` has both `extensions` and `secrets`), so it is
   **config, not code**: `extensions: [httpfs]` + a `secrets:` entry interpolated from the
   `OGIP_S3_*` env slots. SQLMesh opens its own connection, so `configure_duckdb_s3()` cannot
   reach it.
4. **`config/.env-render.py`** — ship `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` plus the
   matching `OGIP_S3_*` dev defaults as `DEMO_DEFAULTS` (the existing `OGIP_PG_PASSWORD`
   pattern), so `make storage-up` + `backend: minio` works from a bare checkout without
   hand-filling slots.

`src/ogip/warehouse.py` needs **no** change: `export_table` reads from the built DuckDB
warehouse and never touches `s3://`.

## Open question — `configure_duckdb_s3()` has no production caller yet

AGENTS rule 2 says no abstraction without two concrete call sites. Today `configure_duckdb_s3`
has **zero**: SQLMesh configures its own connection (item 3 above), and `warehouse.py` never
reads `s3://`. It is currently exercised only by tests. It is kept because
[ADR-0002](../../docs/adr/ADR-0002-duckdb-analytical-engine.md) promises DuckDB reads Parquet
in place from S3/R2, and the ad-hoc consumers that need it are already planned — notebooks
(D7, the primary DS interface) and the `dq/` runner (Phase 4). **If those do not materialise,
delete it** rather than let it rot.

## Verification

`ruff` clean · `pyright` strict 0 errors · 13/13 storage tests green, including the MinIO
round-trip against a live container (`make storage-up`).

## Next

- Apply the staged core wiring once `core-pipeline` releases; then run the full pipeline with
  `backend: minio` end to end (`make run`) and add an e2e assertion.
- Wire R2 as the cloud of record (D9) — credentials only; no code change expected.
- Consider a CI integration job with a MinIO service container (the round-trip test is
  already CI-shaped: it skips cleanly when MinIO is absent).
