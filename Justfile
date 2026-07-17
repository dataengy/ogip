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

# --- Task sync: .ai/tasks/ ↔ GitHub Issues/Projects (A14) ---
tasks-sync *args:
    uv run python integrations/github/tasks_sync.py {{args}}

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
