"""CDC task — ingestr from the Postgres landing zone (D11)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["cdc_catchup"]

_REPO = Path(__file__).resolve().parents[3]
_CDC_SCRIPT = _REPO / "experimental" / "orchestration" / "dagster_ogip" / "cdc" / "ingestr_cdc.sh"


@odos_task("cdc.catchup")
def cdc_catchup(*, dry_run: bool = False) -> None:
    """Capture INSERT/UPDATE/DELETE on the Postgres `landing` schema and merge into the lake."""
    if not _CDC_SCRIPT.is_file():
        raise FileNotFoundError(f"CDC script not found at {_CDC_SCRIPT}")
    argv = ["bash", str(_CDC_SCRIPT)] + (["--dry-run"] if dry_run else [])
    log.bind(task="cdc.catchup").info("exec: {c}", c=" ".join(argv))
    subprocess.run(argv, check=True, cwd=_REPO)
