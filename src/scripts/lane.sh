#!/usr/bin/env bash
# Lane coordination for parallel agent sessions working the same repo.
#
# Lanes are advisory OBJECT locks (not a whole-repo lock) so concurrent sessions —
# core-pipeline / obs / evidence / dagster / s3 / vps — never block each other but
# also never silently clobber each other. See .ai/STATUS.md for the lane map.
#
# Reuses the global primitive (~/.ai/skills/_scripts/session/agent-session-lock.sh) —
# no lock logic of its own. Called via the direct script, NOT `just … agent-lock`,
# whose recipe re-parses --reason through `bash -c` (parens break it).
#
# Usage: just lane <settle|acquire|check|release> [lane] [reason]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCK_SH="${HOME}/.ai/skills/_scripts/session/agent-session-lock.sh"
LANE="${2:-core-pipeline}"
REASON="${3:-OGIP ${LANE} lane}"

log() { echo "[lane] $*"; }
die() {
  echo "[lane] ERROR: $*" >&2
  exit 1
}

[[ -f "$LOCK_SH" ]] || die "global lock primitive not found: $LOCK_SH"

settle() {
  log "settle-check for '$LANE' …"
  git -C "$REPO" fetch -q origin || true

  local drift
  drift="$(git -C "$REPO" status -sb | head -1)"
  log "branch: $drift"
  if git -C "$REPO" status -sb | head -1 | grep -qE '\[(behind|ahead .* behind)'; then
    log "WARNING: local is BEHIND origin — a parallel session pushed. Rebase before writing."
  fi

  local dirty
  dirty="$(git -C "$REPO" status --porcelain | wc -l | tr -d ' ')"
  [[ "$dirty" != "0" ]] && log "dirty tree: $dirty uncommitted path(s)"

  log "locks held in this repo:"
  if compgen -G "$REPO/.ai/.locks/*.lock" >/dev/null; then
    for l in "$REPO"/.ai/.locks/*.lock; do
      local sid="?" reason="?"
      # shellcheck disable=SC1091
      [[ -f "$l/owner.env" ]] && { sid="$(grep -m1 '^SID=' "$l/owner.env" | cut -d= -f2- | tr -d "'\"")"; }
      [[ -f "$l/owner.env" ]] && { reason="$(grep -m1 '^REASON=' "$l/owner.env" | cut -d= -f2- | tr -d "'\"" | cut -c1-60)"; }
      log "  - $(basename "$l") sid=${sid} reason=${reason}"
    done
  else
    log "  (none)"
  fi
  bash "$LOCK_SH" check --repo "$REPO" --object "$LANE" || true
}

case "${1:-}" in
  settle) settle ;;
  acquire) bash "$LOCK_SH" acquire --repo "$REPO" --object "$LANE" --reason "$REASON" ;;
  check) bash "$LOCK_SH" check --repo "$REPO" --object "$LANE" ;;
  release) bash "$LOCK_SH" release --repo "$REPO" --object "$LANE" ;;
  *) die "usage: just lane <settle|acquire|check|release> [lane] [reason]" ;;
esac
