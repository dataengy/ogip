#!/usr/bin/env bash
# Merge (or otherwise act on) a PR under the repo-owner account, then restore whoever was
# active (re-root T9, #40). Encodes the account dance this repo needs: dataengy/ogip PRs and
# issues reject writes from a non-collaborator token, so the flow is switch → op → restore —
# and the restore must survive a failed op (trap), or the operator is silently left on the
# wrong account for everything that follows.
#
# Merge policy (#57; shared SSoT ~/.ai/skills/.settings/branch_rules.yml#pr_merge): with no
# explicit flags the merge is --squash (the only method the repo allows since 2026-08-20),
# plus --delete-branch unless the PR's head is a long-lived branch — GitHub's auto-delete
# already skips protected branches (main/dev/ru-docs), but the flag must not re-add deletion
# for any other branch that lives between releases. ru-docs never participates in PRs at all
# (#55): refuse rather than merge. After a squash release into main, the head branch must
# back-merge origin/main — squash breaks ancestry, and the next release PR would otherwise
# replay the whole history.
#
# Usage: gh-merge-as.sh <pr-number> [extra `gh pr merge` flags…]   (default: policy flags)
#   OGIP_MERGE_ACCOUNT overrides the acting account (default dataengy).
set -euo pipefail

pr="${1:?usage: gh-merge-as.sh <pr-number> [gh pr merge flags…]}"
shift || true
account="${OGIP_MERGE_ACCOUNT:-dataengy}"
long_lived="dev develop main master prod staging ru-docs"

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

read -r head base < <(gh pr view "$pr" --json headRefName,baseRefName \
  --jq '"\(.headRefName) \(.baseRefName)"')

if [[ "$head" == "ru-docs" || "$base" == "ru-docs" ]]; then
  echo "gh-merge-as: ru-docs never merges — it is the standalone bilingual view (#55, #57)" >&2
  exit 1
fi

if (($# == 0)); then
  set -- --squash
  case " $long_lived " in
    *" $head "*) ;;
    *) set -- "$@" --delete-branch ;;
  esac
fi

out="$(gh pr merge "$pr" "$@" 2>&1)" && status=0 || status=$?
echo "$out"

if ((status == 0)) && [[ "$base" == "main" ]]; then
  case " $long_lived " in
    *" $head "*)
      echo
      echo "gh-merge-as: squash release landed — $head must back-merge $base now (see #57):"
      echo "  git checkout $head && git pull --ff-only origin $head \\"
      echo "    && git fetch origin && git merge origin/$base && git push origin $head"
      ;;
  esac
fi

if ((status != 0)); then
  # A permission-classifier block is an instruction, not a retry case: hand the exact
  # command to the human instead of hammering it from the wrong context.
  if grep -qiE 'not.*(allowed|permitted)|classifier|blocked' <<<"$out"; then
    echo >&2
    echo "gh-merge-as: the merge action looks policy-gated — run it manually:" >&2
    echo "  gh auth switch -u $account && gh pr merge $pr $* && gh auth switch -u $prev" >&2
  fi
  exit "$status"
fi
