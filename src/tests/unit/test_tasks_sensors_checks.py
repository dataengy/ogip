"""The poll/check/alerting callables ODOS automations reference (design §4.5, §4.6, §4.6a)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ogip.tasks import get_task
from ogip.tasks.checks import market_features_nonempty
from ogip.tasks.sensors import landing_rowcount, spec_sql_mtime


def test_all_four_names_are_registered() -> None:
    for name in (
        "sensors.landing_rowcount",
        "sensors.spec_sql_mtime",
        "checks.market_features_nonempty",
        "alerting.notify_run_failure",
    ):
        assert callable(get_task(name))


def test_landing_rowcount_without_dsn_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OGIP_PG_DSN", raising=False)
    assert landing_rowcount() is None


def test_landing_rowcount_with_unreachable_dsn_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dead DB is 'nothing to watch', never an exception — sensors must not crash the tick."""
    monkeypatch.setenv("OGIP_PG_DSN", "postgresql://nobody@127.0.0.1:1/void?connect_timeout=1")
    assert landing_rowcount() is None


def test_spec_sql_mtime_token_tracks_newest_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import ogip.tasks.sensors as sensors

    (tmp_path / "raw").mkdir()
    model = tmp_path / "raw" / "a.sql"
    model.write_text("select 1")
    monkeypatch.setattr(sensors, "_SPEC_SQL", tmp_path)
    first = spec_sql_mtime()
    assert first is not None
    import os

    os.utime(model, (model.stat().st_atime, model.stat().st_mtime + 10))
    second = spec_sql_mtime()
    assert second is not None and second != first


def test_spec_sql_mtime_empty_dir_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import ogip.tasks.sensors as sensors

    monkeypatch.setattr(sensors, "_SPEC_SQL", tmp_path)
    assert spec_sql_mtime() is None


def test_check_reports_missing_warehouse_as_failed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The ODOS check contract: a dict with a required boolean 'passed' key."""
    import ogip.tasks.checks

    stub_settings = MagicMock()
    stub_settings.platform.warehouse_path = tmp_path / "absent.duckdb"
    monkeypatch.setattr(ogip.tasks.checks, "get_settings", lambda: stub_settings)
    result = market_features_nonempty()
    assert result["passed"] is False
    assert "reason" in result


def test_check_never_raises_on_missing_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Regression: check must never raise when warehouse exists but table doesn't."""
    import duckdb

    import ogip.tasks.checks

    # Create a real empty warehouse file
    warehouse_path = tmp_path / "ogip.duckdb"
    duckdb.connect(str(warehouse_path)).close()

    stub_settings = MagicMock()
    stub_settings.platform.warehouse_path = warehouse_path
    monkeypatch.setattr(ogip.tasks.checks, "get_settings", lambda: stub_settings)

    # This must NOT raise — it should return in-band failure
    result = market_features_nonempty()
    assert result["passed"] is False
    assert "reason" in result
