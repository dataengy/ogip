"""Monitoring — run-failure alerting hook for the whole code location."""

import dagster as dg
from dagster import RunFailureSensorContext


@dg.run_failure_sensor(
    name="dwh_run_failure_alert",
    description="Fire on any failed run — the hook point for the alerting lane's Notifier "
    "(Telegram/Mattermost/Slack). Logs the run id + failure message.",
)
def dwh_failure_sensor(context: RunFailureSensorContext) -> None:
    context.log.error(
        "run %s failed: %s", context.dagster_run.run_id, context.failure_event.message
    )


defs = dg.Definitions(sensors=[dwh_failure_sensor])
