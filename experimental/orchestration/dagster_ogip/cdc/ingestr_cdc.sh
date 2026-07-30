#!/usr/bin/env bash
# ingestr CDC — Change Data Capture from the platform Postgres LANDING zone into the lake.
#
# WHY ingestr (not dlt) here: dlt is the default batch ingester (ADR-0006/D11), but the landing
# zone is exactly the "some pipeline" that benefits from CDC — scrapers write rows there
# continuously, and ingestr exposes Postgres logical-replication CDC as one flag-driven command
# (`--stream`, replication_slot/publication in the source URI). See:
#   https://getbruin.com/docs/ingestr/getting-started/cdc.html
#
# This captures INSERT/UPDATE/DELETE on landing tables and merges them into DuckDB, keeping the
# lake a live mirror of landing rather than a periodic snapshot. Batch API sources stay on dlt.
#
#   cdc/ingestr_cdc.sh --dry-run        # print the ingestr command, touch nothing
#   cdc/ingestr_cdc.sh                   # one-shot CDC catch-up (merge changes since the slot)
#   cdc/ingestr_cdc.sh --stream          # continuous: flush on interval/row-count trigger
#
# Config comes from OGIP_* env (ADR-0011 — secrets never inlined):
#   OGIP_PG_HOST/PORT/USER/PG_PASSWORD/DATABASE, OGIP_PG_LANDING_SCHEMA (default: landing),
#   OGIP_CDC_SLOT (default: ogip_cdc), OGIP_CDC_PUBLICATION (default: ogip_landing_pub),
#   OGIP_DATA_DIR (default: .run/data).
set -euo pipefail

DRY=0
STREAM_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --stream) STREAM_ARGS+=(--stream) ;;
    *) STREAM_ARGS+=("$arg") ;;
  esac
done

: "${OGIP_PG_HOST:=localhost}"
: "${OGIP_PG_PORT:=5432}"
: "${OGIP_PG_USER:=ogip}"
: "${OGIP_PG_PASSWORD:=}"
: "${OGIP_PG_DATABASE:=ogip}"
: "${OGIP_PG_LANDING_SCHEMA:=landing}"
: "${OGIP_CDC_SLOT:=ogip_cdc}"
: "${OGIP_CDC_PUBLICATION:=ogip_landing_pub}"
: "${OGIP_DATA_DIR:=.run/data}"

# Postgres CDC source URI: logical replication via a slot + publication (ingestr/dlt pg_replication).
SOURCE_URI="postgresql://${OGIP_PG_USER}:${OGIP_PG_PASSWORD}@${OGIP_PG_HOST}:${OGIP_PG_PORT}/${OGIP_PG_DATABASE}?replication_slot=${OGIP_CDC_SLOT}&publication=${OGIP_CDC_PUBLICATION}"
# Destination: the lake mirror as a local DuckDB (S3/R2 when the storage lane lands its URL).
DEST_URI="duckdb://${OGIP_DATA_DIR}/warehouse/ogip.duckdb"

# CDC multi-table mode: no --source-table → every table in the publication is captured, merged
# on its primary key so the destination reflects the current landing state.
cmd=(
  ingestr ingest
  --source-uri "$SOURCE_URI"
  --dest-uri "$DEST_URI"
  --source-table "${OGIP_PG_LANDING_SCHEMA}.*"
  --dest-table "cdc_landing"
  --incremental-strategy merge
  "${STREAM_ARGS[@]}"
)

redacted="${cmd[*]//${OGIP_PG_PASSWORD:-__nopass__}/******}"
echo "[cdc] $redacted"
if [[ "$DRY" == "1" ]]; then
  echo "[cdc] --dry-run: nothing executed."
  exit 0
fi
if [[ -z "$OGIP_PG_PASSWORD" ]]; then
  echo "[cdc] ERROR: OGIP_PG_PASSWORD is blank — render .env / fill secrets first." >&2
  exit 1
fi
exec uv run "${cmd[@]}"
