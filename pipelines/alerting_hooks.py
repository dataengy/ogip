"""Prefect state-change hooks — route a failed flow run into the alerting layer.

A flow failure is precisely the event alerting exists for. `notify_flow_failure` is wired as an
`on_failure` hook on the `@flow` decorator, so Prefect calls it with `(flow, flow_run, state)`
the moment a run enters a FAILED state. See `ogip.alerting` and the observability architecture doc.

Two properties, both deliberate:

* **Silent without credentials.** `make_notifier()` returns None in CI and demo mode, so a
  pipeline with no alerting secrets fails exactly as before — no notice, no error.
* **Never raises.** An alert hook that throws would bury the real failure under its own
  traceback. `Notifier.notify` already swallows transport errors; this guards the rest
  (building the notifier, reading the state) so the hook can only ever log, never escalate.
"""

from __future__ import annotations

from typing import Any

from ogip.alerting import make_notifier
from ogip.logger import logger

__all__ = ["notify_flow_failure"]


def notify_flow_failure(flow: Any, flow_run: Any, state: Any) -> None:
    """`on_failure` hook: alert that a flow run failed. Best-effort; never raises.

    Typed loosely on purpose — Prefect calls this positionally with its own `Flow` / `FlowRun`
    / `State`, and the hook only reads `.name` / `.message` off them. Keeping the annotations
    structural avoids pinning the module to Prefect's generic `FlowStateHook` signature.
    """
    try:
        flow_name = getattr(flow, "name", "?")
        run_name = getattr(flow_run, "name", "?")
        reason = getattr(state, "message", None) or getattr(state, "name", "FAILED")
        text = f"🔴 OGIP flow failed: {flow_name}\nrun: {run_name}\nstate: {reason}"

        notifier = make_notifier()
        if notifier is None:
            logger.bind(flow=flow_name).debug("flow failed; alerting off — no notice sent")
            return
        result = notifier.notify(text)
        if not result:
            logger.bind(flow=flow_name).warning(
                "flow-failure alert not delivered: {e}", e=result.error
            )
    except Exception as exc:  # a failure hook must never raise — that would mask the failure
        logger.error("flow-failure alert hook errored (suppressed): {e}", e=exc)
