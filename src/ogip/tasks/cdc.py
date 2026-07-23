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
def cdc_catchup(*, dry_run: bool = False, stream: bool = False) -> None:
    """Capture INSERT/UPDATE/DELETE on the Postgres `landing` schema and merge into the lake.

    ``dry_run`` prints the ingestr command without executing it; ``stream`` runs continuous
    CDC instead of a one-shot catch-up (forwarded to `cdc/ingestr_cdc.sh` as `--stream`).
    The two are contradictory — passing both raises ``ValueError`` rather than silently
    preferring one.
    """
    if dry_run and stream:
        raise ValueError(
            f"cdc.catchup: dry_run={dry_run!r} and stream={stream!r} are mutually exclusive"
        )
    if not _CDC_SCRIPT.is_file():
        raise FileNotFoundError(f"CDC script not found at {_CDC_SCRIPT}")
    flag = ["--dry-run"] if dry_run else ["--stream"] if stream else []
    argv = ["bash", str(_CDC_SCRIPT), *flag]
    log.bind(task="cdc.catchup").info("exec: {c}", c=" ".join(argv))
    subprocess.run(argv, check=True, cwd=_REPO)
