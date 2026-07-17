# Storage — the Parquet lake

> Scope: where raw Parquet lives and how the pipeline reaches it.
> Decisions: [ADR-0003](../adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md) (Parquet lake;
> Iceberg/DuckLake deferred) · [ADR-0002](../adr/ADR-0002-duckdb-analytical-engine.md) (DuckDB
> reads Parquet in place) · D2 (storage profiles).

## One code path, four backends

The lake is **plain Parquet** (PyArrow, written by dlt). Where it lands is a *profile*, not a
code branch:

| Backend | What it is | Endpoint | URL style |
|---|---|---|---|
| `local` | **default** — local filesystem under `.run/data/raw` | — (`file://`) | — |
| `minio` | S3-compatible container for local dev / CI | `http://localhost:9000` | **path** |
| `s3` | AWS S3 | *empty* → resolved by region | virtual-host |
| `r2` | Cloudflare R2 — the cloud of record (D9) | `https://<account>.r2.cloudflarestorage.com` | virtual-host |

`minio`, `s3` and `r2` are **the same S3 code path** — only endpoint, credentials and URL
style differ. That is the whole point of ADR-0003: develop against MinIO for free and offline,
then point at R2 or S3 with credentials alone. Nothing in `ingestion/`, `spec/` or the flow
changes.

MinIO needs **path-style** URLs (`endpoint/bucket/key`) because it has no DNS-style bucket
hosts; AWS and R2 use the default virtual-host style. `src/ogip/storage.py` handles this.

## The seam

All of it lives in [`src/ogip/storage.py`](../../src/ogip/storage.py):

| Function | Used by | Does |
|---|---|---|
| `raw_bucket_url(data_dir)` | writers | `file://…` for `local`, else `s3://<raw_bucket>` |
| `dlt_filesystem_destination(data_dir)` | `ingestion/base/base_source.py` | the dlt destination, credentials attached |
| `configure_duckdb_s3(con)` | `src/ogip/warehouse.py` | loads `httpfs` + registers the S3 secret so DuckDB reads `s3://` |

`configure_duckdb_s3` is a **no-op on `local`** and idempotent, so it is safe to call
unconditionally. Credentials are passed to DuckDB as **bound parameters** — never
interpolated into SQL.

## Configuration (SSoT)

Two layers, per [`config/README.md`](../../config/README.md):

- **Which** backend → `config/config.yml → storage.backend`; override with
  `OGIP_STORAGE_BACKEND`. Never edit the rendered `.env` — edit the YAML and
  `make render-env`.
- **Where/how** → `OGIP_S3_*`: `ENDPOINT_URL`, `RAW_BUCKET`, `REGION` (derived from
  `config.yml`) plus `ACCESS_KEY_ID` / `SECRET_ACCESS_KEY` (secret slots, blank by default —
  filled by hand or by GitHub Actions secrets, ADR-0011 / D10).

Misconfiguration fails **early and explanatorily** rather than as a cryptic 403:
`minio` and `r2` without an endpoint, or any object backend without credentials, raise
`StorageBackendError` naming the exact variable to set.

## Local development

```bash
make storage-up                      # MinIO + create the raw bucket; prints the dev keys
# config/config.yml → storage.backend: minio
make render-env
make run                             # raw Parquet now lands in s3://ogip-raw
make test-integration                # round-trips real Parquet through MinIO
```

MinIO console: `http://localhost:9001` (dev keys `ogipminio` / `ogipminio123` — throwaway
local literals, **not** secrets). `make storage-down` stops it; the data volume survives.

MinIO's root credentials are intentionally **separate** from the `OGIP_S3_*` client slots —
see [deploy/README.md](../../deploy/README.md#credentials) for why.

## Layout

Unchanged across backends — only the prefix moves:

```
<lake-root>/raw/<system>__<entity>/*.parquet     # Layer 0, 1:1 AS-IS
```

`<lake-root>` is `.run/data` (local) or `s3://ogip-raw`. Raw partitioning follows
`config.yml → raw.partitioning`; Layer-0 naming (`<system>__<table>`) is law — see
[overview.md](overview.md).

## Why not a table format (yet)

Iceberg/DuckLake stay research (ADR-0003): plain Parquet + DuckDB covers the dataset sizes
this platform targets, and a table format would add a catalog, maintenance jobs and a
migration story for no present gain. The S3 code path here is the same one an Iceberg
migration would need, so nothing is foreclosed.
