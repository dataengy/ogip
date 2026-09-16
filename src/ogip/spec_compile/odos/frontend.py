"""ODOS frontend (design §8): YAML → validated, resolved spec.

`load_spec()` is the single entry: parse every group file, merge `_defaults`, build the
asset graph, statically expand every `select:`, and validate every name against its
closed vocabulary — the task registry, the graph, the location-wide job namespace.
Anything unresolvable raises OdosSpecError naming the file; nothing is dropped silently
(§7 failure policy). Adapters consume the result; they re-validate nothing.

YAML is loaded with a loader that is NOT plain `yaml.safe_load`: PyYAML's default (YAML 1.1)
bool resolution folds `on`/`off`/`yes`/`no` into booleans, and ODOS keys its automations/hooks
sections with a literal `on:` (§4.5) — under `safe_load` every such key silently becomes the
bool `True` before it ever reaches the IR. See `_YamlLoader` below.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from ogip.spec_compile.odos import ir
from ogip.spec_compile.odos.graph import AssetGraph, SelectedAsset

_REPO = Path(__file__).resolve().parents[4]
SPEC_ORCH = _REPO / "spec" / "orchestration"
SPEC_SQL = _REPO / "spec" / "sql"

# Lane-specific values an adapter injects; the portable spec must not author them.
ADAPTER_OWNED_ARGS = frozenset({"project_dir", "partition"})

_Tasks = Mapping[str, Callable[..., object]]


class _YamlLoader(yaml.SafeLoader):
    """`SafeLoader`, but only `true`/`false` resolve to bool.

    Plain YAML 1.1 (what `SafeLoader` implements) also folds `on`/`off`/`yes`/`no` (any
    case) into booleans — the classic "Norway problem". ODOS keys its automations/hooks
    sections with a literal `on:` (§4.5), so that default would silently rewrite every
    `on:` mapping key to the bool `True` before it ever reaches the IR. Restricting the
    bool tag to `true`/`false` keeps `on` a string without losing real boolean parsing
    (`full_refresh: true`, `blocking: false`, ...).
    """


def _construct_bool(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> bool | str:
    value = loader.construct_scalar(node)
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


_YamlLoader.add_constructor(
    "tag:yaml.org,2002:bool",
    cast("Callable[[yaml.SafeLoader, yaml.Node], object]", _construct_bool),
)


@dataclass(frozen=True)
class ResolvedJob:
    name: str
    group: str
    job: ir.Job
    selection: tuple[SelectedAsset, ...] | None
    retry: ir.Retry | None
    concurrency: ir.Concurrency | None
    on_failure: str | None
    partitions: ir.DailyPartitions | None


@dataclass(frozen=True)
class OdosSpec:
    defaults: ir.DefaultsFile
    groups: dict[str, ir.GroupFile]
    jobs: dict[str, ResolvedJob]
    graph: AssetGraph


def targets_include(targets: list[str] | None, target: str) -> bool:
    return targets is None or target in targets


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = cast("object", yaml.load(path.read_text(encoding="utf-8"), Loader=_YamlLoader))
    if not isinstance(loaded, dict):
        raise ir.OdosSpecError(f"{path.name}: not a YAML mapping")
    return cast("dict[str, object]", loaded)


def _require_task(tasks: _Tasks, name: str, where: str) -> Callable[..., object]:
    if name not in tasks:
        raise ir.OdosSpecError(
            f"{where}: unknown registry name {name!r}; known: {', '.join(sorted(tasks))}"
        )
    return tasks[name]


def load_spec(
    spec_dir: Path = SPEC_ORCH,
    spec_sql_dir: Path = SPEC_SQL,
    *,
    tasks: _Tasks | None = None,
) -> OdosSpec:
    if tasks is None:
        from ogip.tasks import TASKS  # importing registers the whole vocabulary

        tasks = TASKS

    defaults_path = spec_dir / "_defaults.yml"
    if not defaults_path.exists():
        raise ir.OdosSpecError(f"{spec_dir}: _defaults.yml is required")
    try:
        defaults = ir.DefaultsFile.model_validate(_load_yaml(defaults_path))
    except ValidationError as err:
        raise ir.OdosSpecError(f"_defaults.yml: {err}") from err
    partitions = defaults.partitions_defs()
    if defaults.defaults.on_failure is not None:
        _require_task(tasks, defaults.defaults.on_failure, "_defaults.yml: on_failure")

    groups: dict[str, ir.GroupFile] = {}
    for path in sorted(spec_dir.glob("*.yml")):
        if path.name == "_defaults.yml":
            continue
        try:
            group_file = ir.GroupFile.model_validate(_load_yaml(path))
        except ValidationError as err:
            raise ir.OdosSpecError(f"{path.name}: {err}") from err
        if group_file.group != path.stem:
            raise ir.OdosSpecError(
                f"{path.name}: group {group_file.group!r} does not match the filename"
            )
        groups[group_file.group] = group_file

    declared: dict[str, ir.AssetDecl] = {}
    for group_name, group_file in groups.items():
        for asset_name, decl in group_file.assets.items():
            if asset_name in declared:
                raise ir.OdosSpecError(f"asset {asset_name} declared twice")
            declared[asset_name] = decl
            where = f"{group_name}: asset {asset_name}"
            if decl.task is not None:
                _require_task(tasks, decl.task, where)
            if decl.partitions is not None and decl.partitions not in partitions:
                raise ir.OdosSpecError(
                    f"{where}: unknown partitions {decl.partitions!r}; "
                    f"_defaults.yml defines: {sorted(partitions)}"
                )

    graph = AssetGraph.from_spec(spec_sql_dir, declared)

    jobs: dict[str, ResolvedJob] = {}
    for group_name, group_file in groups.items():
        for job_name, job in group_file.jobs.items():
            if job_name in jobs:
                raise ir.OdosSpecError(
                    f"job {job_name} defined in both {jobs[job_name].group} and "
                    f"{group_name} — job names are location-wide"
                )
            jobs[job_name] = _resolve_job(
                group_name, job_name, job, defaults, graph, declared, partitions, tasks
            )

    for group_name, group_file in groups.items():
        for auto_name, automation in group_file.automations.items():
            where = f"{group_name}: automation {auto_name}"
            trigger = automation.trigger
            if isinstance(trigger, ir.PollTrigger):
                _require_task(tasks, trigger.callable_name, where)
            if isinstance(trigger, ir.AssetMaterializedTrigger) and (
                trigger.asset not in graph.nodes
            ):
                raise ir.OdosSpecError(f"{where}: unknown asset {trigger.asset!r}")
            run = trigger.job if isinstance(trigger, ir.PartitionReadyTrigger) else automation.run
            assert run is not None  # guaranteed by ir.Automation validation
            if run not in jobs:
                raise ir.OdosSpecError(f"{where}: runs unknown job {run!r}")
            if jobs[run].group != group_name:
                raise ir.OdosSpecError(
                    f"{where}: job {run!r} lives in group {jobs[run].group!r} — an "
                    "automation must run a job from its own group (0.1 rule)"
                )
            if isinstance(trigger, ir.PartitionReadyTrigger) and jobs[run].partitions is None:
                raise ir.OdosSpecError(f"{where}: partition_ready over an unpartitioned job")
        for check_name, check in group_file.checks.items():
            where = f"{group_name}: check {check_name}"
            _require_task(tasks, check.task, where)
            if check.asset not in graph.nodes:
                raise ir.OdosSpecError(f"{where}: unknown asset {check.asset!r}")
        for hook_name, hook in group_file.hooks.items():
            _require_task(tasks, hook.task, f"{group_name}: hook {hook_name}")

    return OdosSpec(defaults=defaults, groups=groups, jobs=jobs, graph=graph)


def _resolve_job(
    group: str,
    name: str,
    job: ir.Job,
    defaults: ir.DefaultsFile,
    graph: AssetGraph,
    declared: Mapping[str, ir.AssetDecl],
    partitions: Mapping[str, ir.DailyPartitions],
    tasks: _Tasks,
) -> ResolvedJob:
    where = f"{group}: job {name}"
    on_failure = job.on_failure or defaults.defaults.on_failure
    if job.on_failure is not None:
        _require_task(tasks, job.on_failure, where)

    selection: tuple[SelectedAsset, ...] | None = None
    job_partitions: ir.DailyPartitions | None = None
    if job.task is not None:
        fn = _require_task(tasks, job.task, where)
        params = inspect.signature(fn).parameters
        owned = sorted(set(job.args) & ADAPTER_OWNED_ARGS)
        if owned:
            raise ir.OdosSpecError(
                f"{where}: {owned} are adapter-owned (lane-specific) — not spec-authorable"
            )
        unknown = sorted(set(job.args) - set(params))
        if unknown:
            raise ir.OdosSpecError(
                f"{where}: task {job.task} has no parameter(s) {unknown}; accepts: {sorted(params)}"
            )
    else:
        try:
            selection = tuple(graph.expand(job.select_terms))
        except ir.OdosSpecError as err:
            raise ir.OdosSpecError(f"{where}: {err}") from err
        if job.partitioned:
            partition_names = {
                declared[sel.name].partitions if sel.name in declared else None for sel in selection
            }
            if len(partition_names) != 1 or None in partition_names:
                raise ir.OdosSpecError(
                    f"{where}: partitioned, but its selection does not share exactly one "
                    "partitions definition (§4.3)"
                )
            only = partition_names.pop()
            assert only is not None
            job_partitions = partitions[only]

    return ResolvedJob(
        name=name,
        group=group,
        job=job,
        selection=selection,
        retry=job.retry or defaults.defaults.retry,
        concurrency=job.concurrency or defaults.defaults.concurrency,
        on_failure=on_failure,
        partitions=job_partitions,
    )
