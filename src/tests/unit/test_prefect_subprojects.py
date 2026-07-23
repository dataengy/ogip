"""Guard: each engine gets a separately-deployable Prefect sub-project (#37, Part 3.2).

`pipelines/<engine>/{__init__.py,flow.py,prefect.yaml}` — one per SQL profile plus `dagster` —
each importing the shared step library from `pipelines._shared` (Part 3.1). Old
`pipelines/flows/engines/prefect_*.py` modules keep working (retired in Part 3.3); this is
purely additive.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

_ENGINES = ["sqlmesh", "dbt", "bruin", "opendbt", "sqlmesh_dbt", "dagster"]


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


def test_dagster_shim_reexports_moved_seam() -> None:
    import pipelines.dagster.flow as moved
    from pipelines.flows.engines.prefect_dagster import DAGSTER_PROJECT, flow, run_dagster_dlt_dbt

    assert DAGSTER_PROJECT is moved.DAGSTER_PROJECT
    assert flow is moved.flow
    assert run_dagster_dlt_dbt is moved.run_dagster_dlt_dbt
