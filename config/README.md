# `config/` — configuration (SSoT)

Every non-secret default is declared **once** here. Nothing config-shaped lives in the repo root.

| File | Purpose |
|---|---|
| `config.yml` | **Single source of truth** — paths, ports, storage, Postgres, profiles, sources. Python reads it directly; `.env` is derived from it. |
| `.env-render.py` | Renders the flat root `.env` from `config.yml` (derived values + blank secret slots; merge-safe on secrets). `make render-env`. |
| `.pre-commit-config.yaml` | Hooks run by **prek** (fast): ruff · sqlfluff (SQL) · shellcheck/shfmt (Bash) · yamllint · gitleaks · ty · smoke tests (+ data tests on push). |
| `.yamllint.yaml` | Relaxed YAML lint config. |
| `sqlfluff/` | Per-dialect SQL lint presets (DuckDB house style also in `pyproject.toml`). |
| `.env-secrets-render.sh` | _(opt-in)_ fill secret slots from Bitwarden / git-secret (ADR-0011). Default is manual `.env` / GitHub Actions secrets. |

**Never** put secret values here — tracked templates carry blank slots / env-var names only.
