#!/usr/bin/env bash
# OGIP — bring up the local Airbyte OSS instance for the EVALUATION lane (#41).
#
# Airbyte OSS removed docker-compose (2024-08-23, PR #13544); both supported paths -- abctl
# and Helm -- end in Kubernetes. abctl runs kind (k8s-in-Docker), so this is heavy: it pulls a
# node image plus ~10 Airbyte containers. That weight is the reason for the disk gate below.
#
# This lane is experimental and OFF the `make` path. Nothing here is production ingestion.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

log() { echo "[airbyte] $*"; }
die() {
  echo "[airbyte] ERROR: $*" >&2
  exit 1
}

# Port: the rendered .env wins (config/config.yml -> services.airbyte_port is the SSoT).
# Never a literal here -- see the lane README.
if [[ -f .env ]]; then
  # shellcheck disable=SC1090
  source <(grep -E '^OGIP_AIRBYTE_PORT=' .env || true)
fi
PORT="${OGIP_AIRBYTE_PORT:-}"
[[ -n "$PORT" ]] || die "OGIP_AIRBYTE_PORT unset — run \`make render-env\` first (config SSoT)."

# Disk gate. abctl is k8s-in-Docker; a mid-install exhaustion leaves a half-provisioned
# cluster AND risks truncated writes elsewhere in the repo. Fail BEFORE starting, loudly.
# Precondition recorded in docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md.
#
# MEASURED 2026-07-25 (first real run, this machine): the original 10Gi gate was too low.
# The install pulled ~5GB of images which, extracted into the kind node's containerd (a
# transient ~2x), drove free space from ~13Gi to 2Gi BEFORE Helm even deployed — the cluster
# then went unreachable (TLS handshake timeout) and the install failed. When a Docker VM
# (colima/Docker Desktop) is involved, freed-inside space does NOT return to the host, so the
# gate must budget for the whole peak. Set to 20Gi as the empirical floor. The pull is also
# network-heavy and SLOW on throttled links (29 min observed under corp VPN).
MIN_DISK_GI="${AIRBYTE_MIN_DISK_GI:-20}"
free_gi="$(df -k /System/Volumes/Data 2>/dev/null | awk 'NR==2{printf "%d", $4/1024/1024}')"
if [[ -z "$free_gi" ]]; then
  free_gi="$(df -k . | awk 'NR==2{printf "%d", $4/1024/1024}')"
fi
if ((free_gi < MIN_DISK_GI)); then
  die "disk ${free_gi}Gi < ${MIN_DISK_GI}Gi required. abctl would likely exhaust it mid-install.
       Free space first (/clean-disk), or override with AIRBYTE_MIN_DISK_GI= if you know better."
fi
log "disk ${free_gi}Gi free (min ${MIN_DISK_GI}Gi) — ok"

command -v abctl >/dev/null 2>&1 || die "abctl not installed: brew tap airbytehq/tap && brew install abctl"
docker info >/dev/null 2>&1 || die "Docker unreachable — start it first (this machine uses colima: \`colima start\`)."

log "abctl local install --port ${PORT} (this pulls a kind node image + ~10 containers; slow)"
abctl local install --port "$PORT"

log "up. Credentials: bash experimental/ingestion/airbyte/credentials.sh"
log "UI: http://localhost:${PORT}"
