"""Smoke tests — cheapest wiring checks. No external services, no warehouse."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, cast

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


def _env_render_module() -> Any:
    path = REPO / "config" / ".env-render.py"
    spec = importlib.util.spec_from_file_location("_env_render", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_env_render_script_is_importable() -> None:
    assert callable(_env_render_module().render)


def test_rendered_env_never_uses_reserved_prefect_namespace() -> None:
    """Prefect 3 reads .env via pydantic-settings: a bare PREFECT_* key would hijack its
    own settings and force client→server mode, breaking ephemeral runs. Ours are OGIP_-prefixed.
    """
    module = _env_render_module()
    derived = cast("dict[str, str]", module._derived(module._load()))
    reserved = [k for k in derived if k.startswith("PREFECT_")]
    assert reserved == [], f"reserved Prefect settings emitted into .env: {reserved}"
