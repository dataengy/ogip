"""Guard: each engine gets a separately-deployable Prefect sub-project (#37, Part 3.2/3.3).

`pipelines/<engine>/{__init__.py,flow.py,prefect.yaml}` — one per SQL profile (including
`plain_sql`) plus `dagster` — each importing the shared step library from `pipelines._shared`
(Part 3.1). The old `pipelines/flows/engines/prefect_*.py` modules and the `ENGINE_FLOWS`
registry that lived alongside them were retired in Part 3.3: every consumer now resolves an
engine's flow through one of these sub-projects (see `pipelines._shared.engines.ENGINE_FLOWS`).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

_ENGINES = ["sqlmesh", "plain_sql", "dbt", "bruin", "opendbt", "sqlmesh_dbt", "dagster"]


@pytest.mark.parametrize("engine", _ENGINES)
def test_each_engine_is_a_separated_subproject(engine: str) -> None:
    base = Path("pipelines") / engine
    assert (base / "flow.py").is_file()
    assert (base / "prefect.yaml").is_file()
    flow = importlib.import_module(f"pipelines.{engine}.flow").flow
    assert callable(flow)


@pytest.mark.parametrize("engine", _ENGINES)
def test_prefect_yaml_is_valid_with_deployments(engine: str) -> None:
    path = Path("pipelines") / engine / "prefect.yaml"
    doc = yaml.safe_load(path.read_text())
    assert doc.get("deployments")


def test_engine_flows_registry_points_at_every_subproject() -> None:
    """`pipelines._shared.engines.ENGINE_FLOWS` is the ONLY registry now — no `engines/` package."""
    from pipelines._shared.engines import ENGINE_FLOWS

    assert set(ENGINE_FLOWS) == set(_ENGINES)
    for engine, module_path in ENGINE_FLOWS.items():
        assert module_path == f"pipelines.{engine}.flow"
        assert callable(importlib.import_module(module_path).flow)
