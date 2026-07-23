"""Snapshot task — input validation and the missing-warehouse precondition.

These pin the two failure modes `snapshot_write` must surface loudly instead of
silently succeeding: a malformed `partition` (Finding 1 — it used to be interpolated
raw into SQL and a filesystem path with no validation at all) and a missing warehouse
(Finding 2 — it used to log a warning, create an empty `date=.../` directory, and
return `0`, which downstream listing code could misread as "partition written, zero
rows" instead of "never ran"). Real DuckDB access belongs to the integration/e2e
tiers; `get_settings` is monkeypatched here so these tests never touch a real
warehouse.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ogip.tasks.snapshots import snapshot_write


def _fake_settings(tmp_path: Path) -> SimpleNamespace:
    platform = SimpleNamespace(
        warehouse_path=tmp_path / "warehouse" / "ogip.duckdb",
        data_dir=tmp_path / "data",
    )
    return SimpleNamespace(platform=platform)


def test_invalid_partition_raises_value_error_naming_the_bad_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ogip.tasks.snapshots.get_settings", lambda: _fake_settings(tmp_path))
    with pytest.raises(ValueError, match="partition") as excinfo:
        snapshot_write(partition="not-a-date")
    assert "not-a-date" in str(excinfo.value)


def test_invalid_partition_is_rejected_before_any_filesystem_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ogip.tasks.snapshots.get_settings", lambda: _fake_settings(tmp_path))
    with pytest.raises(ValueError):
        snapshot_write(partition="2024-13-99")
    # No directory tree — not the data dir, not the warehouse dir — was ever touched.
    assert list(tmp_path.iterdir()) == []


def test_missing_warehouse_raises_file_not_found_naming_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _fake_settings(tmp_path)
    monkeypatch.setattr("ogip.tasks.snapshots.get_settings", lambda: settings)
    with pytest.raises(FileNotFoundError) as excinfo:
        snapshot_write(partition="2024-01-15")
    assert str(settings.platform.warehouse_path) in str(excinfo.value)


def test_missing_warehouse_leaves_no_output_directory_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _fake_settings(tmp_path)
    monkeypatch.setattr("ogip.tasks.snapshots.get_settings", lambda: settings)
    with pytest.raises(FileNotFoundError):
        snapshot_write(partition="2024-01-15")
    # Old behaviour created `<data_dir>/snapshots/date=.../` before checking the
    # warehouse; the fix must check first, so nothing under data_dir exists at all.
    assert not settings.platform.data_dir.exists()
