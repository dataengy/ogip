"""Guard: the back-compat shims and `pipelines._shared` resolve to the SAME objects (#37, Part 3.1).

`pipelines/flows/_common.py`, `pipelines/flows/_paths.py`, and `pipelines/alerting_hooks.py`
became thin re-export shims over `pipelines._shared` so every existing importer keeps working
unchanged while the six separated Prefect sub-projects import the shared step library directly.
Identity, not equivalence: a shim that re-defined instead of re-exporting would still "work" but
would silently diverge from the shared copy.
"""

from __future__ import annotations


def test_shared_lib_and_shims_are_the_same_objects() -> None:
    from pipelines._shared.steps import make_engine_flow as a
    from pipelines.flows._common import make_engine_flow as b

    assert a is b

    from pipelines._shared.alerting import notify_flow_failure as c
    from pipelines.alerting_hooks import notify_flow_failure as d

    assert c is d


def test_shared_lib_and_shims_agree_on_every_preserved_public_name() -> None:
    from pipelines import _shared, alerting_hooks
    from pipelines.flows import _common, _paths

    for name in ("ingest_raw", "build_warehouse", "build_ml_outputs", "publish_outputs"):
        assert getattr(_shared, name) is getattr(_common, name)

    for name in ("REPO", "SPEC_SQL", "SQLMESH_DIR"):
        assert getattr(_shared, name) is getattr(_paths, name)

    assert _shared.notify_flow_failure is alerting_hooks.notify_flow_failure
