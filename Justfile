# OGIP — every developer/infra/spec op lives here. The Makefile is the pipeline launcher
# (one target per pipeline) and forwards any other `make <op>` here. Runtime env: uv → .run/venv.

export UV_PROJECT_ENVIRONMENT := ".run/venv"

compose := "docker compose -f deploy/docker-compose.yml --env-file .env"
obs := "docker compose -f deploy/obs/docker-compose.obs.yml --env-file .env"
prek := "uvx prek --config config/.pre-commit-config.yaml"

# List recipes (default)
default:
    @just --list

# ─── Setup & config ───────────────────────────────────────────────────────────
# Install deps (uv → .run/venv), pre-commit (prek) hooks, render .env
bootstrap:
    uv sync
    {{prek}} install
    uv run python config/.env-render.py

# Re-render .env from config/config.yml (merge-safe on secrets)
render-env:
    uv run python config/.env-render.py

# ─── Quality gates ────────────────────────────────────────────────────────────
# Ruff lint + format check + SQL lint
lint:
    # explicit nested path: `ruff check .` skips experimental/orchestration/dagster_ogip
    # locally (nested-project boundary) while CI's clean runner reaches it — #39
    uv run ruff check . experimental/orchestration/dagster_ogip/src
    uv run ruff format --check . experimental/orchestration/dagster_ogip/src
    @just sql-lint

# Auto-fix lint + format
fmt:
    uv run ruff check --fix .
    uv run ruff format .

# Pyright strict
typecheck:
    uv run pyright

# Fast tests: smoke + unit (integration + e2e excluded)
test:
    uv run pytest -m "not integration and not e2e"

test-smoke:
    uv run pytest -m smoke

test-unit:
    uv run pytest -m "not smoke and not integration and not e2e"

test-integration:
    uv run pytest -m integration

# E2E: run the Prefect/Dagster setups end-to-end and assert results
test-e2e:
    uv run pytest -m e2e

# All quality gates (CI parity)
check: lint typecheck test dq-check

# Run the shared CI steps exactly as GitHub Actions runs them
ci:
    bash .ci/run.sh lint
    bash .ci/run.sh typecheck
    bash .ci/run.sh test
    bash .ci/run.sh lfs-guard

# One-time per clone: enable Git LFS hooks (large test datasets)
lfs-install:
    git lfs install --local

# Run all pre-commit hooks over the whole tree
hooks:
    {{prek}} run --all-files

# Remove caches/artifacts (keeps .run/venv and data)
clean:
    rm -rf .run/pytest_cache .run/ruff_cache .run/.coverage .run/junit.xml dist
    find . -type d -name __pycache__ -not -path './.run/*' -prune -exec rm -rf {} +

# ─── Infrastructure ───────────────────────────────────────────────────────────
# Start core services (Postgres, Prefect) and wait for health
up: render-env
    {{compose}} up -d --wait postgres prefect
    @echo "Prefect UI: http://localhost:4200"
    open http://localhost:4200

# Stop services (volumes preserved)
down:
    {{compose}} down

# Service status
ps:
    {{compose}} ps

# Tail service logs
logs:
    {{compose}} logs -f --tail=100

# Start observability stack (VictoriaMetrics, Loki, Alloy, Grafana)
obs-up: render-env
    @mkdir -p .run/logs
    {{obs}} up -d --wait
    @just obs-verify

# Stop observability stack (volumes preserved)
obs-down:
    {{obs}} down

# Start MinIO (S3-compatible lake) + create the raw bucket
storage-up: render-env
    {{compose}} --profile storage up -d --wait minio
    {{compose}} --profile storage run --rm minio-init
    @echo "MinIO console: http://localhost:9001 — dev keys ogipminio / ogipminio123"

# Stop MinIO (data volume preserved)
storage-down:
    {{compose}} --profile storage stop minio

# Open JupyterLab on the ML-ready datasets
notebook:
    uv run jupyter lab --notebook-dir notebooks

# --- Run profiles (A12): orchestrator × engine setups ---
# Launch a run profile from config/config.yml → run_profiles (src/scripts/run-profile.py).
run-profile name="prefect-sqlmesh":
    uv run python src/scripts/run-profile.py {{name}}

# --- Spec compiler (ADR-0005): regenerate transform/ engine projects from spec/sql ---
spec-compile engine="all":
    uv run python -m ogip.spec_compile {{engine}}

