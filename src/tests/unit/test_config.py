"""Unit tests for the typed configuration layer (no external services)."""

from __future__ import annotations

from ogip.config import get_settings, load_app_config


def test_settings_build_from_ssot() -> None:
    settings = get_settings()
    assert settings.platform.warehouse_path.name == "ogip.duckdb"
    assert settings.platform.outputs_dir.name == "outputs"
    assert settings.pg.database


def test_demo_mode_when_no_credentials() -> None:
    # No source API keys set in the test env → demo mode drives from sample data.
    assert get_settings().demo_mode is True


def test_app_config_is_a_mapping() -> None:
    cfg = load_app_config()
    assert cfg["transformation"]["engine"] == "sqlmesh"
    assert "prefect-sqlmesh" in cfg["run_profiles"]
