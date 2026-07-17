#!/usr/bin/env bash
# Ship loop — "commit + push after every successful run" (D15) as ONE command, so commits
# stay frequent, every green run is recorded, tasks sync to GitHub Issues, and the result
# is announced to Telegram.
#
#   bash src/scripts/ship.sh "feat(spec): add rawg contract"        # stage this lane's paths
#   bash src/scripts/ship.sh "fix(ci): x" .ci/steps/lint.sh          # stage exactly these paths
#
# SHARED WORKING TREE: parallel agent sessions (obs / evidence / dagster / s3 / vps) run in
# THIS SAME checkout. So we never `git add -A` — that would sweep their in-flight work into
# our commit. We stage only this lane's allowlist (or the explicit paths given), and refuse
# to touch contested shared files unless we hold their object lock.
#
# Steps: lane guard → settle → make check → scoped commit → push → watch CI → tasks-sync → tg-inform.
# Env: LANE (default core-pipeline), SKIP_CI_WATCH=1, SKIP_TG=1, SKIP_SYNC=1.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

MSG="${1:-}"
shift || true
EXPLICIT_PATHS=("$@")
LANE="${LANE:-core-pipeline}"
TG_JF="${HOME}/.ai/scripts/telegram/Justfile"
LOCK_SH="${HOME}/.ai/skills/_scripts/session/agent-session-lock.sh"

log() { echo "[ship] $*"; }
die() {
  echo "[ship] ERROR: $*" >&2
  exit 1
}

[[ -n "$MSG" ]] || die 'usage: ship.sh "type(scope): message" [paths...]'

# Paths this lane owns. Contested shared files are deliberately EXCLUDED — they need their
# own object lock and must be passed explicitly (see shared_guard below).
lane_paths() {
  case "$1" in
    core-pipeline) echo "spec src/ogip src/tests src/scripts/lane.sh src/scripts/ship.sh ingestion transform pipelines config .ci .github integrations/github notebooks docs .ai" ;;
    obs) echo "deploy/obs src/scripts/obs-verify.sh src/scripts/obs-smoke-log.sh" ;;
    evidence) echo "experimental/bi/evidence" ;;
    dagster) echo "experimental/orchestration" ;;
    s3) echo "deploy/s3" ;;
    vps) echo "deploy/vps" ;;
    *) die "unknown lane '$1' — add it to lane_paths()" ;;
  esac
}

# Files EVERY lane extends (the SSoT config, build files, shared status). They belong to no
# single lane, so they may only be committed by the session holding their object lock.
CONTESTED=(
  pyproject.toml uv.lock Justfile Makefile .gitignore
  config/config.yml deploy/docker-compose.yml .ai/STATUS.md
)

lock_object_for() {
  case "$1" in
    pyproject.toml | uv.lock) echo "pyproject" ;;
    Justfile | Makefile | .gitignore) echo "build-files" ;;
    config/config.yml) echo "config-ssot" ;;
    deploy/docker-compose.yml) echo "deploy-compose" ;;
    .ai/STATUS.md) echo "status-doc" ;;
    *) echo "" ;;
  esac
}

holds_lock_for() {
  local obj
  obj="$(lock_object_for "$1")"
  [[ -z "$obj" ]] && return 0
  bash "$LOCK_SH" check --repo "$REPO" --object "$obj" 2>/dev/null | grep -q 'HELD-BY-SELF'
}

# Drop contested files from the index unless we hold their lock — protects parallel sessions'
# in-flight edits to the shared SSoT from being swept into our commit.
unstage_unlocked_contested() {
  local f
  for f in "${CONTESTED[@]}"; do
    if git diff --cached --name-only | grep -qxF "$f"; then
      if ! holds_lock_for "$f"; then
        git restore --staged -- "$f" 2>/dev/null || git reset -q HEAD -- "$f"
        log "unstaged contested '$f' (lock '$(lock_object_for "$f")' not held by us)"
      fi
    fi
  done
}

