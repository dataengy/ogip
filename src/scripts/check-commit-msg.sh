#!/usr/bin/env bash
# commit-msg hook — every commit must be bound to a task (a GitHub issue).
#
# Tasks live in .ai/tasks/ and are synced to Issues by src/scripts/tasks_sync.py, so an
# issue number is the binding. Requires a `Refs:/Closes:/Fixes:/Resolves: #12` trailer.
# Merge/revert/fixup commits are exempt (they inherit their parents' binding).
#
# A bare inline `#12` is deliberately NOT accepted: eea77c1's prose "Task file picked up
# GitHub issue #6 via a parallel session's tasks-sync" satisfied a permissive `#[0-9]+`, so
# an unbound commit read as bound — and #6 had already been deleted. Mentioning an issue is
# not declaring that the commit serves it. Kept identical to .ci/steps/commit-binding.sh,
# the un-bypassable half: a looser hook would accept what CI then rejects.
#
# Wired via config/.pre-commit-config.yaml (stage: commit-msg), run by prek.
set -euo pipefail

msg_file="${1:?usage: check-commit-msg.sh <path-to-COMMIT_EDITMSG>}"
# git's own comment lines start with '#': strip them BEFORE looking for '#<n>', otherwise a
# bare "#12" line is indistinguishable from a comment.
body="$(grep -v '^#' "$msg_file" || true)"

if grep -qE '^(Merge|Revert|fixup!|squash!)' <<<"$body"; then
  exit 0
fi

if grep -qE '^[[:space:]]*(Refs|Closes|Fixes|Resolves):[[:space:]]*#[0-9]+' <<<"$body"; then
  exit 0
fi

cat >&2 <<'EOF'
[commit-msg] ERROR: this commit is not bound to a task.

  Every commit must reference the GitHub issue for its task via a trailer, e.g.:
    Refs: #12          (or Closes: #12 / Fixes: #12 / Resolves: #12)

  A bare "#12" in the prose does NOT count — mentioning an issue is not the
  same as declaring that this commit serves it.

  Find the issue:   gh issue list
  No task yet?      add .ai/tasks/<slug>.md, then: just tasks-sync
EOF
exit 1
