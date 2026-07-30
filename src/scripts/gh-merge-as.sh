#!/usr/bin/env bash
# Merge (or otherwise act on) a PR under the repo-owner account, then restore whoever was
# active (re-root T9, #40). Encodes the account dance this repo needs: dataengy/ogip PRs and
# issues reject writes from a non-collaborator token, so the flow is switch → op → restore —
# and the restore must survive a failed op (trap), or the operator is silently left on the
# wrong account for everything that follows.
#
# Usage: gh-merge-as.sh <pr-number> [extra `gh pr merge` flags…]   (default: --merge)
#   OGIP_MERGE_ACCOUNT overrides the acting account (default dataengy).
set -euo pipefail

pr="${1:?usage: gh-merge-as.sh <pr-number> [gh pr merge flags…]}"
shift || true
account="${OGIP_MERGE_ACCOUNT:-dataengy}"

prev="$(gh api user --jq .login 2>/dev/null || true)"
if [[ -z "$prev" ]]; then
  echo "gh-merge-as: no active gh login — run \`gh auth login\` first" >&2
  exit 1
fi

restore() {
  if [[ "$prev" != "$account" ]]; then
    gh auth switch -u "$prev" >/dev/null 2>&1 || true
  fi
}
trap restore EXIT

if [[ "$prev" != "$account" ]]; then
  gh auth switch -u "$account" >/dev/null
fi

out="$(gh pr merge "$pr" "${@:---merge}" 2>&1)" && status=0 || status=$?
echo "$out"

if ((status != 0)); then
  # A permission-classifier block is an instruction, not a retry case: hand the exact
  # command to the human instead of hammering it from the wrong context.
  if grep -qiE 'not.*(allowed|permitted)|classifier|blocked' <<<"$out"; then
    echo >&2
    echo "gh-merge-as: the merge action looks policy-gated — run it manually:" >&2
    echo "  gh auth switch -u $account && gh pr merge $pr ${*:---merge} && gh auth switch -u $prev" >&2
  fi
  exit "$status"
fi
