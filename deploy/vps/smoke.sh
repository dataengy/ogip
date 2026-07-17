#!/usr/bin/env bash
# Post-deploy verification — RUNS ON THE VPS (runbook "Verify" section).
#
# Checks what the runbook promises: containers healthy, a Prefect smoke run reaches
# Completed, outputs written, no secret leaked to the logs. Read-only: it asserts, it
# never fixes. Non-zero exit = do not consider the deploy good.
#
# Usage: deploy/vps/smoke.sh [--dry-run]

# shellcheck source=deploy/vps/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

vps_usage() {
  cat <<'USAGE'
Usage: deploy/vps/smoke.sh [--dry-run]

Verifies a deploy on the VPS: compose health, a sample Prefect run, outputs on disk,
and a secret-leak scan of the run log.

  --dry-run   print every command instead of running it
  --help      this text
USAGE
}

vps_parse_flags "$@"
cd "$VPS_REPO_ROOT"

failures=0
check() {
  local label="$1"
  shift
  if vps_run "$@"; then
    log "PASS — ${label}"
  else
    warn "FAIL — ${label}"
    failures=$((failures + 1))
  fi
}

log "smoke — $(date -u '+%Y-%m-%d %H:%M:%SZ') · $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown ref')"

log "1/4 — compose services healthy"
check "compose ps" docker compose -f deploy/docker-compose.yml --env-file .env ps

log "2/4 — Prefect smoke run on sample data"
export UV_PROJECT_ENVIRONMENT="${VPS_REPO_ROOT}/.run/venv"
check "prefect run" uv run python integrations/prefect/trigger.py ingest_transform_publish

log "3/4 — ML-ready outputs present"
# shellcheck disable=SC2016  # the $(find ...) belongs to the inner shell, evaluated at check time.
check "outputs written" bash -c '[[ -n "$(find .run/data/outputs -name "*.parquet" -print -quit 2>/dev/null)" ]]'

log "4/4 — no secret value in the logs"
check "secret scan" bash "${VPS_REPO_ROOT}/.ci/steps/secret-scan.sh"

if [[ "$failures" -gt 0 ]]; then
  die "smoke FAILED — ${failures} check(s) failed; roll back per docs/runbooks/deploy-vps.md"
fi
log "smoke PASSED — deploy verified"
