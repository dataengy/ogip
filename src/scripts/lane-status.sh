#!/usr/bin/env bash
# lane-status.sh — the "check env, parallel sessions & locks" ritual as ONE read-only command.
#
# Answers, in a single pass, the questions every session asks before writing to this shared
# checkout (several agent sessions commit to the same branch — see .ai/STATUS.md):
#
#   LOCKS  — every lock actually on disk (.ai/.locks/), each classified live/STALE from its
#            own OWNER_AT+TTL, with holder sid + age. Disk is the truth: lanes are listed from
#            the lock store, never from a hardcoded table that drifts from reality.
#   GIT    — branch, ahead/behind origin (after fetch), and the dirty files. Dirty files here
#            are usually ANOTHER lane's in-flight work: report them, never touch them.
#   SETTLE — the global settle-check verdict (reflog churn), when the primitive is available.
#   VERDICT— GO (no live foreign locks) / COORDINATE (someone is live — name them).
#
# Wait mode turns "watch and wait otherwise" into a deterministic loop instead of a human
# re-running the snapshot: poll until the named lane is claimable (lock absent OR stale).
#
# Usage:
#   lane-status.sh                              # full snapshot + verdict
#   lane-status.sh <lane>                       # one lane: exit 0 claimable, 1 held-live
#   lane-status.sh --wait <lane> [--timeout S] [--interval S]   # block until claimable
#   lane-status.sh --repo DIR ...               # another checkout (mainly for tests)
#
# Exit codes:
#   snapshot : 0 always (it is a report)
#   <lane>   : 0 claimable (free or stale) · 1 held by a live session · 4 bad usage
#   --wait   : 0 became claimable · 3 timed out · 4 bad usage
#
# Read-only by design: no lock is ever acquired, broken, or released here — claiming is
# lane.sh's job. The only side effect is `git fetch` (remote-tracking refs), same as settle.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETTLE_SH="${HOME}/.ai/skills/_scripts/session/settle-check.sh"
MY_SID="${CLAUDE_CODE_SESSION_ID:-}"

WAIT_LANE="" QUERY_LANE="" TIMEOUT=1800 INTERVAL=30

log() { echo "[lane-status] $*"; }
die() {
  echo "[lane-status] ERROR: $*" >&2
  exit 4
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$(cd "${2:?--repo needs a dir}" && pwd)"; shift 2 ;;
    --wait) WAIT_LANE="${2:?--wait needs a lane}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    --interval) INTERVAL="${2:?}"; shift 2 ;;
    -h | --help) sed -n '2,31p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) die "unknown flag: $1" ;;
    *) [[ -z "$QUERY_LANE" ]] || die "one lane at most"; QUERY_LANE="$1"; shift ;;
  esac
done

git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a git work tree: $REPO"
LOCKS_DIR="$REPO/.ai/.locks"

# Same slug rule as agent-session-lock.sh — the two must never disagree on a lane's lock name.
lock_dir_for() {
  printf '%s/obj--%s.lock' "$LOCKS_DIR" "$(printf '%s' "$1" | tr '/ ' '__' | tr -cd 'A-Za-z0-9._-')"
}

# Prints "state|sid|age|reason" for one lock dir; state ∈ FREE|LIVE|STALE|MINE.
probe() {
  local dir="$1" meta sid at ttl now age rem reason
  [[ -d "$dir" ]] || { printf 'FREE|||'; return 0; }
  meta="$dir/owner.env"
  sid="" at="" ttl="" reason=""
  if [[ -f "$meta" ]]; then
    # owner.env is `KEY=%q` lines; strip the quoting rather than sourcing foreign shell code.
    sid="$(sed -n "s/^OWNER_SID=//p" "$meta" | head -1 | tr -d "'\"")"
    at="$(sed -n "s/^OWNER_AT=//p" "$meta" | head -1 | tr -d "'\"")"
    ttl="$(sed -n "s/^OWNER_TTL=//p" "$meta" | head -1 | tr -d "'\"")"
    # owner.env values are printf-%q quoted — strip the escaping for display
    # shellcheck disable=SC1003  # `tr -d '\\'` deletes backslashes; not a quote-escape typo
    reason="$(sed -n "s/^OWNER_REASON=//p" "$meta" | head -1 | tr -d '\\' | tr -d "'\"" | cut -c1-60)"
  fi
  now="$(date +%s)"
  if [[ -z "$at" || -z "$ttl" ]]; then
    printf 'STALE|%s|?|%s' "$sid" "$reason"   # garbled meta = stale, same call the lock makes
    return 0
  fi
  age=$((now - at)); rem=$((ttl - age))
  if [[ -n "$MY_SID" && "$sid" == "$MY_SID" ]]; then
    printf 'MINE|%s|%ss|%s' "$sid" "$age" "$reason"
  elif [[ "$rem" -le 0 ]]; then
    printf 'STALE|%s|%ss over TTL|%s' "$sid" "$((-rem))" "$reason"
  else
    printf 'LIVE|%s|%ss left|%s' "$sid" "$rem" "$reason"
  fi
}

