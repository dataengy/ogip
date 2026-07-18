# Task — obs wiring handoff (lane obs → core-pipeline)

**Status:** ✅ done — the shipped obs stack's pipeline-facing half, which lived in the
core-pipeline lane (`config/`, `pipelines/`), is now wired.

## What the obs lane needed from us (STATUS handoff)

1. **The flow wrote no log file** → Alloy tailed an empty dir, Loki panels stayed blank.
2. **Obs ports never reached `.env`** → the obs compose fell back to literals duplicating the SSoT.

## Delivered

- `pipelines/flows/main.py` — the daily flow now calls
  `setup_logging(json_logs=settings.platform.log_json, log_file=settings.platform.log_file)`
  instead of a bare `setup_logging()`, so it writes a structured log file (`.run/logs/ogip.log`)
  that Alloy → Loki tails.
- `config/config.yml` — `platform.log_json: true`, so the file is JSON and Loki gets parsed labels.
- `config/.env-render.py` — `_derived()` now maps `VICTORIAMETRICS_PORT`, `LOKI_PORT`,
  `GRAFANA_PORT` from the `services` SSoT into `.env` (the obs compose reads these).

## Verified

- `make check` green (46 tests). e2e green + stable — the flow writes `.run/logs/ogip.log`
  (20 JSON lines confirmed). `make render-env` emits the three obs ports + `OGIP_LOG_JSON=true`.

## Not in scope (still obs lane / later)

- OTLP metrics export (`localhost:4318`, prefix `ogip_`) — the dashboard panel is waiting; a
  pipeline-instrumentation follow-up.
- The alerting failure hook is already wired (`on_failure=[notify_flow_failure]` — the alerting
  lane landed it).
