"""Guard: primary vs experimental Prefect sub-projects (re-root #40).

The two PRIMARY comparison candidates — **dbt** and **bruin** — stay on the default path under
`pipelines/<engine>/`. The five demoted engines (sqlmesh, plain_sql, opendbt, sqlmesh_dbt,
dagster) move OFF the default path to `experimental/pipelines/<engine>/`. Each sub-project is a
separately-deployable `{__init__.py,flow.py,prefect.yaml}` importing the shared step library from
`pipelines._shared`; `pipelines._shared.engines.ENGINE_FLOWS` is the only flow registry.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

_PRIMARY = ["dbt", "bruin"]
_EXPERIMENTAL = ["sqlmesh", "plain_sql", "opendbt", "sqlmesh_dbt", "dagster"]
_ALL = _PRIMARY + _EXPERIMENTAL


def _base(engine: str) -> Path:
    return (Path("pipelines") if engine in _PRIMARY else Path("experimental/pipelines")) / engine


@pytest.mark.parametrize("engine", _ALL)
def test_each_engine_is_a_separated_subproject(engine: str) -> None:
    base = _base(engine)
    assert (base / "flow.py").is_file()
    assert (base / "prefect.yaml").is_file()
    module = "pipelines" if engine in _PRIMARY else "experimental.pipelines"
    flow = importlib.import_module(f"{module}.{engine}.flow").flow
    assert callable(flow)


@pytest.mark.parametrize("engine", _EXPERIMENTAL)
def test_experimental_engines_are_off_the_default_path(engine: str) -> None:
    assert not (Path("pipelines") / engine).exists(), (
        f"{engine} must live under experimental/pipelines/, not pipelines/"
    )


@pytest.mark.parametrize("engine", _ALL)
def test_prefect_yaml_is_valid_with_deployments(engine: str) -> None:
    doc = yaml.safe_load((_base(engine) / "prefect.yaml").read_text())
    assert doc.get("deployments")


def test_engine_flows_registry_points_at_every_subproject() -> None:
    """Primary maps to `pipelines.<e>.flow`, experimental to `experimental.pipelines.<e>.flow`."""
    from pipelines._shared.engines import ENGINE_FLOWS

    assert set(ENGINE_FLOWS) == set(_ALL)
    for engine, module_path in ENGINE_FLOWS.items():
        prefix = "pipelines" if engine in _PRIMARY else "experimental.pipelines"
        assert module_path == f"{prefix}.{engine}.flow"
        assert callable(importlib.import_module(module_path).flow)
