# Runbook — Bootstrap OGIP R&D on a new workstation

> 🇷🇺 Русская версия: [new-workstation.ru.md](new-workstation.ru.md)

- **Trigger:** moving R&D to a fresh machine; the repo must arrive whole (code + secrets +
  reproducible env) with nothing left behind on the old one.
- **Owner:** repo owner. **Severity/urgency:** planned migration, not an incident.

## Preconditions

- On the **old** machine everything is settled: `just preflight` says `clean`
  (no dirty worktrees, no unpushed single-copy branches, no stale locks).
- Secrets escrowed via one opt-in backend
  ([comparison](../comparisons/secrets-management.md)): `just secrets-push` (Bitwarden) or
  `just secrets-hide` + committed blob (git-secret).
- New machine: macOS/Linux with Homebrew or equivalent package manager.

## Steps

1. Install the toolchain:

   ```bash
   brew install git git-lfs uv just gh jq        # core
   brew install bitwarden-cli                    # if secrets.backend = bitwarden
   brew install git-secret gnupg                 # if secrets.backend = git-secret
   git lfs install
   ```

2. Clone and enter (large test datasets are LFS objects — pull them explicitly):

   ```bash
   git clone https://github.com/dataengy/ogip.git && cd ogip
   git lfs pull
   ```

3. Render config and build the env (first `uv` run builds `.run/venv` — takes minutes):

   ```bash
   make render-env
   uv sync
   ```

4. Fill the secret slots from your backend:

   ```bash
   just secrets-doctor                            # readiness report, read-only
   # Bitwarden path:
   bw login && export BW_SESSION="$(bw unlock --raw)"
   just secrets-render-dry && just secrets-render
   # git-secret path (import your GPG key first):
   bash config/.env-secrets-render.sh pull --backend git-secret
   ```

5. Recreate the lane worktrees you actually need (worktrees are machine-local, lanes live
   on origin):

   ```bash
   git worktree add ../OGIP.worktrees/<name> lane/<name>
   ```

6. Gate and run:

   ```bash
   make check
   make run
   ```

## Verify

- `just secrets-doctor` shows every slot `set` (or deliberately `blank`).
- `make check` green; `make run` completes on sample data.
- `git status` clean; `git log --oneline -3` matches origin/dev.

## Rollback

- Nothing here mutates origin — a botched bootstrap is fixed by re-cloning.
- A wrong secrets fill: re-run `make render-env` (merge-safe render keeps only what you
  confirm) or blank the slot by hand and `just secrets-render` again.

## Escalation

- Secrets backend unusable → the loud `doctor`/`pull` error names the exact fix
  (unlock command, missing GPG key). Infra/DevOps beyond that is handled separately
  ([ADR-0012](../adr/ADR-0012-github-ci-manual-vps-deploy.md)).
