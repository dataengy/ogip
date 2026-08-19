#!/usr/bin/env bash
# SessionStart hook (#52): is the whole checkout settled — every worktree clean, every local
# branch pushed or contained, no stashes? One line when settled, details when not, so an
# unsettled checkout is visible the moment a session opens (a dirty sibling worktree or an
# unpushed single-copy branch is invisible from the main tree otherwise).
#
# READ-ONLY and network-free: compares against the last-fetched origin/* refs — `just
# preflight` is the full recon (fetch + patch-id dups + PR rollup) when this warns.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$repo_root"
base="origin/dev"
problems=()

while read -r wt _; do
  [[ -d "$wt" ]] || continue
  dirty="$(git -C "$wt" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  [[ "$dirty" == 0 ]] || problems+=("worktree ${wt##*/}: $dirty dirty file(s)")
done < <(git worktree list | awk '{print $1}')

while IFS= read -r branch; do
  if git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    ahead="$(git rev-list --count "origin/$branch..$branch" 2>/dev/null || echo '?')"
    [[ "$ahead" == 0 ]] || problems+=("$branch: $ahead commit(s) ahead of origin/$branch")
  else
    novel="$(git rev-list --count "$base..$branch" 2>/dev/null || echo '?')"
    [[ "$novel" == 0 ]] || problems+=("$branch: UNPUSHED single copy — $novel commit(s) beyond $base")
  fi
done < <(git for-each-ref --format='%(refname:short)' refs/heads/)

stashes="$(git stash list 2>/dev/null | wc -l | tr -d ' ')"
[[ "$stashes" == 0 ]] || problems+=("$stashes stash(es) — machine-local, lost on migration")

if ((${#problems[@]})); then
  echo "⚠ [settle] checkout NOT migration-ready — ${#problems[@]} issue(s):"
  printf '  - %s\n' "${problems[@]}"
  echo "  → commit/push per lane · full recon: just preflight · runbook: docs/runbooks/new-workstation.md"
else
  echo "✅ [settle] worktrees clean · branches pushed/contained · no stashes"
fi
