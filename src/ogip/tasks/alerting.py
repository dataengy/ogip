"""Alerting task — ODOS `on_failure:` / `hooks:` body (design §4.6a, §4.7).

A thin wrapper over the obs lane's Notifier: this module OWNS no transport logic
(src/ogip/alerting/ is the obs lane's); it only gives the alert a registry name.
"""

from __future__ import annotations

from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["notify_run_failure"]


@odos_task("alerting.notify_run_failure")
def notify_run_failure(*, run_id: str, message: str = "") -> None:
    """Deliver a run-failure alert; degrade to a log line when alerting is unconfigured."""
    from ogip.alerting import make_notifier

    text = f"OGIP orchestration run failed\nrun: {run_id}"
    if message:
        text += f"\n{message}"
    notifier = make_notifier()
    if notifier is None:
        log.error("run {r} failed (alerting off): {m}", r=run_id, m=message)
        return
    notifier.notify(text)
