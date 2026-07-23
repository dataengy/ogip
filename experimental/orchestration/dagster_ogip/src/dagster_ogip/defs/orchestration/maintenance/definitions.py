"""Maintenance jobs — keeping the generated dbt subproject and its packages healthy.

`spec/` (Bruin) is the SSoT, so the dbt project is regenerated; these jobs re-generate it, run
only the models a spec change touched, and audit the project with dbt_project_evaluator.
"""

from dagster_ogip._lib.orchestration import SPEC_SQL, run_task

import dagster as dg
from dagster import OpExecutionContext, SensorEvaluationContext


@dg.op
def _update_dbt(context: OpExecutionContext) -> None:
    run_task(context, "update-dbt")


@dg.op
def _update_dbt_changed(context: OpExecutionContext) -> None:
    run_task(context, "update-dbt-changed")


@dg.op
def _dbt_evaluate(context: OpExecutionContext) -> None:
    run_task(context, "dbt-evaluate")


@dg.job(
    tags={"maintenance": "dbt"},
    description="Regenerate the dbt project from `spec/`, install packages (`dbt deps`), and "
    "`dbt parse` — refreshes the manifest without running models.",
)
def update_dbt_job() -> None:
    _update_dbt()


@dg.job(
    tags={"maintenance": "dbt"},
    description="Regenerate from `spec/` and build only the models a change touched "
    "(`dbt build --select state:modified+`), falling back to a full build on the first run.",
)
def update_dbt_changed_job() -> None:
    _update_dbt_changed()


@dg.job(
    tags={"maintenance": "dbt", "package": "dbt_project_evaluator"},
    description="Audit the generated dbt project with dbt_project_evaluator — flags modeling, "
    "testing, documentation and DAG anti-patterns (warns, does not block).",
)
def dbt_project_evaluator_job() -> None:
    _dbt_evaluate()


schedules = [
    dg.ScheduleDefinition(
        name="daily_dbt_subproject_update",
        job=update_dbt_job,
        cron_schedule="0 2 * * *",
        description="Daily (02:00) regenerate-from-spec + `dbt deps` + parse.",
    ),
    dg.ScheduleDefinition(
        name="weekly_dbt_project_evaluator",
        job=dbt_project_evaluator_job,
        cron_schedule="0 4 * * 1",
        description="Weekly (Mon 04:00) dbt project audit.",
    ),
]


@dg.sensor(
    job=update_dbt_changed_job,
    minimum_interval_seconds=30,
    name="spec_change_updates_dbt",
    description="Watch `spec/sql` mtimes; on a change, regenerate the dbt subproject and rebuild "
    "only the changed models (the code location also hot-reloads under `dg dev`).",
)
def spec_change_sensor(context: SensorEvaluationContext) -> dg.SensorResult | dg.SkipReason:
    latest = max((p.stat().st_mtime for p in SPEC_SQL.rglob("*.sql")), default=0.0)
    token = f"{latest:.0f}"
    if context.cursor == token:
        return dg.SkipReason("spec/sql unchanged")
    return dg.SensorResult(run_requests=[dg.RunRequest(run_key=token)], cursor=token)


defs = dg.Definitions(
    jobs=[update_dbt_job, update_dbt_changed_job, dbt_project_evaluator_job],
    schedules=schedules,
    sensors=[spec_change_sensor],
)
