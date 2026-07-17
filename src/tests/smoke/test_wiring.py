"""Smoke tests — cheapest wiring checks. No external services, no warehouse."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

REPO = Path(__file__).resolve().parents[3]


def test_package_imports() -> None:
    import ogip

    assert ogip.__version__


def test_config_yml_has_core_sections() -> None:
    import yaml

    cfg = yaml.safe_load((REPO / "config" / "config.yml").read_text(encoding="utf-8"))
    required = ("platform", "storage", "postgres", "transformation", "ingestion", "run_profiles")
    for section in required:
        assert section in cfg, f"config.yml missing '{section}'"
    assert cfg["transformation"]["engine"] == "sqlmesh"
    assert cfg["ingestion"]["engine"] == "dlt"


def test_env_render_script_is_importable() -> None:
    path = REPO / "config" / ".env-render.py"
    spec = importlib.util.spec_from_file_location("_env_render", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.render)