# 1. Lane guard — never write while another session holds this lane.
log "lane guard ($LANE)"
bash "$LOCK_SH" check --repo "$REPO" --object "$LANE" 2>/dev/null | grep -q 'HELD-BY-SELF' ||
  die "lane '$LANE' not held by this session — run: bash src/scripts/lane.sh acquire $LANE"

# 2. Settle — refuse to push onto a parallel session's work.
git fetch -q origin || true
if git status -sb | head -1 | grep -q 'behind'; then
  die "local is BEHIND origin (a parallel session pushed) — rebase first: git pull --rebase"
fi

# 3. Gates.
log "make check"
make check

# 4. Scoped stage — NEVER `git add -A` in a shared tree.
if [[ ${#EXPLICIT_PATHS[@]} -gt 0 ]]; then
  for p in "${EXPLICIT_PATHS[@]}"; do
    holds_lock_for "$p" ||
      die "'$p' is contested — acquire its lock: bash src/scripts/lane.sh acquire $(lock_object_for "$p")"
  done
  git add -- "${EXPLICIT_PATHS[@]}"
else
  read -r -a paths <<<"$(lane_paths "$LANE")"
  for p in "${paths[@]}"; do
    # `if`, not `[[ ]] && …`: a false test on the final iteration would make the loop
    # exit non-zero and trip `set -e`.
    if [[ -e "$p" ]]; then git add -- "$p"; fi
  done
fi

unstage_unlocked_contested

# Report what we deliberately left alone (other sessions' in-flight work).
FOREIGN="$(git status --porcelain | grep -E '^(\?\?| M| D)' | awk '{print $2}' || true)"
[[ -n "$FOREIGN" ]] && log "left for other lanes: $(echo "$FOREIGN" | tr '\n' ' ')"

if git diff --cached --quiet; then
  log "nothing staged for this lane — tree clean"
else
  git commit -q -F - <<EOF
${MSG}

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
  log "committed $(git rev-parse --short HEAD)"
fi

# 5. Push.
git push -q origin HEAD
SHA="$(git rev-parse --short HEAD)"
log "pushed $SHA"

# 6. Watch CI.
CI_RESULT="skipped"
if [[ "${SKIP_CI_WATCH:-0}" != "1" ]] && command -v gh >/dev/null 2>&1; then
  sleep 6
  RID="$(gh run list --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || true)"
  if [[ -n "$RID" ]]; then
    log "watching CI run $RID"
    if gh run watch "$RID" --exit-status --interval 12 >/dev/null 2>&1; then CI_RESULT="green"; else CI_RESULT="RED"; fi
    log "CI: $CI_RESULT"
  fi
fi

# 7. Sync tasks → GitHub Issues.
if [[ "${SKIP_SYNC:-0}" != "1" && -f integrations/github/tasks_sync.py ]]; then
  log "tasks-sync → GitHub Issues"
  uv run python integrations/github/tasks_sync.py || log "WARN: tasks-sync failed (non-fatal)"
fi

# 8. Telegram inform (delegates to the shared tg-inform primitive; never fails the ship).
if [[ "${SKIP_TG:-0}" != "1" && -f "$TG_JF" ]]; then
  BODY="$(printf 'lane   %s\ncommit %s\nCI     %s\nmsg    %s' "$LANE" "$SHA" "$CI_RESULT" "$MSG")"
  EMOJI="🚀"
  [[ "$CI_RESULT" == "RED" ]] && EMOJI="🔴"
  just -f "$TG_JF" tg-inform -- --title "OGIP ship · $LANE" --emoji "$EMOJI" \
    --body "$BODY" --pre --ctx-from "$REPO" >/dev/null 2>&1 || log "WARN: tg-inform failed (non-fatal)"
fi

[[ "$CI_RESULT" == "RED" ]] && die "CI is RED for $SHA"
log "done: $SHA (CI $CI_RESULT)"
