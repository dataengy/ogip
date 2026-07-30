"""Unit tests for `spec/dq/policy.yml` + `dq/run.py`'s load+report of it.

Monitors (row-count floors, freshness) are NOT ODTS checks and NOT ODOS hooks — their one
home is `spec/dq/policy.yml` (see .ai/PLAN.md A8, dq/README.md). `dq/run.py` loads and reports
them; it does not execute them (the executor is Phase 4 — out of scope here, see task brief).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from dq.run import load_policy, main

from ogip.spec_compile import load_assets

_REPO = Path(__file__).resolve().parents[3]
_POLICY_PATH = _REPO / "spec" / "dq" / "policy.yml"
_SPEC_SQL = _REPO / "spec" / "sql"

_VALID_TYPES = {"row_count", "freshness"}
_VALID_SEVERITIES = {"error", "warn"}
_REQUIRED_FIELDS = {"name", "model", "type", "severity"}


def _raw_policy() -> dict[str, Any]:
    loaded = yaml.safe_load(_POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return cast("dict[str, Any]", loaded)


def _raw_monitors() -> list[dict[str, Any]]:
    return list(_raw_policy()["monitors"])


def _known_models() -> set[str]:
    return {asset.name for asset in load_assets(_SPEC_SQL)}


# ── spec/dq/policy.yml shape ────────────────────────────────────────────────


def test_policy_file_parses_as_yaml_mapping() -> None:
    loaded = _raw_policy()
    assert loaded.get("version") == 1
    assert isinstance(loaded.get("monitors"), list)
    assert loaded["monitors"], "policy.yml declares no monitors"


def test_every_monitor_has_required_fields() -> None:
    for monitor in _raw_monitors():
        missing = _REQUIRED_FIELDS - monitor.keys()
        assert not missing, f"monitor {monitor.get('name')!r} missing fields {missing}"


def test_every_monitor_type_is_row_count_or_freshness() -> None:
    for monitor in _raw_monitors():
        assert monitor["type"] in _VALID_TYPES, (
            f"monitor {monitor['name']!r} has unsupported type {monitor['type']!r}"
        )


def test_every_monitor_severity_is_error_or_warn() -> None:
    for monitor in _raw_monitors():
        assert monitor["severity"] in _VALID_SEVERITIES, (
            f"monitor {monitor['name']!r} has unsupported severity {monitor['severity']!r}"
        )


def test_every_monitor_model_is_a_real_spec_sql_asset() -> None:
    known = _known_models()
    unknown = {m["model"] for m in _raw_monitors()} - known
    assert not unknown, (
        f"policy.yml references unknown models {sorted(unknown)}; known: {sorted(known)}"
    )


def test_monitor_names_are_unique() -> None:
    names = [m["name"] for m in _raw_monitors()]
    assert len(names) == len(set(names)), "duplicate monitor names in policy.yml"


# ── dq/run.py: load ──────────────────────────────────────────────────────────


def test_load_policy_returns_every_declared_monitor() -> None:
    monitors = load_policy()
    assert len(monitors) == len(_raw_monitors())


def test_load_policy_missing_file_returns_empty_list(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yml"
    assert load_policy(missing) == []


# ── dq/run.py: report (load + report only — no execution) ──────────────────


def test_main_reports_the_declared_monitor_count(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert str(len(_raw_monitors())) in out


def test_main_fast_flag_still_reports_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--fast"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "fast" in out


def test_main_missing_policy_file_reports_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import dq.run as dq_run

    monkeypatch.setattr(dq_run, "_POLICY_PATH", tmp_path / "missing.yml")
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "no" in out.lower()
