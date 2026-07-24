#!/usr/bin/env python
"""Data-quality runner — loads + reports the monitors declared in ``spec/dq/policy.yml``
(ADR-0008 severity model: ``error`` blocks, ``warn`` records).

Monitors (row-count floors, freshness) are declared as data in ``spec/dq/policy.yml`` — they
are NOT ODTS checks (``spec/sql`` ``columns[].checks``) and NOT ODOS hooks. This runner loads
that policy and prints a summary; it does NOT execute the monitors against the warehouse yet —
the executor (query DuckDB, evaluate thresholds, record to ``platform_meta.dq_results``) arrives
in Phase 4. ``--fast`` is the pre-push subset. Exits 0 cleanly either way so the hook/gate stays
wired now.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

_POLICY_PATH = Path(__file__).resolve().parent.parent / "spec" / "dq" / "policy.yml"


class Monitor(TypedDict):
    """One declared row-count/freshness monitor (see ``spec/dq/policy.yml``)."""

    name: str
    model: str
    type: str
    severity: str


def load_policy(policy_path: Path | None = None) -> list[Monitor]:
    """Parse ``spec/dq/policy.yml``'s ``monitors`` list. Missing/empty file -> ``[]``.

    ``policy_path`` defaults to the module-level ``_POLICY_PATH`` — read at call time (not
    bound as a default argument) so tests can monkeypatch ``dq.run._POLICY_PATH``.
    """
    if policy_path is None:
        policy_path = _POLICY_PATH
    if not policy_path.is_file():
        return []
    loaded = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return []
    monitors = cast("dict[str, Any]", loaded).get("monitors")
    if not isinstance(monitors, list):
        return []
    return [cast("Monitor", monitor) for monitor in cast("list[Any]", monitors)]


def _summarize(monitors: list[Monitor]) -> str:
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for monitor in monitors:
        by_type[monitor["type"]] = by_type.get(monitor["type"], 0) + 1
        by_severity[monitor["severity"]] = by_severity.get(monitor["severity"], 0) + 1
    types = ", ".join(f"{k}={v}" for k, v in sorted(by_type.items()))
    severities = ", ".join(f"{k}={v}" for k, v in sorted(by_severity.items()))
    return f"{len(monitors)} monitor(s) declared ({types}; severity: {severities})"


def main(argv: list[str]) -> int:
    fast = "--fast" in argv
    scope = "fast (pre-push subset)" if fast else "full"
    monitors = load_policy()
    if not monitors:
        print(f"[dq] {scope}: no policy declared at spec/dq/policy.yml — OK")
        return 0
    # TODO(phase-4): execute these monitors against the warehouse and record results.
    print(f"[dq] {scope}: {_summarize(monitors)} — load+report only, execution arrives in Phase 4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
