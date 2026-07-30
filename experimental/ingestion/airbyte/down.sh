#!/usr/bin/env bash
# OGIP — tear down the local Airbyte OSS instance (evaluation lane, #41).
#
# Default is a plain uninstall, which LEAVES the persisted data volumes so a later `up.sh`
# resumes the same instance. Pass --persisted to also drop them (full reset, unrecoverable).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

log() { echo "[airbyte] $*"; }
die() {
  echo "[airbyte] ERROR: $*" >&2
  exit 1
}

command -v abctl >/dev/null 2>&1 || die "abctl not installed — nothing to tear down."

if [[ "${1:-}" == "--persisted" ]]; then
  log "abctl local uninstall --persisted (DROPS persisted volumes — unrecoverable)"
  abctl local uninstall --persisted
else
  log "abctl local uninstall (persisted volumes kept; --persisted to drop them)"
  abctl local uninstall
fi

log "down."