# Cross-engine parity: every generated engine builds the SAME data from one spec.
spec-verify *args:
    uv run python src/scripts/spec-compile-verify.py {{args}}

# Validate the normative ODTS/ODOS packages and their conformance examples.
standards-validate:
    uv run pytest src/tests/unit/test_standard_packages.py

# --- Prefect (integrations/prefect: deploy + trigger via CLI/API) ---
prefect-deploy:
    uv run python integrations/prefect/deploy.py

prefect-run flow="ingest_transform_publish":
    uv run python integrations/prefect/trigger.py {{flow}}

# --- Task sync: .ai/tasks/ → GitHub Issues (A14/D12). Mutating → has a -dry sibling. ---
tasks-sync *args:
    uv run python src/scripts/tasks_sync.py {{args}}

tasks-sync-dry *args:
    uv run python src/scripts/tasks_sync.py --dry-run {{args}}

# --- Data quality: run spec/dq assertions ---
dq-check:
    uv run python dq/run.py

# --- Linters ---
sql-lint:
    bash .ci/steps/sql-lint.sh

bash-lint:
    bash .ci/steps/bash-lint.sh

# --- Secrets: opt-in backends (Bitwarden / git-secret, ADR-0011) ---
# pull fills only BLANK slots in .env (merge-safe); values are never printed.
secrets-render:
    bash config/.env-secrets-render.sh pull
secrets-render-dry:
    bash config/.env-secrets-render.sh pull --dry-run
# push the FILLED slots of .env into the Bitwarden secure-note item (creates it on first push)
secrets-push:
    bash config/.env-secrets-render.sh push
secrets-push-dry:
    bash config/.env-secrets-render.sh push --dry-run
# git-secret: export filled slots -> plaintext -> committed *.secret blob (and back)
secrets-hide:
    bash config/.env-secrets-render.sh hide
secrets-hide-dry:
    bash config/.env-secrets-render.sh hide --dry-run
secrets-reveal:
    bash config/.env-secrets-render.sh reveal
# one-time git-secret init (needs a GPG secret key; pass an email to override git config)
secrets-setup-git-secret *args:
    bash config/.env-secrets-render.sh setup-git-secret {{ args }}
# read-only readiness report for both backends
secrets-doctor:
    bash config/.env-secrets-render.sh doctor

# --- Repo hygiene: fail if stray files land in the root (root-lean rule) ---
tidy-root:
    bash .ci/steps/structure-validate.sh

# --- Repo hygiene: large test datasets must be LFS pointers, not raw blobs ---
lfs-guard:
    bash .ci/steps/lfs-guard.sh

# --- Data-source registry (SSoT: ~/.ai/skills; spec/sources/ here is its projection) ---
# Passthroughs so OGIP devs need no $JF incantation. Registry-less machines: probe/route
# fail loud (registry required); sources-drift self-skips (see the script header).
sources_jf := home_directory() / ".ai/skills/_scripts/de/ingestion/Justfile"

# Live-probe every registered source (real GETs; FORBIDDEN entries never fetched).
sources-probe-all:
    just -f "{{sources_jf}}" probe-all

# Route one source (or all) to its ingestion tool with the recorded reason.
sources-route key="--all":
    just -f "{{sources_jf}}" {{ if key == "--all" { "route-all" } else { "route " + key } }}

# Full drift gate: registry well-formed + engine drift + stale projections. Exit 1 = drift.
sources-drift:
    bash src/scripts/sources-registry-check.sh

# --- Airbyte EVALUATION lane (#41) — experimental, OFF the `make` path. See
#     experimental/ingestion/airbyte/README.md. All local + credential-gated; CI never applies. ---
airbyte_jf := home_directory() / ".ai/skills/_scripts/de/ingestion/Justfile"

# Validate every `airbyte:` block against the LIVE OSS registry (connector exists; incremental
# ⇒ cursor; streams non-empty). Self-skips on machines without ~/.ai. Also the pre-commit gate.
airbyte-validate *args:
    bash src/scripts/airbyte-blocks-check.sh {{args}}

# Bring up local Airbyte (abctl = kind/k8s-in-Docker). Disk-gated; port from the config SSoT.
airbyte-up:
    bash experimental/ingestion/airbyte/up.sh

