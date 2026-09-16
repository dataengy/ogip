#!/usr/bin/env python
"""Data-quality runner — loads AND EXECUTES the monitors declared in ``spec/dq/policy.yml``
(ADR-0008 severity model: ``error`` blocks with a non-zero exit, ``warn`` reports).

Monitors (row-count floors, freshness) are declared as data in ``spec/dq/policy.yml`` — they
are NOT ODTS checks (``spec/sql`` ``columns[].checks``) and NOT ODOS hooks. Full mode queries
the DuckDB warehouse and evaluates thresholds; with no warehouse present it SKIPs loudly and
exits 0 (a fresh checkout's ``make check`` must not require a pipeline run). ``--fast`` is the
pre-push subset: policy validity only. Recording results to ``platform_meta.dq_results`` stays
deferred (docs/techdebt/finalization-tbd.md row 9).
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


def _resolve_table(con: Any, model: str) -> str | None:
    """`schema.name` → a queryable relation, tolerant of per-engine schema placement.

    The raw layer is deliberately unqualified in the dbt render (it lands in `main`), while
    plain-SQL/SQLMesh materialize it as `raw.*` — so monitors resolve by table NAME first
    within the declared schema, then anywhere. Returns a quoted `schema.table` or None.
    """
    schema, _, name = model.rpartition(".")
    rows = con.execute(
        "select table_schema from information_schema.tables where table_name = ?", [name]
    ).fetchall()
    schemas = [r[0] for r in rows]
    if not schemas:
        return None
    chosen = schema if schema in schemas else schemas[0]
    return f'"{chosen}"."{name}"'


def _run_monitor(con: Any, monitor: Monitor) -> tuple[bool, str]:
    """Evaluate one monitor; (passed, human detail). Unknown types fail loudly (never skip)."""
    target = _resolve_table(con, monitor["model"])
    if target is None:
        return False, f"table {monitor['model']} not found in warehouse"
    raw = cast("dict[str, Any]", monitor)
    if monitor["type"] == "row_count":
        min_rows = int(raw.get("min_rows", 1))
        n = int(con.execute(f"select count(*) from {target}").fetchone()[0])
        return n >= min_rows, f"rows={n} (min {min_rows})"
    if monitor["type"] == "freshness":
        column, max_age = str(raw.get("column")), float(raw.get("max_age_hours", 24))
        age = con.execute(
            f"select date_diff('minute', max(\"{column}\"), now()) from {target}"
        ).fetchone()[0]
        if age is None:
            return False, f"{column} has no values (empty table?)"
        hours = float(age) / 60.0
        return hours <= max_age, f"age={hours:.1f}h (max {max_age}h)"
    return False, f"unknown monitor type {monitor['type']!r}"


def execute(monitors: list[Monitor], warehouse: Path) -> int:
    """Run every monitor against the DuckDB warehouse. Exit 1 iff any `error` monitor fails.

    `warn` failures are reported and do not block (ADR-0008). Recording results to
    `platform_meta.dq_results` stays deferred (docs/techdebt/finalization-tbd.md row 9).
    """
    import duckdb

    failed_errors = 0
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        for monitor in monitors:
            passed, detail = _run_monitor(con, monitor)
            mark = "PASS" if passed else "FAIL"
            print(f"[dq] {mark} {monitor['severity']:<5} {monitor['name']}: {detail}")
            if not passed and monitor["severity"] == "error":
                failed_errors += 1
    finally:
        con.close()
    if failed_errors:
        print(f"[dq] {failed_errors} error-severity monitor(s) FAILED — blocking (ADR-0008)")
        return 1
    print("[dq] all error-severity monitors passed")
    return 0


def main(argv: list[str]) -> int:
    fast = "--fast" in argv
    scope = "fast (pre-push subset)" if fast else "full"
    monitors = load_policy()
    if not monitors:
        print(f"[dq] {scope}: no policy declared at spec/dq/policy.yml — OK")
        return 0
    print(f"[dq] {scope}: {_summarize(monitors)}")
    if fast:
        # Pre-push subset: policy validity only — executing needs a built warehouse.
        return 0
    from ogip.config import get_settings

    warehouse = get_settings().platform.warehouse_path
    if not warehouse.is_file():
        print(
            f"[dq] SKIPPED: no warehouse at {warehouse} — run a pipeline first "
            "(make run-dbt / run-bruin); monitors were NOT evaluated."
        )
        return 0
    return execute(monitors, warehouse)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
