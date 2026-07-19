"""Prefect setup for **Bruin** — the `prefect-bruin` complete alternative profile.

Separated setup (A12): ingest (dlt) → Bruin runs `spec/sql` natively (pass-through, spec *is*
Bruin) → ML feature matrix → ML-ready Parquet. Shares step logic via `pipelines.flows._common`.
Needs the `bruin` CLI on PATH.
"""

from __future__ import annotations

from pipelines.flows._common import make_engine_flow

flow = make_engine_flow("bruin")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("bruin pipeline complete: {r}", r=flow())
