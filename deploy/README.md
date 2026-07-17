# deploy/ — local & VPS runtime stacks

Compose stacks for the services OGIP runs against. Everything is driven from the SSoT
(`config/config.yml` → rendered `.env` via `make render-env`) — never hardcode a port,
bucket or user here; add it to the SSoT and reference `${VAR}`.

| File | Stack | Commands |
|---|---|---|
| `docker-compose.yml` | **base**: Postgres, Prefect server, MinIO (profile `storage`) | `make up` · `make storage-up` · `make down` |
| `obs/docker-compose.obs.yml` | **observability**: VictoriaMetrics, Loki, Alloy, Grafana | `make obs-up` · `make obs-down` |

Both projects share the external-facing `ogip` network declared by the base stack.

## Services

- **postgres** — landing zone + `platform_meta` + the Prefect backend (ADR-0008 / D9).
- **prefect** — Prefect server for the `server` runtime profile. The **default runtime is
  ephemeral** (D3), so `make run` needs no server at all.
- **minio** + **minio-init** — S3-compatible object storage for the `minio` lake profile
  (D2 / [ADR-0003](../docs/adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md)). Behind the
  `storage` profile, so `make up` stays lean. `minio-init` creates the raw bucket so the
  first run has somewhere to land. See [docs/architecture/storage.md](../docs/architecture/storage.md).

## Credentials

`.env` is gitignored; secrets are blank slots filled by hand or by GitHub Actions (ADR-0011 /
D10). The `${VAR:-default}` fallbacks here mirror the SSoT literals so the stack still boots
from a bare checkout.

MinIO's **root** credentials (`MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`) are deliberately
separate from OGIP's **client** credentials (`OGIP_S3_*`): the client slots may hold a real
AWS or R2 key, and feeding a real key to a local container as its root password is a footgun.
For the `minio` profile the two must match — `config/.env-render.py` ships both as dev
defaults (`ogipminio` / `ogipminio123`), which are throwaway local literals, **not** secrets.

## VPS

Deploy is manual (ADR-0012); DevOps is handled separately. See
[docs/runbooks/](../docs/runbooks/).
