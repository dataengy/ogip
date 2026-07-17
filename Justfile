# OGIP — spec ops & heavy logic (thin common commands live in the Makefile).
# Runtime env: uv manages .run/venv.

export UV_PROJECT_ENVIRONMENT := ".run/venv"

# List recipes (default)
default:
    @just --list

# --- Run profiles (A12): orchestrator × engine setups ---
# Launch a run profile from config/config.yml → run_profiles (src/scripts/run-profile.py).
run-profile name="prefect-sqlmesh":
    uv run python src/scripts/run-profile.py {{name}}

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

# --- Secrets: render blank slots from an opt-in backend (Bitwarden/git-secret) ---
secrets-render:
    bash config/.env-secrets-render.sh

# --- Repo hygiene: fail if stray files land in the root (root-lean rule) ---
tidy-root:
    bash .ci/steps/structure-validate.sh

# --- VPS: manual deploy (ADR-0012). Settings: config/config.yml -> deploy.vps.* ---
# Each mutating recipe has a -dry sibling; both delegate to _vps-script (single body).
_vps-script script *args:
    bash deploy/vps/{{script}} {{args}}

# Bootstrap a bare host over ssh (runs from here, as root on the host). Idempotent.
vps-provision *args:
    @just -f {{justfile()}} _vps-script provision.sh {{args}}

vps-provision-dry *args:
    @just -f {{justfile()}} _vps-script provision.sh --dry-run {{args}}

# Deploy a ref ON the host (ssh + run deploy.sh there). `just vps-deploy <sha>` to pin/roll back.
vps-deploy *args:
    @bash deploy/vps/remote.sh deploy.sh {{args}}

vps-deploy-dry *args:
    @bash deploy/vps/remote.sh deploy.sh --dry-run {{args}}

# Verify a deploy ON the host (read-only).
vps-smoke *args:
    @bash deploy/vps/remote.sh smoke.sh {{args}}

# Show containers + deployed ref on the host (read-only, no -dry sibling needed).
vps-status:
    @bash deploy/vps/status.sh
