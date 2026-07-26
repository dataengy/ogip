"""ODOS IR: the closed vocabulary (§4.9), the `on:` grammar (§4.5), the select grammar (§4.3)."""

import datetime

import pytest
from pydantic import ValidationError

from ogip.spec_compile.odos.ir import (
    AssetDecl,
    AssetMaterializedTrigger,
    Automation,
    CronTrigger,
    GroupFile,
    Job,
    OdosSpecError,
    PartitionReadyTrigger,
    PollTrigger,
    Retry,
    RunFailedTrigger,
    parse_on,
    parse_partitions,
    parse_select,
)


def test_unknown_key_anywhere_is_rejected() -> None:
    """§4.9 — the single largest divergence from dag-factory: no pass-through, ever."""
    with pytest.raises(ValidationError, match="cron_schedule"):
        GroupFile.model_validate(
            {
                "odos": "0.1",
                "group": "warehouse",
                "jobs": {"j": {"task": "dbt.build", "cron_schedule": "0 * * * *"}},
            }
        )


def test_job_is_exactly_select_xor_task() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        Job.model_validate({"select": "core.game", "task": "dbt.build"})
    with pytest.raises(ValidationError, match="exactly one"):
        Job.model_validate({})
    with pytest.raises(ValidationError, match="args"):
        Job.model_validate({"select": "core.game", "args": {"x": 1}})


def test_retry_interval_parses_iso8601_duration() -> None:
    retry = Retry.model_validate({"max_attempts": 3, "type": "exponential", "interval": "PT1M"})
    assert retry.interval == datetime.timedelta(minutes=1)


def test_on_grammar_all_four_forms() -> None:
    assert parse_on('cron("0 3 * * *")') == CronTrigger(cron="0 3 * * *")
    assert parse_on("asset_materialized(raw.rawg__games)") == AssetMaterializedTrigger(
        asset="raw.rawg__games"
    )
    assert parse_on("poll(sensors.landing_rowcount, every=60s)") == PollTrigger(
        callable_name="sensors.landing_rowcount", every_seconds=60
    )
    assert parse_on("partition_ready(market_snapshot_job)") == PartitionReadyTrigger(
        job="market_snapshot_job"
    )
    assert parse_on("run_failed(scope=location)") == RunFailedTrigger(scope="location")


@pytest.mark.parametrize(
    "bad",
    [
        "webhook(x)",  # unknown trigger
        'cron("0 3 * *")',  # 4 fields
        "cron(0 3 * * *)",  # unquoted
        "poll(sensors.x)",  # missing every=
        "poll(sensors.x, every=60)",  # missing s suffix
        "run_failed(scope=job)",  # only location
    ],
)
def test_on_grammar_rejects(bad: str) -> None:
    with pytest.raises(OdosSpecError):
        parse_on(bad)


def test_select_grammar() -> None:
    terms = parse_select(["raw.rawg__games+", "+fs.market_features", "tag:daily", "core.game"])
    assert [(t.kind, t.name, t.closure) for t in terms] == [
        ("asset", "raw.rawg__games", "downstream"),
        ("asset", "fs.market_features", "upstream"),
        ("tag", "daily", "exact"),
        ("asset", "core.game", "exact"),
    ]
    with pytest.raises(OdosSpecError):
        parse_select("+core.game+")
    with pytest.raises(OdosSpecError):
        parse_select("core game")


def test_automation_run_rules() -> None:
    with pytest.raises(ValidationError, match="run"):
        Automation.model_validate({"on": 'cron("0 * * * *")'})  # cron needs run:
    with pytest.raises(ValidationError, match="omitted"):
        Automation.model_validate(
            {"on": "partition_ready(snap_job)", "run": "other_job"}  # partition_ready forbids it
        )
    auto = Automation.model_validate({"on": "poll(sensors.spec_sql_mtime, every=30s)", "run": "j"})
    assert isinstance(auto.trigger, PollTrigger)


def test_asset_decl_external_xor_task() -> None:
    AssetDecl.model_validate({"external": True})
    AssetDecl.model_validate({"task": "snapshot.write"})
    with pytest.raises(ValidationError, match="exactly one"):
        AssetDecl.model_validate({"external": True, "task": "snapshot.write"})
    with pytest.raises(ValidationError, match="reference"):
        AssetDecl.model_validate({"external": True, "group_name": "marts"})


def test_partitions_expression() -> None:
    p = parse_partitions("daily(start=2026-07-01)")
    assert p.start == datetime.date(2026, 7, 1)
    with pytest.raises(OdosSpecError):
        parse_partitions("hourly(start=2026-07-01)")


def test_group_file_version_gate() -> None:
    with pytest.raises(ValidationError, match=r"0\.1"):
        GroupFile.model_validate({"odos": "0.2", "group": "warehouse"})
