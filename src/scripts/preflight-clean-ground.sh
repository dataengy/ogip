#!/usr/bin/env bash
# Pre-restructure recon (re-root T9, #40): is the ground clean enough for a big landing?
#
# READ-ONLY. Prints four tables + a verdict; exits 0 on `clean`, 1 on `not-clean` so it can
# gate a lane-landing recipe. The checks encode what the 2026-07-30 finalization run had to
# discover by hand: diverged local branches, dirty shared checkout, stale session locks in
# WORKTREE-LOCAL stores (invisible from the main tree), unpushed single-copy branches, and
# local commits whose content already lives on origin/dev (patch-id duplicates — a rebase
# would drop them, so they are noise, not work).
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
base="${OGIP_PREFLIGHT_BASE:-origin/dev}"
blockers=()

echo "== preflight-clean-ground · base=$base · $(date -u +%Y-%m-%dT%H:%M:%SZ) =="

git fetch --quiet origin --prune 2>/dev/null || echo "(fetch failed — using stale refs)"

echo
echo "-- branches (vs $base: behind/ahead · contained · pushed) --"
while IFS= read -r branch; do
  counts="$(git rev-list --left-right --count "$base...$branch" 2>/dev/null || echo '? ?')"
  behind="${counts%%$'\t'*}"; ahead="${counts##*$'\t'}"
  contained="no"; if [[ "$ahead" == 0 ]]; then contained="yes"; fi
  upstream="$(git rev-parse --abbrev-ref "$branch@{upstream}" 2>/dev/null || true)"
  pushed="${upstream:-UNPUSHED}"
  dup=""
  if [[ "$ahead" != 0 && "$ahead" != "?" ]]; then
    # `git cherry`: commits marked `-` are content-identical to something on the base.
    dups="$(git cherry "$base" "$branch" 2>/dev/null | grep -c '^-' || true)"
    if [[ "$dups" == "$ahead" ]]; then dup=" (all $ahead = patch-id dups of $base)"; fi
  fi
  printf '  %-42s %s/%s contained=%s %s%s\n' "$branch" "$behind" "$ahead" "$contained" "$pushed" "$dup"
  if [[ "$pushed" == "UNPUSHED" && "$contained" == "no" && -z "$dup" ]]; then
    blockers+=("$branch: unpushed unique commits (single copy)")
  fi
done < <(git for-each-ref --format='%(refname:short)' refs/heads/)

echo
echo "-- worktrees (dirty counts) --"
while read -r wt _; do
  [[ -d "$wt" ]] || continue
  dirty="$(git -C "$wt" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  printf '  %-70s dirty=%s\n' "$wt" "$dirty"
  if [[ "$dirty" != 0 && "$wt" != "$repo_root" ]]; then
    blockers+=("worktree $wt: $dirty dirty files")
  fi
done < <(git worktree list | awk '{print $1}')

echo
echo "-- session locks (incl. worktree-local stores) --"
while read -r wt _; do
  lockdir="$wt/.ai/.locks"
  [[ -d "$lockdir" ]] || continue
  for lock in "$lockdir"/*.lock; do
    [[ -d "$lock" ]] || continue
    owner="$lock/owner.env"
    pid="$(grep -m1 '^OWNER_PID=' "$owner" 2>/dev/null | cut -d= -f2 || true)"
    expires="$(grep -m1 '^OWNER_EXPIRES=' "$owner" 2>/dev/null | cut -d= -f2 || true)"
    # STALE needs BOTH signals: acquiring hooks exit immediately, so a dead pid alone is
    # normal for a live session — only a dead pid past its TTL expiry is abandoned.
    state="LIVE"
    if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
      if [[ -z "$expires" || "$expires" -lt "$(date +%s)" ]]; then state="STALE(pid dead, expired)"; fi
    fi
    printf '  %-50s %s\n' "${lock#"$repo_root/"}" "$state"
    if [[ "$state" != LIVE ]]; then blockers+=("stale lock: $lock"); fi
  done
done < <(git worktree list | awk '{print $1}')

echo
echo "-- open PRs (mergeable · checks) --"
if command -v gh >/dev/null 2>&1; then
  gh pr list --state open --json number,title,mergeable,statusCheckRollup \
    --jq '.[] | "  #\(.number) \(.title[0:60]) mergeable=\(.mergeable) checks=\([.statusCheckRollup[]?.conclusion // "PENDING"] | group_by(.) | map("\(.[0])×\(length)") | join(","))"' \
    2>/dev/null || echo "  (gh query failed)"
else
  echo "  (gh not installed — skipped)"
fi

echo
if ((${#blockers[@]})); then
  echo "VERDICT: not-clean — ${#blockers[@]} blocker(s):"
  printf '  - %s\n' "${blockers[@]}"
  exit 1
fi
echo "VERDICT: clean"