claimable() {  # a lane is claimable when its lock is absent, stale, or already mine
  local state
  state="$(probe "$(lock_dir_for "$1")" | cut -d'|' -f1)"
  [[ "$state" != "LIVE" ]]
}

# ── wait mode ───────────────────────────────────────────────────────────────
if [[ -n "$WAIT_LANE" ]]; then
  deadline=$(($(date +%s) + TIMEOUT))
  while true; do
    if claimable "$WAIT_LANE"; then
      log "lane '$WAIT_LANE' is claimable — go (lane.sh acquire $WAIT_LANE \"reason\")"
      exit 0
    fi
    if (($(date +%s) >= deadline)); then
      log "timed out after ${TIMEOUT}s — lane '$WAIT_LANE' still held live:"
      probe "$(lock_dir_for "$WAIT_LANE")" | awk -F'|' '{printf "  holder sid=%s (%s) reason=%s\n", $2, $3, $4}'
      exit 3
    fi
    sleep "$INTERVAL"
  done
fi

# ── single-lane query ───────────────────────────────────────────────────────
if [[ -n "$QUERY_LANE" ]]; then
  IFS='|' read -r state sid age reason <<<"$(probe "$(lock_dir_for "$QUERY_LANE")")"
  log "$QUERY_LANE: $state${sid:+ sid=$sid}${age:+ ($age)}${reason:+ reason=$reason}"
  [[ "$state" != "LIVE" ]]
  exit $?
fi

# ── full snapshot ───────────────────────────────────────────────────────────
echo "── LOCKS (${LOCKS_DIR#"$REPO"/}) ──"
live_lanes=() stale_lanes=()
if [[ -d "$LOCKS_DIR" ]]; then
  found=0
  for dir in "$LOCKS_DIR"/*.lock; do
    [[ -d "$dir" ]] || continue
    found=1
    name="$(basename "$dir" .lock)"
    IFS='|' read -r state sid age reason <<<"$(probe "$dir")"
    printf '  %-24s %-6s %s%s\n' "$name" "$state" "${sid:0:12}${age:+ ($age)}" "${reason:+  — $reason}"
    case "$state" in
      LIVE) live_lanes+=("$name") ;;
      STALE) stale_lanes+=("$name") ;;
    esac
  done
  [[ "$found" -eq 1 ]] || echo "  (no locks on disk — every lane is FREE)"
else
  echo "  (no lock store — every lane is FREE)"
fi

echo "── GIT ──"
git -C "$REPO" fetch -q origin 2>/dev/null || log "fetch failed (offline?) — ahead/behind may be stale"
branch="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
upstream="origin/$branch"
if git -C "$REPO" rev-parse --verify -q "$upstream" >/dev/null; then
  ahead="$(git -C "$REPO" rev-list --count "$upstream"..HEAD)"
  behind="$(git -C "$REPO" rev-list --count HEAD.."$upstream")"
else
  ahead="?" behind="?"
fi
echo "  branch $branch · ahead $ahead / behind $behind"
dirty="$(git -C "$REPO" status --porcelain)"
if [[ -n "$dirty" ]]; then
  echo "  dirty (likely OTHER lanes' in-flight work — report, don't touch):"
  printf '%s\n' "$dirty" | sed 's/^/    /'
else
  echo "  working tree clean"
fi

echo "── SETTLE ──"
if [[ -f "$SETTLE_SH" ]]; then
  # settle-check exits 3 on DIRTY — that is its verdict, not our failure; a snapshot reports.
  bash "$SETTLE_SH" --repo "$REPO" 2>&1 | grep -v '^$' | tail -1 | sed 's/^/  /' || true
else
  echo "  (settle-check primitive not installed — skipped)"
fi

echo "── VERDICT ──"
if [[ ${#live_lanes[@]} -gt 0 ]]; then
  echo "  COORDINATE — live lanes held: ${live_lanes[*]}. Anything else is claimable."
else
  echo "  GO — no live foreign locks.${stale_lanes[0]:+ Stale (claim over them): ${stale_lanes[*]}.}"
fi
[[ "$behind" != "?" && "$behind" != "0" ]] && echo "  NOTE: behind $upstream by $behind — pull --ff-only before writing."
exit 0
