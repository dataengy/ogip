"""Shared step library for the separated per-engine Prefect setups (Part 3.1, #37).

Foundation for the six separated Prefect sub-projects: each setup imports its steps from here
instead of the historical `pipelines.flows._common` / `pipelines.flows._paths` /
`pipelines.alerting_hooks` modules, which now live on as thin back-compat shims re-exporting
these same objects.
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
