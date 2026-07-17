"""CDC landing → lake, as a Dagster asset (ingestr, D11).

A plain `@asset` (not a Component): ingestr has no Dagster component, and this is a subprocess
boundary, so we shell out to `cdc/ingestr_cdc.sh`. Grouped with `ingestion` so it lives in the
same asset graph as the dlt batch load and the dbt models.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import dagster as dg

_CDC_SCRIPT = Path(__file__).resolve().parents[4] / "cdc" / "ingestr_cdc.sh"


@dg.asset(group_name="ingestion", kinds={"ingestr", "postgres"})
def cdc_landing() -> dg.MaterializeResult:
    """Merge Postgres `landing.*` CDC changes into the lake via ingestr."""
    proc = subprocess.run(
        ["bash", str(_CDC_SCRIPT)], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise dg.Failure(description=f"ingestr CDC failed: {proc.stderr.strip()}")
    return dg.MaterializeResult(metadata={"source": "postgres:landing.*", "loader": "ingestr"})


defs = dg.Definitions(assets=[cdc_landing])
