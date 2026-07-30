#!/usr/bin/env bash
# Assert every commit under review is bound to a GitHub issue — the CI half of the rule.
#
# src/scripts/check-commit-msg.sh (prek, stage commit-msg) enforces this at commit time, but
# that hook is local: it needs `prek install`, and `git commit --no-verify` walks past it. So
# a commit can still reach a PR unbound. This is the gate that cannot be skipped.
#
# Same rule as the hook, deliberately — an inline `#12` or a `Refs:/Closes:/Fixes:` trailer.
# Two different definitions of "bound" would mean CI rejecting what the hook just accepted.
#
# Checks only the commits NEW on this branch — history predates the rule and is published;
# rewriting it would mean force-pushing a branch four other agent sessions commit to.
#
# Usage:
#   .ci/run.sh commit-binding          # vs origin/main (or the PR's base on GitHub)
#   BASE_REF=origin/dev .ci/run.sh commit-binding
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

# On a PR, GitHub tells us the real base; locally, default to origin/main.
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  base="origin/${GITHUB_BASE_REF}"
elif [[ -n "${BASE_REF:-}" ]]; then
  base="$BASE_REF"
else
  base="origin/main"
fi

git rev-parse --verify --quiet "$base" >/dev/null || {
  log "base ref '${base}' not found — skipping (shallow clone or first push)"
  exit 0
}

mapfile -t commits < <(git rev-list "${base}..HEAD" 2>/dev/null || true)
if [[ ${#commits[@]} -eq 0 ]]; then
  log "no new commits vs ${base} — nothing to check"
  exit 0
fi

unbound=()
for sha in "${commits[@]}"; do
  subject="$(git log -1 --format=%s "$sha")"
  # A merge commit records integration, not authored work — it inherits its parents' binding.
  if [[ -n "$(git rev-list --parents -n1 "$sha" | cut -d' ' -f3-)" ]]; then
    continue
  fi
  body="$(git log -1 --format=%B "$sha")"
  if grep -qE '^(Merge|Revert|fixup!|squash!)' <<<"$body"; then
    continue
  fi
  # Trailer only — a bare `#12` anywhere in the body is NOT a binding. Real case: eea77c1's
  # prose "Task file picked up GitHub issue #6 via a parallel session's tasks-sync" matched a
  # permissive `#[0-9]+`, so an unbound commit read as bound — and #6 no longer exists.
  # Mentioning an issue is not the same as declaring the commit serves it.
  if ! grep -qE '^[[:space:]]*(Refs|Closes|Fixes|Resolves):[[:space:]]*#[0-9]+' <<<"$body"; then
    unbound+=("$(git log -1 --format=%h "$sha")  ${subject}")
  fi
done

if [[ ${#unbound[@]} -gt 0 ]]; then
  log "commits with no issue reference (vs ${base}):"
  printf '  %s\n' "${unbound[@]}" >&2
  echo >&2
  echo "  Every commit must name the issue it serves — add a trailer to the message:" >&2
  echo "      Refs: #12        (contributes to)" >&2
  echo "      Closes: #12      (completes)" >&2
  echo "  Amend the last one:  git commit --amend" >&2
  echo "  Older ones:          git rebase -i ${base}   (ONLY if unpushed)" >&2
  exit 1
fi

log "commit binding OK — ${#commits[@]} commit(s) vs ${base}, all reference an issue"