# Tear it down (persisted volumes kept; pass --persisted to drop them).
airbyte-down *args:
    bash experimental/ingestion/airbyte/down.sh {{args}}

# Mint OSS API client-credentials into .env (never printed). Requires the instance up.
airbyte-creds:
    bash experimental/ingestion/airbyte/credentials.sh

# --- VPS: manual deploy (ADR-0012). Settings: config/config.yml -> deploy.vps.* ---
# Each mutating recipe has a -dry sibling; both delegate to _vps-script (single body).
_vps-script script *args:
    bash deploy/vps/{{script}} {{args}}

# Create (or reuse) the Hetzner box, then print the OGIP_VPS_HOST export for vps-provision.
# Idempotent by deploy.hetzner.server_name — re-running reuses the box, never bills a second.
vps-hetzner *args:
    @just -f {{justfile()}} _vps-script hetzner.sh {{args}}

vps-hetzner-dry *args:
    @just -f {{justfile()}} _vps-script hetzner.sh --dry-run {{args}}

# Bootstrap a bare host over ssh (runs from here, as root on the host). Idempotent.
vps-provision *args:
    @just -f {{justfile()}} _vps-script provision.sh {{args}}

vps-provision-dry *args:
    @just -f {{justfile()}} _vps-script provision.sh --dry-run {{args}}

# Deploy a ref ON the host (ssh + run deploy.sh there). `just vps-deploy <sha>` to pin/roll back.
vps-deploy *args:
    @bash deploy/vps/remote.sh deploy.sh {{args}}

# On-HOST preview: ssh in, then deploy.sh --dry-run there. Needs a reachable host (it previews
# what the deploy would do on that specific box). For a host-free check, use vps-deploy-preview.
vps-deploy-dry *args:
    @bash deploy/vps/remote.sh deploy.sh --dry-run {{args}}

# OFFLINE preview: run deploy.sh --dry-run locally, no ssh (opens no connection). Validates the
# deploy logic + the preflight gate for missing cross-lane artifacts. Still needs a host VALUE
# (OGIP_VPS_HOST or deploy.vps.host) since settings load first — but any placeholder works; it
# is never contacted. Use this while the box is still being provisioned.
vps-deploy-preview *args:
    @bash deploy/vps/deploy.sh --dry-run {{args}}

# Verify a deploy ON the host (read-only).
vps-smoke *args:
    @bash deploy/vps/remote.sh smoke.sh {{args}}

# Show containers + deployed ref on the host (read-only, no -dry sibling needed).
vps-status:
    @bash deploy/vps/status.sh

# --- Observability (Phase 7): stack lives in deploy/obs/; start it with `make obs-up` ---
# Compose healthchecks cover VM/Loki/Grafana; Alloy ships no HTTP client and cannot self-probe,
# so obs-verify is what asserts Alloy — and it checks every published port from the host.

# Assert every obs endpoint answers.
obs-verify:
    bash src/scripts/obs-verify.sh

# Accept-check for the log path: file → Alloy → Loki → query. Needs no pipeline run.
obs-smoke-log:
    bash src/scripts/obs-smoke-log.sh

# Tail the obs stack's own container logs.
obs-logs *args:
    docker compose -f deploy/obs/docker-compose.obs.yml logs -f --tail=100 {{args}}

# --- Agentic usage (epic #33) — standard OSS reporter over ~/.claude/projects JSONL. ---
# Live per-project/agentic dashboards are Grafana (ogip-agentic); this is the offline/history
# view. ccusage has no per-project filter — use --since/--until, or the session view below.

# Token/cost by day across local agent sessions (args pass through, e.g. --since 20260701).
agentic-usage *args:
    npx -y ccusage@latest daily {{args}}

# Token/cost by session (project paths visible — pick out OGIP rows).
agentic-usage-sessions *args:
    npx -y ccusage@latest session {{args}}

# --- Finalization / landing helpers (re-root T9, #40) ---

# Read-only recon before a big landing: branches vs origin/dev, worktree dirt, session locks
# (incl. worktree-local stores), open PRs + CI rollup. Exit 1 = blockers listed.
preflight:
    bash src/scripts/preflight-clean-ground.sh

# Merge a PR as the repo-owner account, then restore the previous gh account (trap-safe).
gh-merge-as pr *flags:
    bash src/scripts/gh-merge-as.sh {{pr}} {{flags}}
