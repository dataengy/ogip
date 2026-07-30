"""Runtime bridge for GENERATED ODOS definitions — subprocess to the ogip task registry.

The Dagster venv does not depend on `ogip`; every task, sensor callable, and check crosses
the boundary via `python -m ogip.tasks` in the root venv — the same boundary dg-tasks.sh
uses. A task's return value arrives as the LAST stdout line, JSON-encoded (the CLI prints
it only for non-None returns); logs sink to stderr, so stdout stays parseable.

NOTE: no `from __future__ import annotations` here — see _lib/orchestration.py.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import dagster as dg

PROJECT = Path(__file__).resolve().parents[3]
REPO = PROJECT.parents[2]


def _run(name: str, *args: str) -> "subprocess.CompletedProcess[str]":
    env = {**os.environ, "UV_PROJECT_ENVIRONMENT": ".run/venv"}
    return subprocess.run(
        ["uv", "run", "python", "-m", "ogip.tasks", name, *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO,
        env=env,
    )


def _result_line(stdout: str) -> object:
    lines = [line for line in stdout.splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else None


def call_task(log: Any, name: str, *args: str) -> None:
    """Run a registry task, streaming its output; raise dg.Failure on a non-zero exit."""
    log.info("ogip.tasks %s %s", name, " ".join(args))
    proc = _run(name, *args)
    if proc.stdout:
        log.info(proc.stdout[-6000:])
    if proc.stderr:
        log.info(proc.stderr[-6000:])
    if proc.returncode != 0:
        raise dg.Failure(description=f"task {name} failed (rc={proc.returncode})")


def task_result(log: Any, name: str, *args: str) -> object:
    """call_task, but parse and return the JSON result line (None when the task returned None)."""
    proc = _run(name, *args)
    if proc.stderr:
        log.info(proc.stderr[-6000:])
    if proc.returncode != 0:
        raise dg.Failure(description=f"task {name} failed (rc={proc.returncode})")
    return _result_line(proc.stdout)


def poll_tick(
    context: dg.SensorEvaluationContext, callable_name: str
) -> "dg.SensorResult | dg.SkipReason":
    """The ODOS poll contract (§7.2): registry callable → cursor token; compare, run, advance."""
    proc = _run(callable_name)
    if proc.returncode != 0:
        return dg.SkipReason(f"{callable_name} failed (rc={proc.returncode}): {proc.stderr[-300:]}")
    token_value = _result_line(proc.stdout)
    if token_value is None:
        return dg.SkipReason(f"{callable_name}: nothing to watch")
    token = str(token_value)
    if context.cursor == token:
        return dg.SkipReason(f"{callable_name}: unchanged ({token})")
    return dg.SensorResult(run_requests=[dg.RunRequest(run_key=token)], cursor=token)


def check_result(name: str) -> dg.AssetCheckResult:
    """The ODOS check contract (§4.6): a dict with 'passed' → AssetCheckResult."""
    proc = _run(name)
    if proc.returncode != 0:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"error": f"rc={proc.returncode}", "stderr": proc.stderr[-500:]},
        )
    data = _result_line(proc.stdout)
    if not isinstance(data, dict) or "passed" not in data:
        return dg.AssetCheckResult(
            passed=False, metadata={"error": "check returned no 'passed' key"}
        )
    passed = bool(data.pop("passed"))
    return dg.AssetCheckResult(passed=passed, metadata={k: str(v) for k, v in data.items()})
