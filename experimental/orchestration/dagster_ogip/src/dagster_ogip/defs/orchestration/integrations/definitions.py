"""Cross-orchestrator integrations — hand off to the platform's other engines."""

import dagster as dg
from dagster import OpExecutionContext
from dagster_ogip._lib.orchestration import run_task


@dg.op
def _trigger_prefect(context: OpExecutionContext) -> None:
    run_task(context, "prefect")


@dg.job(
    tags={"orchestration": "prefect"},
    description="Trigger the root Prefect flow (the default production orchestrator) from Dagster "
    "— demonstrates the two orchestrators interoperating over the same spec/warehouse.",
)
def prefect_trigger_job() -> None:
    _trigger_prefect()


defs = dg.Definitions(jobs=[prefect_trigger_job])
