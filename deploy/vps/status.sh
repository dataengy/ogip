#!/usr/bin/env bash
# What is actually running on the VPS right now — RUNS FROM YOUR LAPTOP. Read-only.
#
# Answers the two questions you have before any deploy: which ref is on the box, and are
# the containers up. Touches nothing, so it has no --dry-run sibling.
#
# Usage: deploy/vps/status.sh

# shellcheck source=deploy/vps/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

vps_usage() {
  cat <<'USAGE'
Usage: deploy/vps/status.sh

Prints the deployed ref and container status from the configured VPS. Read-only.
USAGE
}

vps_parse_flags "$@"
VPS_DRY_RUN=0
vps_load_settings
vps_show_target

log "--- deployed ref ---"
vps_ssh "cd '${VPS_PATH}' && git log -1 --format='%h %ci %s' 2>/dev/null || echo 'no checkout'"

log "--- containers ---"
vps_ssh "cd '${VPS_PATH}' && docker compose -f deploy/docker-compose.yml --env-file .env ps 2>/dev/null || echo 'compose not up (or docker-compose.yml missing)'"

log "--- disk ---"
vps_ssh "df -h '${VPS_PATH}' | tail -1"
