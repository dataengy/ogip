# `src/ogip/` — typed Python core

The importable package (`ogip`). Fully typed, Pyright strict.

| Module | Purpose |
|---|---|
| `config.py` | Typed settings from `config/config.yml` (SSoT) + `.env` overrides/secrets. |
| `logger.py` | Structured loguru logging (human + JSON sinks). |
| `warehouse.py` | DuckDB session/helpers _(M0)_. |
| `spec_compile/` | Spec (Bruin) → engine projects (SQLMesh default) _(Phase 3)_. |
| `metrics.py` · `notify.py` | Metrics push + `Notifier` alerts abstraction _(Phase 7)_. |

Business logic for flows lives here; `pipelines/` (Prefect) and `transform/` (SQLMesh) call in.
