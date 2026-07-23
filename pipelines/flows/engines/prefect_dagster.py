"""Back-compat shim — the dagster seam moved to pipelines/dagster/flow.py (Part 3.2)."""

from __future__ import annotations

from pipelines.dagster.flow import DAGSTER_PROJECT, flow, run_dagster_dlt_dbt

__all__ = ["DAGSTER_PROJECT", "flow", "run_dagster_dlt_dbt"]
