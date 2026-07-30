#!/usr/bin/env bash
# Per-lane git worktrees — the structural fix for parallel agent sessions.
#
# WHY: every session used to share ONE checkout, so sessions swept each other's files into
# commits, one lane's in-flight file turned everyone's `make check` red, and a `git checkout`
# moved HEAD under all of them. A worktree gives each lane its own working directory and
# branch over the SAME .git object store — cheap (uv hardlinks its venv from the shared
# cache), isolated, and merged through PRs instead of luck.
#
#   just worktree add obs          # create ../OGIP.worktrees/obs on branch lane/obs off dev
#   just worktree list             # show every lane worktree + its branch
#   just worktree path obs         # print the path (for `cd "$(just worktree path obs)"`)
#   just worktree remove obs       # detach it (branch and commits survive)
#
# Flow: lane/<name> → PR → dev → PR → main. Locks then guard only merges, not files.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && git rev-parse --show-toplevel)"
ROOT="$(dirname "$REPO")/$(basename "$REPO").worktrees"
BASE="${BASE_BRANCH:-dev}"

log() { echo "[worktree] $*"; }
die() {
  echo "[worktree] ERROR: $*" >&2
  exit 1
}

LANES=(core-pipeline obs evidence dagster s3 vps)

is_lane() {
  local l
  for l in "${LANES[@]}"; do [[ "$l" == "$1" ]] && return 0; done
  return 1
}

add() {
  local lane="${1:?usage: worktree add <lane>}"
  is_lane "$lane" || die "unknown lane '$lane' (known: ${LANES[*]})"
  local path="$ROOT/$lane" branch="lane/$lane"

  [[ -d "$path" ]] && {
    log "already exists: $path"
    exit 0
  }
  mkdir -p "$ROOT"
  git -C "$REPO" fetch -q origin || true

  # Reuse the branch if it already exists (locally or on the remote); else fork it off BASE.
  if git -C "$REPO" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$REPO" worktree add "$path" "$branch"
  elif git -C "$REPO" ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
    git -C "$REPO" worktree add "$path" --track -b "$branch" "origin/$branch"
  else
    git -C "$REPO" worktree add "$path" -b "$branch" "origin/$BASE" 2>/dev/null ||
      git -C "$REPO" worktree add "$path" -b "$branch" "$BASE"
  fi
  log "lane '$lane' → $path (branch $branch, off $BASE)"
  log "next:  cd '$path' && make bootstrap"
}

case "${1:-}" in
  add) add "${2:-}" ;;
  list) git -C "$REPO" worktree list ;;
  path)
    is_lane "${2:-}" || die "unknown lane '${2:-}'"
    echo "$ROOT/${2}"
    ;;
  remove)
    is_lane "${2:-}" || die "unknown lane '${2:-}'"
    git -C "$REPO" worktree remove "$ROOT/${2}" "${3:-}"
    log "removed worktree for '${2}' (branch lane/${2} kept)"
    ;;
  *) die "usage: just worktree <add|list|path|remove> [lane]  (lanes: ${LANES[*]})" ;;
esac
