#!/usr/bin/env bash
# commit-msg hook — every commit must be bound to a task (a GitHub issue).
#
# Tasks live in .ai/tasks/ and are synced to Issues by src/scripts/tasks_sync.py, so an
# issue number is the binding. Accepts an inline `#12` or a `Refs:/Closes:/Fixes: #12`
# trailer. Merge/revert/fixup commits are exempt (they inherit their parents' binding).
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

if grep -qE '#[0-9]+' <<<"$body"; then
  exit 0
fi

cat >&2 <<'EOF'
[commit-msg] ERROR: this commit is not bound to a task.

  Every commit must reference the GitHub issue for its task, e.g.:
    Refs: #12          (or Closes: #12 / Fixes: #12, or an inline #12)

  Find the issue:   gh issue list
  No task yet?      add .ai/tasks/<slug>.md, then: just tasks-sync
EOF
exit 1
