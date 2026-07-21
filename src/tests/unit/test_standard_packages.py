"""Machine-readable conformance checks for the standards packages under ``spec/``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

_REPO = Path(__file__).resolve().parents[3]
_ODOS = _REPO / "spec" / "ODOS"
_EXAMPLES = _ODOS / "examples"
_ODTS = _REPO / "spec" / "ODTS"
_ODTS_EXAMPLES = _ODTS / "examples"
_SPEC_SQL = _REPO / "spec" / "sql"

# SPEC.md §3 — the closed 0.1 directive vocabulary.
_ODTS_DIRECTIVES = {"model", "kind", "owner", "tags", "depends", "columns", "checks", "imports"}


def _mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"{path} must contain a YAML mapping"
    return cast("dict[str, Any]", value)


def _validator() -> Draft202012Validator:
    schema_value = json.loads((_ODOS / "schema.json").read_text(encoding="utf-8"))
    assert isinstance(schema_value, dict)
    schema = cast("dict[str, Any]", schema_value)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_odos_schema_is_valid_and_accepts_every_conformance_example() -> None:
    validator = _validator()
    documents = sorted(_EXAMPLES.glob("*.yml"))
    assert len(documents) == 7
    for path in documents:
        validator.validate(_mapping(path))  # pyright: ignore[reportUnknownMemberType]


def test_odos_examples_cover_the_six_normative_groups_once() -> None:
    groups = {
        str(_mapping(path)["group"])
        for path in _EXAMPLES.glob("*.yml")
        if path.name != "_defaults.yml"
    }
    assert groups == {
        "warehouse",
        "ingestion",
        "snapshots",
        "maintenance",
        "integrations",
        "monitoring",
    }


def test_odos_example_job_and_partition_references_resolve() -> None:
    defaults = _mapping(_EXAMPLES / "_defaults.yml")
    partition_names = set(cast("dict[str, Any]", defaults.get("partitions", {})))

    for path in _EXAMPLES.glob("*.yml"):
        if path.name == "_defaults.yml":
            continue
        document = _mapping(path)
        jobs = cast("dict[str, Any]", document.get("jobs", {}))
        automations = cast("dict[str, dict[str, Any]]", document.get("automations", {}))
        assets = cast("dict[str, dict[str, Any]]", document.get("assets", {}))

        for automation in automations.values():
            trigger = str(automation["on"])
            if trigger.startswith("partition_ready("):
                job_name = trigger.removeprefix("partition_ready(").removesuffix(")")
            else:
                job_name = str(automation["run"])
            assert job_name in jobs, f"{path}: automation references unknown job {job_name!r}"

        for name, asset in assets.items():
            partition = asset.get("partitions")
            if partition is not None:
                assert partition in partition_names, (
                    f"{path}: asset {name!r} references unknown partition {partition!r}"
                )


def test_odos_closed_vocabulary_rejects_unknown_keys() -> None:
    document = _mapping(_EXAMPLES / "warehouse.yml")
    document["orchestrator_kwargs"] = {"silently": "vendor-specific"}
    with pytest.raises(ValidationError):
        _validator().validate(document)  # pyright: ignore[reportUnknownMemberType]


def test_odos_target_specific_hook_requires_an_explicit_target() -> None:
    document = _mapping(_EXAMPLES / "monitoring.yml")
    hooks = cast("dict[str, dict[str, Any]]", document["hooks"])
    hooks["dwh_run_failure_alert"].pop("targets")
    with pytest.raises(ValidationError):
        _validator().validate(document)  # pyright: ignore[reportUnknownMemberType]


@pytest.mark.parametrize("forbidden_key", ["task", "args"])
def test_odos_asset_selection_job_rejects_task_only_fields(forbidden_key: str) -> None:
    document = _mapping(_EXAMPLES / "warehouse.yml")
    jobs = cast("dict[str, dict[str, Any]]", document["jobs"])
    jobs["staging_job"][forbidden_key] = "dbt.build" if forbidden_key == "task" else {}
    with pytest.raises(ValidationError):
        _validator().validate(document)  # pyright: ignore[reportUnknownMemberType]


def _odts_header_and_body(text: str) -> tuple[list[str], str]:
    """Split an ``@odts`` document into header lines (sans version line) and the SQL body."""
    assert text.startswith("/* @odts 0.1\n"), "first line must declare the @odts version"
    header, sep, body = text.partition("*/\n")
    assert sep, "header comment must close with '*/'"
    return header.splitlines()[1:], body


def _directive_names(header_lines: list[str]) -> set[str]:
    names: set[str] = set()
    for line in header_lines:
        if not line.strip() or line.startswith((" ", "\t")):
            continue  # blanks and indented block entries (columns, checks, imports)
        names.add(line.split()[0].rstrip(":"))
    return names


def test_odts_package_publishes_the_normative_files() -> None:
    for name in ("README.md", "SPEC.md", "GOVERNING-BRIEF.md", "IMPLEMENTATION.md"):
        assert (_ODTS / name).is_file(), f"spec/ODTS/{name} missing"
    assert len(sorted(_ODTS_EXAMPLES.glob("*/*.sql"))) == 6


def test_odts_fixtures_use_the_closed_vocabulary_and_match_their_paths() -> None:
    for path in sorted(_ODTS_EXAMPLES.glob("*/*.sql")):
        header, _ = _odts_header_and_body(path.read_text(encoding="utf-8"))
        names = _directive_names(header)
        unknown = names - _ODTS_DIRECTIVES
        assert not unknown, f"{path}: unknown directives {sorted(unknown)}"
        assert {"model", "kind"} <= names, f"{path}: model and kind are required"
        model_line = next(line for line in header if line.startswith("model"))
        assert model_line.split()[1] == f"{path.parent.name}.{path.stem}", (
            f"{path}: model name must equal <layer>.<file-stem>"
        )


def test_odts_closed_vocabulary_detects_unknown_directives() -> None:
    header, _ = _odts_header_and_body("/* @odts 0.1\nmodel a.b\nmaterialize table\n*/\nselect 1\n")
    assert _directive_names(header) - _ODTS_DIRECTIVES == {"materialize"}


def test_contracts_are_valid_odcs_and_anchored_to_raw_models() -> None:
    """Every ODCS contract either has its raw model in spec/sql or declares contract-first.

    Encodes the source DoD: a connector that lands Parquet with no contract is invisible
    here, but a contract that names a dataset must either be backed by a `raw.<name>`
    registration or say explicitly that the connector is still owed.
    """
    contracts = sorted((_REPO / "spec" / "contracts").rglob("*.odcs.yaml"))
    assert contracts, "spec/contracts must not be empty"
    for path in contracts:
        document = _mapping(path)
        assert document["kind"] == "DataContract", path
        name = str(document["name"])
        tables = cast("list[dict[str, Any]]", document["schema"])
        assert tables and cast("list[Any]", tables[0]["properties"]), f"{path}: empty schema"
        assert cast("list[Any]", document["quality"]), f"{path}: no quality rules"
        servers = cast("list[dict[str, Any]]", document["servers"])
        assert servers[0]["path"] == f".run/data/raw/{name}/", f"{path}: server path mismatch"

        if (_SPEC_SQL / "raw" / f"{name}.sql").is_file():
            continue  # implemented: the Layer-0 registration exists
        custom = cast("list[dict[str, Any]]", document.get("customProperties", []))
        statuses = [
            str(entry["value"]) for entry in custom if entry.get("property") == "connectorStatus"
        ]
        assert statuses and statuses[0].startswith("contract-first"), (
            f"{path}: no raw model in spec/sql and no contract-first declaration"
        )


def test_odts_fixture_bodies_are_byte_identical_to_spec_sql() -> None:
    for path in sorted(_ODTS_EXAMPLES.glob("*/*.sql")):
        live = _SPEC_SQL / path.parent.name / path.name
        assert live.is_file(), f"{path} has no live counterpart at {live}"
        _, fixture_body = _odts_header_and_body(path.read_text(encoding="utf-8"))
        _, sep, live_body = live.read_text(encoding="utf-8").partition("@bruin */\n")
        assert sep, f"{live}: expected a legacy @bruin header"
        assert fixture_body == live_body, f"{path}: SQL body drifted from {live}"
