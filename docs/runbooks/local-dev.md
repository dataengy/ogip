# Runbook — Local development bootstrap

- **Trigger:** first-time setup, or refreshing a local checkout.
- **Owner:** any contributor.

## Preconditions

- [uv](https://docs.astral.sh/uv/), Docker Compose. Optional: [just](https://just.systems/).
- Secrets: fill the gitignored `.env` slots by hand (or `just secrets-render` for an opt-in backend).

## Steps

1. `make bootstrap` — uv → `.run/venv`, pre-commit hooks, render `.env` from `config/config.yml`.
2. `make check` — ruff + pyright strict + pytest (CI parity).
3. `make up` — start core services in Docker (Postgres; Prefect; MinIO if the storage profile needs it).
4. `make run` — run the pipeline on bundled sample data (no API keys required).

## Verify

- `make check` is green; `make up` reports healthy containers; `make run` writes `.run/outputs/*.parquet`.

## Rollback

- `make down` stops services; delete `.run/` to reset all runtime state (safe — gitignored).

## Escalation

- Environment/Docker issues that aren't code: infra/DevOps is handled separately.
