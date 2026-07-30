"""Cross-orchestrator integration tasks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["trigger_prefect"]

_REPO = Path(__file__).resolve().parents[3]


@odos_task("integrations.trigger_prefect")
def trigger_prefect() -> None:
    """Trigger the root Prefect flow — the two orchestrators over one spec and one warehouse."""
    log.bind(task="integrations.trigger_prefect").info("running pipelines.flows.main")
    subprocess.run([sys.executable, "-m", "pipelines.flows.main"], check=True, cwd=_REPO)
