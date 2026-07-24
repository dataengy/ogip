"""Shared helpers for the orchestration `defs/` subdirs — paths, asset keys, the task-runner,
and partitions. Lives OUTSIDE `defs/` on purpose, so `dg` does not autoload it as definitions;
the domain modules under `defs/orchestration/<group>/` import from here.

NOTE: no `from __future__ import annotations` anywhere in the orchestration code — it stringizes
the op-`context` annotation and Dagster's typed-context check then rejects it.
"""

import subprocess
from pathlib import Path

import dagster as dg
from dagster import OpExecutionContext

# .../dagster_ogip/src/dagster_ogip/_lib/orchestration.py → dagster_ogip (project) → worktree root
PROJECT = Path(__file__).resolve().parents[3]
REPO = PROJECT.parents[2]
TASKS = PROJECT / "jobs" / "dg-tasks.sh"
WAREHOUSE = REPO / ".run" / "data" / "warehouse" / "ogip.duckdb"
SPEC_SQL = REPO / "spec" / "sql"
SNAPSHOTS_DIR = REPO / ".run" / "data" / "snapshots"

# Asset keys supplied by the components (dlt / dbt / ingestr). dbt models are schema-prefixed
# (raw stays unqualified — the dlt asset is the real raw producer).
K_RAW_DLT = dg.AssetKey(["raw", "rawg__games"])  # the dlt-produced raw Parquet
K_RAW_DBT = dg.AssetKey("rawg__games")  # the dbt raw registration view
K_STAGING = dg.AssetKey(["staging", "stg_games"])
K_CORE = dg.AssetKey(["core", "game"])
K_FS = dg.AssetKey(["fs", "market_features"])
K_CDC = dg.AssetKey("cdc_landing")

# Shared daily partitions for the backfillable snapshot fact.
snapshot_partitions = dg.DailyPartitionsDefinition(start_date="2026-07-01")


def run_task(context: OpExecutionContext, *args: str) -> None:
    """Run a `jobs/dg-tasks.sh` task, streaming its output into the Dagster run."""
    context.log.info("dg-tasks.sh %s", " ".join(args))
    proc = subprocess.run(["bash", str(TASKS), *args], capture_output=True, text=True, check=False)
    if proc.stdout:
        context.log.info(proc.stdout[-6000:])
    if proc.returncode != 0:
        context.log.error(proc.stderr[-6000:])
        raise dg.Failure(description=f"dg-tasks.sh {' '.join(args)} failed (rc={proc.returncode})")
