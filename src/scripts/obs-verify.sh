#!/usr/bin/env bash
# OGIP — assert the observability stack is live (Phase 7 · lane `obs`).
#
# Complements the compose healthchecks rather than repeating them: Alloy has no in-image HTTP
# client (no wget/curl/nc), so it cannot self-probe and carries no healthcheck — this script is
# the only thing that asserts Alloy is ready. It also checks the stack from OUTSIDE, which is
# what actually matters: a container can be healthy while its published port is unreachable.
#
# Invoked by `make obs-up` and `just obs-verify`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

log() { echo "[obs] $*"; }
die() {
  echo "[obs] ERROR: $*" >&2
  exit 1
}

# Ports: the rendered .env wins; fallbacks mirror config/config.yml (the SSoT). Today .env
# carries no obs ports — config/.env-render.py does not map them yet (lane `core-pipeline`).
if [[ -f .env ]]; then
  # shellcheck disable=SC1090
  source <(grep -E '^(VICTORIAMETRICS|LOKI|GRAFANA|ALLOY)_PORT=' .env || true)
fi

VM_PORT="${VICTORIAMETRICS_PORT:-8428}"
LOKI_PORT="${LOKI_PORT:-3100}"
GRAFANA_PORT="${GRAFANA_PORT:-3300}"
ALLOY_PORT="${ALLOY_PORT:-12345}"

RETRIES="${OBS_VERIFY_RETRIES:-30}" # ~30s: Grafana provisioning is the slow one on first boot

# probe <name> <url> <expected-substring>
probe() {
  local name="$1" url="$2" want="$3" body="" i=1
  while ((i <= RETRIES)); do
    if body="$(curl -fsS --max-time 3 "$url" 2>/dev/null)" && [[ "$body" == *"$want"* ]]; then
      log "OK    $name — $url"
      return 0
    fi
    sleep 1
    ((i++))
  done
  log "FAIL  $name — $url (last response: ${body:-<none>})"
  return 1
}

failed=0
probe victoriametrics "http://localhost:${VM_PORT}/health" "OK" || failed=1
probe loki "http://localhost:${LOKI_PORT}/ready" "ready" || failed=1
probe alloy "http://localhost:${ALLOY_PORT}/-/ready" "" || failed=1
probe grafana "http://localhost:${GRAFANA_PORT}/api/health" "ok" || failed=1

((failed == 0)) || die "stack is not healthy — inspect: docker compose -f deploy/obs/docker-compose.obs.yml logs"

log "healthy → Grafana http://localhost:${GRAFANA_PORT} (dashboard: OGIP — Pipeline & Stack)"
