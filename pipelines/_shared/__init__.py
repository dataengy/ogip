"""Shared step library for the separated per-engine Prefect setups (Part 3.1-3.3, #37).

Foundation for the seven separated Prefect sub-projects (`pipelines/<engine>/`, one per SQL
profile plus `dagster`): each setup imports its steps from here. The historical
`pipelines.flows._common` / `pipelines.flows._paths` / `pipelines.alerting_hooks` back-compat
shims and the `pipelines.flows.engines` package they backed were retired in Part 3.3 — this is
the only copy of the step library now.
"""

from __future__ import annotations

from pipelines._shared.alerting import notify_flow_failure
from pipelines._shared.paths import REPO, SPEC_SQL, SQLMESH_DIR
from pipelines._shared.steps import (
    build_ml_outputs,
    build_warehouse,
    ingest_raw,
    make_engine_flow,
    publish_outputs,
)

__all__ = [
    "REPO",
    "SPEC_SQL",
    "SQLMESH_DIR",
    "build_ml_outputs",
    "build_warehouse",
    "ingest_raw",
    "make_engine_flow",
    "notify_flow_failure",
    "publish_outputs",
]
