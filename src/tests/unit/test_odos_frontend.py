"""Cross-file resolution: defaults merge, expansion, and the closed-world validations."""

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from ogip.spec_compile.odos.frontend import load_spec
from ogip.spec_compile.odos.ir import OdosSpecError

_REPO = Path(__file__).resolve().parents[3]


def _toy_sql(tmp_path: Path) -> Path:
    spec_sql = tmp_path / "sql"
    (spec_sql / "raw").mkdir(parents=True)
    (spec_sql / "raw" / "a.sql").write_text(
        "/* @bruin\nname: raw.a\ntags: [daily]\n@bruin */\nselect 1 as x\n"
    )
    (spec_sql / "staging").mkdir()
    (spec_sql / "staging" / "b.sql").write_text(
        "/* @bruin\nname: staging.b\ndepends:\n  - raw.a\n@bruin */\nselect x from raw.a\n"
    )
    return spec_sql


def _toy_tasks() -> Mapping[str, Callable[..., object]]:
    def build(*, project_dir: Path, full_refresh: bool = False, select: str | None = None) -> None:
        del project_dir, full_refresh, select

    def token() -> str | None:
        return None

    def alert(*, run_id: str, message: str = "") -> None:
        del run_id, message

    return {"dbt.build": build, "sensors.token": token, "alerting.notify": alert}


def _write_spec(tmp_path: Path, group_body: str, defaults: str | None = None) -> Path:
    spec = tmp_path / "orchestration"
    spec.mkdir(exist_ok=True)
    (spec / "_defaults.yml").write_text(
        defaults or "odos: 0.1\ndefaults:\n  retry: {max_attempts: 3, interval: PT1M}\n"
    )
    (spec / "warehouse.yml").write_text(group_body)
    return spec


_GOOD = """odos: 0.1
group: warehouse
jobs:
  build_job: {task: dbt.build, args: {full_refresh: true}}
  layers_job: {select: raw.a+}
automations:
  hourly: {on: cron("0 * * * *"), run: build_job}
  polled: {on: "poll(sensors.token, every=60s)", run: build_job}
"""


def test_good_spec_resolves(tmp_path: Path) -> None:
    spec = load_spec(_write_spec(tmp_path, _GOOD), _toy_sql(tmp_path), tasks=_toy_tasks())
    build = spec.jobs["build_job"]
    assert build.retry is not None and build.retry.max_attempts == 3  # merged default
    layers = spec.jobs["layers_job"]
    assert layers.selection is not None
    assert [s.name for s in layers.selection] == ["raw.a", "staging.b"]


def test_job_level_retry_overrides_default(tmp_path: Path) -> None:
    body = _GOOD.replace(
        "build_job: {task: dbt.build, args: {full_refresh: true}}",
        "build_job: {task: dbt.build, retry: {max_attempts: 7}}",
    )
    spec = load_spec(_write_spec(tmp_path, body), _toy_sql(tmp_path), tasks=_toy_tasks())
    retry = spec.jobs["build_job"].retry
    assert retry is not None and retry.max_attempts == 7


def test_unknown_task_name_lists_vocabulary(tmp_path: Path) -> None:
    body = _GOOD.replace("task: dbt.build", "task: dbt.bulid")
    with pytest.raises(OdosSpecError, match=r"dbt\.build"):  # message names the real vocabulary
        load_spec(_write_spec(tmp_path, body), _toy_sql(tmp_path), tasks=_toy_tasks())


def test_unknown_poll_callable_fails(tmp_path: Path) -> None:
    body = _GOOD.replace("sensors.token", "sensors.typo")
    with pytest.raises(OdosSpecError, match=r"sensors\.typo"):
        load_spec(_write_spec(tmp_path, body), _toy_sql(tmp_path), tasks=_toy_tasks())


def test_unknown_arg_name_fails_at_compile_time(tmp_path: Path) -> None:
    """The plan-1 CLI defect class, moved to compile time: arg names checked vs signature."""
    body = _GOOD.replace("args: {full_refresh: true}", "args: {full_refres: true}")
    with pytest.raises(OdosSpecError, match="full_refres"):
        load_spec(_write_spec(tmp_path, body), _toy_sql(tmp_path), tasks=_toy_tasks())


def test_adapter_owned_arg_is_rejected(tmp_path: Path) -> None:
    body = _GOOD.replace("args: {full_refresh: true}", 'args: {project_dir: "transform/dbt"}')
    with pytest.raises(OdosSpecError, match="adapter-owned"):
        load_spec(_write_spec(tmp_path, body), _toy_sql(tmp_path), tasks=_toy_tasks())


def test_automation_running_unknown_job_fails(tmp_path: Path) -> None:
    body = _GOOD.replace("run: build_job", "run: ghost_job", 1)
    with pytest.raises(OdosSpecError, match="ghost_job"):
        load_spec(_write_spec(tmp_path, body), _toy_sql(tmp_path), tasks=_toy_tasks())


def test_group_filename_mismatch_fails(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, _GOOD.replace("group: warehouse", "group: wares"))
    with pytest.raises(OdosSpecError, match="filename"):
        load_spec(spec, _toy_sql(tmp_path), tasks=_toy_tasks())


def test_duplicate_job_name_across_groups_fails(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, _GOOD)
    (spec / "ingestion.yml").write_text(
        "odos: 0.1\ngroup: ingestion\njobs:\n  build_job: {task: dbt.build}\n"
    )
    with pytest.raises(OdosSpecError, match="location-wide"):
        load_spec(spec, _toy_sql(tmp_path), tasks=_toy_tasks())


def test_cross_group_run_ref_fails(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, _GOOD)
    (spec / "ingestion.yml").write_text(
        "odos: 0.1\ngroup: ingestion\nautomations:\n"
        '  cross: {on: cron("0 * * * *"), run: build_job}\n'
    )
    with pytest.raises(OdosSpecError, match="own group"):
        load_spec(spec, _toy_sql(tmp_path), tasks=_toy_tasks())


def test_the_real_committed_spec_loads() -> None:
    """The acceptance test: the design-§6 model compiles against the real registry."""
    spec = load_spec()
    assert set(spec.groups) == {
        "ingestion",
        "integrations",
        "maintenance",
        "monitoring",
        "snapshots",
        "warehouse",
    }
    dwh = spec.jobs["dwh_assets_job"]
    assert dwh.selection is not None
    # Property assertions, not an exact list: `raw.rawg__games+` is a real downstream closure
    # over spec/sql lineage, which grows as sources are added (metacritic/opencritic/psn/
    # steamcharts fan in through staging.stg_game_match before fs.market_features) — pinning
    # an exact member list here would go stale on the next spec/sql addition.
    names = [s.name for s in dwh.selection]
    canonical_layers = {"raw.rawg__games", "staging.stg_games", "core.game", "fs.market_features"}
    assert canonical_layers <= set(names)  # the four canonical layers are all present
    assert names[0] == "raw.rawg__games"  # topo order: root first
    assert names[-1] == "fs.market_features"  # topo order: sink last
    assert all(not s.exact for s in dwh.selection)  # closure roles -> view-rooted keys
    assert len(names) == len(set(names))  # no dupes
    snap = spec.jobs["market_snapshot_job"]
    assert snap.partitions is not None and str(snap.partitions.start) == "2026-07-01"
