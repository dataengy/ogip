#!/usr/bin/env bash
# Deploy a commit — RUNS ON THE VPS, inside the checkout (step 2 of the runbook).
#
# Drive it from your laptop with `just vps-deploy` (which ssh's in and calls this), or run
# it directly after `ssh <host>; cd /opt/ogip`. Idempotent: re-running redeploys the same ref.
#
# Usage: deploy/vps/deploy.sh [--dry-run] [<git-ref>]
# See docs/runbooks/deploy-vps.md · ADR-0012.

# shellcheck source=deploy/vps/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

VPS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

vps_usage() {
  cat <<'USAGE'
Usage: deploy/vps/deploy.sh [--dry-run] [<git-ref>]

Runs ON the VPS: fetch + checkout the ref, uv sync, render .env, deploy the Prefect flows,
and bring compose up. Defaults to deploy.vps.branch when no ref is given.

  --dry-run   print every command instead of running it
  --help      this text
USAGE
}

# preflight — abort BEFORE mutating the checkout if a prerequisite is absent.
# These artifacts are owned by other lanes; a deploy that fetches, syncs and then dies
# halfway leaves the host in a state nobody asked for. Fail first, fail whole.
preflight() {
  local missing=()
  [[ -f "${VPS_REPO_ROOT}/config/.env-render.py" ]] || missing+=("config/.env-render.py")
  [[ -f "${VPS_REPO_ROOT}/integrations/prefect/deploy.py" ]] ||
    missing+=("integrations/prefect/deploy.py  (Justfile 'prefect-deploy' — core-pipeline lane)")
  [[ -f "${VPS_REPO_ROOT}/deploy/docker-compose.yml" ]] ||
    missing+=("deploy/docker-compose.yml  (Makefile 'up' — compose/obs lane)")

  if [[ ${#missing[@]} -gt 0 ]]; then
    warn "deploy prerequisites are missing from this checkout:"
    printf '  - %s\n' "${missing[@]}" >&2
    die "cannot deploy yet — these are tracked as known gaps in .ai/STATUS.md"
  fi
}

vps_parse_flags "$@"
vps_load_settings

# Positional ref wins over the configured branch — this is how rollback pins an old sha.
if [[ ${#VPS_ARGS[@]} -gt 0 ]]; then
  target_ref="${VPS_ARGS[0]}"
else
  target_ref="$VPS_BRANCH"
fi

cd "$VPS_REPO_ROOT"
log "deploying ref ${target_ref} in ${VPS_REPO_ROOT}"
[[ "$VPS_DRY_RUN" -eq 1 ]] && log "mode   : DRY-RUN — nothing will be changed"

log "step 0/6 — preflight"
preflight

log "step 1/6 — fetch + checkout ${target_ref}"
vps_run git fetch --all --tags --prune
vps_run git checkout --force "$target_ref"
# Fast-forward only when on a branch; a detached sha (rollback) has no upstream to pull.
if [[ "$VPS_DRY_RUN" -eq 0 ]] && git symbolic-ref -q HEAD >/dev/null; then
  vps_run git pull --ff-only
fi

log "step 2/6 — uv sync (into .run/venv)"
export UV_PROJECT_ENVIRONMENT="${VPS_REPO_ROOT}/.run/venv"
vps_run uv sync --frozen

log "step 3/6 — render .env from config/config.yml (filled secrets are preserved)"
vps_run uv run python config/.env-render.py

log "step 4/6 — verify required secrets are filled"
vps_run bash "${VPS_SCRIPT_DIR}/check-secrets.sh"

log "step 5/6 — deploy Prefect flows"
vps_run uv run python integrations/prefect/deploy.py

log "step 6/6 — compose up (core services)"
vps_run make up

log "deploy complete — ref $(git rev-parse --short HEAD 2>/dev/null || echo "${target_ref}")"
log "NEXT: verify with deploy/vps/smoke.sh (or: just vps-smoke)"
