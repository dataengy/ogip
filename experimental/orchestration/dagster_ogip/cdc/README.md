# CDC — Change Data Capture from the Postgres landing zone (ingestr)

**One pipeline uses CDC, deliberately** (D11). The default ingester is **dlt** for batch API
sources (ADR-0006). But the Postgres **landing** zone — where scrapers write parsed rows
continuously — is exactly the source where CDC pays off, so it uses **ingestr**, which exposes
Postgres logical-replication CDC as a single flag-driven command.

Reference: <https://getbruin.com/docs/ingestr/getting-started/cdc.html>

## How

`ingestr_cdc.sh` captures INSERT/UPDATE/DELETE on `landing.*` via a replication **slot** +
**publication** and merges them into the lake (DuckDB), so the lake is a *live mirror* of
landing rather than a periodic snapshot.

```bash
cdc/ingestr_cdc.sh --dry-run     # print the command, touch nothing (works with no DB)
cdc/ingestr_cdc.sh               # one-shot CDC catch-up (merge changes since the slot)
cdc/ingestr_cdc.sh --stream      # continuous (flush on interval / row-count trigger)
```

Config is `OGIP_*` env only (ADR-0011 — no secret literals); the printed command redacts the
password. In this environment it is exercised via `--dry-run` (no Docker/Postgres); a live run
needs the landing DB with `wal_level=logical` and the publication created:

```sql
ALTER SYSTEM SET wal_level = logical;   -- then restart
CREATE PUBLICATION ogip_landing_pub FOR TABLES IN SCHEMA landing;
```

## One-time setup on the source (prod)

The replication slot is created by ingestr on first run; the publication and `wal_level` are a
DBA/provision step (belongs to the VPS/DevOps lane, ADR-0012). Then schedule the asset (below)
or run `--stream` under the daemon.

## As a Dagster asset

`defs/cdc_ingest/definitions.py` wraps the script as an asset in the `ingestion` group, so CDC
sits in the same graph as the dlt batch load and the dbt models, selectable with
`dg launch --assets 'key:"cdc_landing"'`.
