"""ODOS 0.1 typed IR (design §4, §8) — Pydantic v2, closed vocabulary.

Every model forbids unknown keys (§4.9): any key ODOS does not define is a compile error,
never a pass-through to an orchestrator constructor. Parsing here is file-local and purely
syntactic; cross-file resolution (defaults merge, `select:` expansion, registry validation)
lives in `frontend.py`.
"""

from __future__ import annotations

import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ODOS_VERSION = "0.1"
Target = Literal["dagster", "prefect"]

_NAME = re.compile(r"[a-z_][a-z0-9_]*")
_DOTTED = re.compile(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+")


class OdosSpecError(ValueError):
    """spec/orchestration says something ODOS 0.1 does not define — a compile-time failure."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Retry(_Strict):
    max_attempts: int = Field(ge=1)
    type: Literal["constant", "exponential"] = "constant"
    interval: datetime.timedelta = datetime.timedelta(seconds=30)  # ISO-8601 in YAML (PT30S)


class Concurrency(_Strict):
    limit: int = Field(ge=1)
    behavior: Literal["queue", "cancel", "fail"] = "queue"


class Defaults(_Strict):
    retry: Retry | None = None
    concurrency: Concurrency | None = None
    on_failure: str | None = None


class DailyPartitions(_Strict):
    kind: Literal["daily"] = "daily"
    start: datetime.date


_PARTITIONS = re.compile(r"daily\(start=(\d{4}-\d{2}-\d{2})\)")


def parse_partitions(text: str) -> DailyPartitions:
    match = _PARTITIONS.fullmatch(text.strip())
    if match is None:
        raise OdosSpecError(
            f"unknown partitions form {text!r}; ODOS 0.1 defines daily(start=YYYY-MM-DD)"
        )
    return DailyPartitions(start=datetime.date.fromisoformat(match.group(1)))


def _check_version(value: str) -> str:
    if str(value) != ODOS_VERSION:
        raise ValueError(f"this compiler speaks odos {ODOS_VERSION}, file says {value!r}")
    return str(value)


class DefaultsFile(_Strict):
    odos: str
    owner: str | None = None
    registry: str = "ogip.tasks"
    partitions: dict[str, str] = {}
    defaults: Defaults = Defaults()

    _version = field_validator("odos", mode="before")(_check_version)

    def partitions_defs(self) -> dict[str, DailyPartitions]:
        return {name: parse_partitions(raw) for name, raw in self.partitions.items()}


# ---- `on:` triggers — one key, a closed set of forms (§4.5, §4.6a) ----


class CronTrigger(_Strict):
    cron: str


class AssetMaterializedTrigger(_Strict):
    asset: str


class PollTrigger(_Strict):
    callable_name: str
    every_seconds: int


class PartitionReadyTrigger(_Strict):
    job: str


class RunFailedTrigger(_Strict):
    scope: Literal["location"]


Trigger = CronTrigger | AssetMaterializedTrigger | PollTrigger | PartitionReadyTrigger

_ON = re.compile(r"(?P<fn>[a-z_]+)\((?P<body>.*)\)")


def parse_on(text: str) -> Trigger | RunFailedTrigger:
    match = _ON.fullmatch(text.strip())
    if match is None:
        raise OdosSpecError(f"unparseable trigger {text!r}")
    fn, body = match.group("fn"), match.group("body").strip()
    if fn == "cron":
        quoted = re.fullmatch(r'"([^"]+)"', body)
        if quoted is None or len(quoted.group(1).split()) != 5:
            raise OdosSpecError(f"cron(...) takes a quoted 5-field expression, got {body!r}")
        return CronTrigger(cron=quoted.group(1))
    if fn == "asset_materialized":
        if _DOTTED.fullmatch(body) is None:
            raise OdosSpecError(f"asset_materialized(...) takes a dotted asset name, got {body!r}")
        return AssetMaterializedTrigger(asset=body)
    if fn == "poll":
        poll = re.fullmatch(rf"(?P<c>{_DOTTED.pattern}),\s*every=(?P<n>\d+)s", body)
        if poll is None:
            raise OdosSpecError(
                f"poll(...) takes `<registry callable>, every=<seconds>s`, got {body!r}"
            )
        return PollTrigger(callable_name=poll.group("c"), every_seconds=int(poll.group("n")))
    if fn == "partition_ready":
        if _NAME.fullmatch(body) is None:
            raise OdosSpecError(f"partition_ready(...) takes a job name, got {body!r}")
        return PartitionReadyTrigger(job=body)
    if fn == "run_failed":
        if body != "scope=location":
            raise OdosSpecError(f"run_failed(...) supports only scope=location, got {body!r}")
        return RunFailedTrigger(scope="location")
    raise OdosSpecError(
        f"unknown trigger {fn!r} — ODOS 0.1 defines cron, asset_materialized, poll, "
        "partition_ready, run_failed"
    )


# ---- `select:` — the deliberately small grammar (§4.3) ----


class SelectTerm(_Strict):
    kind: Literal["asset", "tag"]
    name: str
    closure: Literal["exact", "downstream", "upstream"] = "exact"


def parse_select(value: str | list[str]) -> list[SelectTerm]:
    items = [value] if isinstance(value, str) else list(value)
    terms: list[SelectTerm] = []
    for raw in items:
        text = raw.strip()
        if text.startswith("tag:"):
            terms.append(SelectTerm(kind="tag", name=text[4:]))
            continue
        if text.startswith("+") and text.endswith("+"):
            raise OdosSpecError(f"select {raw!r}: +name+ is not in the ODOS 0.1 grammar")
        closure: Literal["exact", "downstream", "upstream"] = "exact"
        if text.endswith("+"):
            closure, text = "downstream", text[:-1]
        elif text.startswith("+"):
            closure, text = "upstream", text[1:]
        if _DOTTED.fullmatch(text) is None:
            raise OdosSpecError(
                f"select {raw!r}: expected a dotted asset name, `name+`, `+name`, or `tag:<t>`"
            )
        terms.append(SelectTerm(kind="asset", name=text, closure=closure))
    if not terms:
        raise OdosSpecError("select: is empty")
    return terms


# ---- the five sections (§4.2) ----


class Job(_Strict):
    doc: str | None = None
    tags: dict[str, str] = {}
    targets: list[Target] | None = None
    select: str | list[str] | None = None
    task: str | None = None
    args: dict[str, str | int | bool] = {}
    partitioned: bool = False
    retry: Retry | None = None
    concurrency: Concurrency | None = None
    on_failure: str | None = None

    @model_validator(mode="after")
    def _one_form(self) -> Job:
        if (self.select is None) == (self.task is None):
            raise ValueError("a job is either `select:` or `task:` — exactly one (§4.3)")
        if self.args and self.task is None:
            raise ValueError("`args:` is only valid on a task job")
        if self.partitioned and self.select is None:
            raise ValueError("`partitioned:` is only valid on a select job")
        if self.select is not None:
            parse_select(self.select)  # surface grammar errors at parse time, with file context
        return self

    @property
    def select_terms(self) -> list[SelectTerm]:
        if self.select is None:
            raise OdosSpecError("select_terms on a task job")
        return parse_select(self.select)


class Automation(_Strict):
    on: str
    run: str | None = None
    doc: str | None = None
    tags: dict[str, str] = {}
    targets: list[Target] | None = None

    @model_validator(mode="after")
    def _trigger_rules(self) -> Automation:
        trigger = parse_on(self.on)
        if isinstance(trigger, RunFailedTrigger):
            raise ValueError("run_failed(...) is a hook trigger, not an automation (§4.6a)")
        if isinstance(trigger, PartitionReadyTrigger):
            if self.run is not None:
                raise ValueError("partition_ready(job) names its job — `run:` must be omitted")
        elif self.run is None:
            raise ValueError(f"`run:` is required for {type(trigger).__name__}")
        return self

    @property
    def trigger(self) -> Trigger:
        trigger = parse_on(self.on)
        assert not isinstance(trigger, RunFailedTrigger)  # excluded by validation
        return trigger


class AssetDecl(_Strict):
    task: str | None = None
    external: bool = False
    partitions: str | None = None
    kinds: list[str] = []
    group_name: str | None = None
    doc: str | None = None
    tags: dict[str, str] = {}
    targets: list[Target] | None = None

    @model_validator(mode="after")
    def _external_or_task(self) -> AssetDecl:
        if self.external == (self.task is not None):
            raise ValueError(
                "an asset is either `task:` (generated) or `external: true` — exactly one"
            )
        if self.external and (self.partitions or self.kinds or self.group_name):
            raise ValueError(
                "an external asset is a reference — no partitions/kinds/group_name on it"
            )
        return self


class Check(_Strict):
    asset: str
    task: str
    blocking: bool = False
    doc: str | None = None
    tags: dict[str, str] = {}
    targets: list[Target] | None = None


class Hook(_Strict):
    on: str
    task: str
    doc: str | None = None
    tags: dict[str, str] = {}
    targets: list[Target] | None = None

    @model_validator(mode="after")
    def _run_failed_only(self) -> Hook:
        if not isinstance(parse_on(self.on), RunFailedTrigger):
            raise ValueError("hooks accept only run_failed(scope=location) (§4.6a)")
        return self


class GroupFile(_Strict):
    odos: str
    group: str
    doc: str | None = None
    assets: dict[str, AssetDecl] = {}
    jobs: dict[str, Job] = {}
    automations: dict[str, Automation] = {}
    checks: dict[str, Check] = {}
    hooks: dict[str, Hook] = {}

    _version = field_validator("odos", mode="before")(_check_version)

    @model_validator(mode="after")
    def _names(self) -> GroupFile:
        if _NAME.fullmatch(self.group) is None:
            raise ValueError(f"group {self.group!r} is not a valid name")
        for section in (self.jobs, self.automations, self.checks, self.hooks):
            for name in section:
                if _NAME.fullmatch(name) is None:
                    raise ValueError(f"{name!r} is not a valid object name ([a-z_][a-z0-9_]*)")
        for name in self.assets:
            if _DOTTED.fullmatch(name) is None:
                raise ValueError(f"asset {name!r} must be a dotted ODTS-style name")
        return self
