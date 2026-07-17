#!/usr/bin/env bash
# OGIP — end-to-end smoke test of the log path: file → Alloy → Loki → query (Phase 7 · lane `obs`).
#
# Writes one loguru-shaped JSON line into .run/logs/ and asserts it comes back out of Loki with
# its parsed labels. This is the Phase 7 accept-check for logs, and it needs no pipeline run —
# useful because the flow does not write a log file yet (see docs/architecture/observability.md).
#
# Invoked by `just obs-smoke-log`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

log() { echo "[obs-smoke] $*"; }
die() {
  echo "[obs-smoke] ERROR: $*" >&2
  exit 1
}

if [[ -f .env ]]; then
  # shellcheck disable=SC1090
  source <(grep -E '^LOKI_PORT=' .env || true)
fi
LOKI_PORT="${LOKI_PORT:-3100}"

command -v jq >/dev/null || die "jq is required (brew install jq)"

marker="obs-smoke-$(date +%s)-$$"
log_file=".run/logs/obs-smoke.log"
mkdir -p .run/logs

# Mirror loguru's serialize=true envelope exactly — this is what Alloy's stage.json parses.
cat >>"$log_file" <<EOF
{"text":"${marker} synthetic smoke line","record":{"level":{"name":"ERROR"},"name":"ogip.smoke","message":"${marker} synthetic smoke line","extra":{"source":"smoke","entity":"selftest","flow_run_id":"${marker}"}}}
EOF
log "wrote marker to ${log_file} → ${marker}"

# Alloy's sync_period is 10s; give it room, then query Loki for the marker.
deadline=$((SECONDS + 60))
query='{job="ogip",level="ERROR"}'
while ((SECONDS < deadline)); do
  hits="$(
    curl -fsS --max-time 5 -G "http://localhost:${LOKI_PORT}/loki/api/v1/query_range" \
      --data-urlencode "query=${query}" \
      --data-urlencode "start=$(($(date +%s) - 600))000000000" \
      --data-urlencode "limit=100" 2>/dev/null |
      jq -r --arg m "$marker" '[.data.result[]?.values[]?[1] | select(contains($m))] | length' 2>/dev/null || echo 0
  )"
  if [[ "${hits:-0}" -gt 0 ]]; then
    log "PASS — marker round-tripped file → Alloy → Loki, and parsed as level=ERROR"
    exit 0
  fi
  sleep 3
done

die "marker never reached Loki within 60s — check: docker logs ogip-alloy"
