"""Render parsed Bruin assets into a dbt project (ADR-0005).

The `dagster_dbt.DbtProjectComponent` needs a real dbt project, but `spec/` stays the SSoT —
so we generate one. Bruin's schema-qualified deps (`from staging.stg_games`) are rewritten to
dbt `{{ ref('stg_games') }}`, and Bruin column checks become dbt tests in `schema.yml`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import yaml

from .bruin import Asset, load_assets
from .dialect import rewrite_refs

# stdlib logging (named `log` per the house convention), NOT loguru/ogip.logger: this compiler is
# imported by the nested Dagster subproject's venv (experimental/orchestration/dagster_ogip), which
# does not depend on loguru — so it cannot import ogip.logger.
log = logging.getLogger(__name__)

_MATERIALIZATION = {"table": "table", "view": "view"}


def _check_value(check: dict[str, Any]) -> Any:
    """Bruin spells a check's argument `value:`; some checks carry a mapping, some a list."""
    return check.get("value")


def _column_test(check: dict[str, Any]) -> str | dict[str, Any] | None:
    """Bruin column check -> dbt column test.

    A bare str is a dbt builtin generic test; a dict is a parameterised test (builtin or from a
    package — dbt_utils/dbt_expectations are always installed, see `_DBT_PACKAGES`). Unknown
    names return None and are dropped WITH A WARNING by the caller rather than silently — a
    silent drop once hid `non_negative` from the generated project entirely.
    """
    name = str(check.get("name"))
    value = _check_value(check)
    if name in ("not_null", "unique"):
        return name
    if name == "accepted_values":
        values = list(cast("list[Any]", value)) if isinstance(value, list) else []
        return {"accepted_values": {"values": values}}
    if name == "relationships":
        # value: {to: <model name>, field: <column>} — `to` is rendered as a dbt ref().
        rel = cast("dict[str, Any]", value) if isinstance(value, dict) else {}
        return {
            "relationships": {
                "to": f"ref('{rel.get('to')}')",
                "field": str(rel.get("field", "id")),
            }
        }
    if name == "non_negative":
        # >= 0; dbt_utils.accepted_range with only min_value is the idiomatic spelling.
        return {"dbt_utils.accepted_range": {"min_value": 0}}
    if name == "accepted_range":
        # value: {min: <n>, max: <n>} — either bound may be omitted.
        rng = cast("dict[str, Any]", value) if isinstance(value, dict) else {}
        args: dict[str, Any] = {}
        if rng.get("min") is not None:
            args["min_value"] = rng["min"]
        if rng.get("max") is not None:
            args["max_value"] = rng["max"]
        return {"dbt_utils.accepted_range": args}
    if name == "matches_regex":
        return {"dbt_expectations.expect_column_values_to_match_regex": {"regex": str(value)}}
    return None


def _model_test(check: dict[str, Any]) -> dict[str, Any] | None:
    """Bruin ASSET-level check -> dbt model-level test (things no single column can express)."""
    name = str(check.get("name"))
    value = _check_value(check)
    if name == "not_empty":
        return {"dbt_expectations.expect_table_row_count_to_be_between": {"min_value": 1}}
    if name == "row_count_between":
        rng = cast("dict[str, Any]", value) if isinstance(value, dict) else {}
        args: dict[str, Any] = {}
        if rng.get("min") is not None:
            args["min_value"] = rng["min"]
        if rng.get("max") is not None:
            args["max_value"] = rng["max"]
        return {"dbt_expectations.expect_table_row_count_to_be_between": args}
    return None


# Well-known dbt-hub packages, emitted into the generated project's packages.yml (installed by
# `dbt deps`). Version ranges, not pins, so dbt resolves the newest compatible release. These
# are the widely DuckDB-compatible utilities; opinionated/heavier ones (automate_dv for Data
# Vault, elementary for observability) are opt-in via OGIP_DBT_EXTRA_PACKAGES=1.
_DBT_PACKAGES: list[dict[str, object]] = [
    {"package": "dbt-labs/dbt_utils", "version": [">=1.1.1", "<2.0.0"]},
    {"package": "dbt-labs/codegen", "version": [">=0.12.0", "<1.0.0"]},
    {"package": "dbt-labs/audit_helper", "version": [">=0.12.0", "<1.0.0"]},
    {"package": "dbt-labs/dbt_project_evaluator", "version": [">=0.14.0", "<1.0.0"]},
    {"package": "dbt-labs/dbt_external_tables", "version": [">=0.9.0", "<1.0.0"]},
    {"package": "godatadriven/dbt_date", "version": [">=0.10.0", "<1.0.0"]},
    {"package": "metaplane/dbt_expectations", "version": [">=0.10.0", "<1.0.0"]},
    {"package": "data-mie/dbt_profiler", "version": [">=0.8.0", "<1.0.0"]},
]
_DBT_PACKAGES_EXTRA: list[dict[str, object]] = [
    {"package": "Datavault-UK/automate_dv", "version": [">=0.11.0", "<1.0.0"]},
    {"package": "elementary-data/elementary", "version": [">=0.16.0", "<1.0.0"]},
]


def _rewrite_refs(sql: str, assets: list[Asset]) -> str:
    """`from staging.stg_games` -> `from {{ ref('stg_games') }}` for every known model.

    AST-scoped (see `dialect.py`): a text substitution would also rewrite the name where it
    appears inside a string literal or a comment, producing silently wrong SQL.
    """
    return rewrite_refs(sql, {a.name: f"{{{{ ref('{a.model}') }}}}" for a in assets})


def _absolutize_runtime_paths(sql: str, repo_root: Path) -> str:
    """`read_parquet('.run/…')` -> an absolute path.

    Spec SQL carries repo-relative runtime paths. That works for the SQLMesh target (run from
    the repo root) but NOT for dbt: Dagster/dbt execute from the dbt project directory, so a
    relative path silently resolves to the wrong place and the model reads nothing.
    """
    return sql.replace("'.run/", f"'{repo_root}/.run/")


def _model_sql(asset: Asset, assets: list[Asset], repo_root: Path) -> str:
    materialized = _MATERIALIZATION.get(asset.materialization, "table")
    # `cast` rather than bare isinstance narrowing: YAML gives Any, and pyright strict rejects
    # the resulting list[Unknown] element types.
    tags_value = asset.meta.get("tags")
    tag_list = (
        [str(t) for t in cast("list[Any]", tags_value)] if isinstance(tags_value, list) else []
    )
    # schema=<layer> + the generate_schema_name macro (below) → dbt materializes into the
    # platform's layer schemas (stg/core/fs), matching the SQLMesh target instead of flattening
    # into dbt's default `main`. The `raw` layer is left unqualified on purpose: it is only an
    # external-registration view over the Parquet the dlt asset produces, and qualifying it as
    # `raw` would collide with the dlt asset's Dagster key `raw/<table>`.
    schema_cfg = "" if asset.schema == "raw" else f"schema='{asset.schema}', "
    config = f"{{{{ config(materialized='{materialized}', {schema_cfg}tags={tag_list!r}) }}}}"
    body = _absolutize_runtime_paths(_rewrite_refs(asset.sql, assets), repo_root)
    return f"{config}\n\n{body}\n"


def _schema_yml(assets: list[Asset]) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    for asset in assets:
        columns_value = asset.meta.get("columns")
        columns_meta = cast("list[Any]", columns_value) if isinstance(columns_value, list) else []
        columns: list[dict[str, Any]] = []
        for col_value in columns_meta:
            if not isinstance(col_value, dict):
                continue
            col = cast("dict[str, Any]", col_value)
            checks_value = col.get("checks")
            checks = cast("list[Any]", checks_value) if isinstance(checks_value, list) else []
            tests: list[str | dict[str, Any]] = []
            for c in checks:
                if not isinstance(c, dict):
                    continue
                check = cast("dict[str, Any]", c)
                test = _column_test(check)
                if test is None:
                    log.warning(
                        "spec check %r on %s.%s has no dbt mapping — dropped",
                        check.get("name"),
                        asset.model,
                        col.get("name"),
                    )
                    continue
                tests.append(test)
            entry: dict[str, Any] = {"name": str(col.get("name"))}
            if col.get("description"):
                entry["description"] = str(col["description"])
            if tests:
                entry["data_tests"] = tests
            columns.append(entry)
        model: dict[str, Any] = {"name": asset.model}
        if asset.meta.get("description"):
            model["description"] = str(asset.meta["description"])
        # ASSET-level checks -> model-level data_tests (row counts etc.; no one column owns them)
        asset_checks_value = asset.meta.get("checks")
        asset_checks = (
            cast("list[Any]", asset_checks_value) if isinstance(asset_checks_value, list) else []
        )
        model_tests: list[dict[str, Any]] = []
        for c in asset_checks:
            if not isinstance(c, dict):
                continue
            check = cast("dict[str, Any]", c)
            mtest = _model_test(check)
            if mtest is None:
                log.warning(
                    "spec asset-level check %r on %s has no dbt mapping — dropped",
                    check.get("name"),
                    asset.model,
                )
                continue
            model_tests.append(mtest)
        if model_tests:
            model["data_tests"] = model_tests
        if columns:
            model["columns"] = columns
        models.append(model)

    schema: dict[str, Any] = {"version": 2, "models": models}
    # dbt UNIT tests (dbt >= 1.8): logic tests over mocked inputs, no warehouse data needed.
    # Spec carries them verbatim under `unit_tests:` — they are model-logic fixtures, not DQ.
    unit_tests: list[dict[str, Any]] = []
    for asset in assets:
        ut_value = asset.meta.get("unit_tests")
        for ut in cast("list[Any]", ut_value) if isinstance(ut_value, list) else []:
            if not isinstance(ut, dict):
                continue
            entry_ut = dict(cast("dict[str, Any]", ut))
            entry_ut["model"] = asset.model
            unit_tests.append(entry_ut)
    if unit_tests:
        schema["unit_tests"] = unit_tests
    return schema


def compile_to_dbt(
    spec_sql_dir: Path,
    project_dir: Path,
    *,
    warehouse: Path,
    repo_root: Path,
    with_packages: bool = True,
) -> list[str]:
    """Generate a runnable dbt (duckdb) project from `spec/sql`; return model names.

    ``with_packages=False`` emits an empty ``packages.yml``. Needed by every flavor that does
    not run stock dbt-core: SQLMesh's dbt loader cannot render the hub packages' runtime jinja,
    and OpenDBT pins dbt <1.10 where the hub versions we track refuse to install. Those
    comparisons target *our* models, not dbt's tooling.
    """
    assets = load_assets(spec_sql_dir)
    models_dir = project_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    for stale in models_dir.rglob("*"):
        if stale.is_file():
            stale.unlink()

    for asset in assets:
        target = models_dir / asset.schema / f"{asset.model}.sql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_model_sql(asset, assets, repo_root), encoding="utf-8")

    (models_dir / "schema.yml").write_text(
        yaml.safe_dump(_schema_yml(assets), sort_keys=False), encoding="utf-8"
    )

    # SINGULAR tests — one .sql per Bruin `custom_checks` entry. A dbt singular test is just a
    # query that must return ZERO rows; spec owns the query, so bespoke assertions stay in the
    # SSoT instead of being hand-written into the generated project (or into the orchestrator).
    tests_dir = project_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    for stale in tests_dir.glob("*.sql"):
        stale.unlink()
    for asset in assets:
        custom_value = asset.meta.get("custom_checks")
        for cc in cast("list[Any]", custom_value) if isinstance(custom_value, list) else []:
            if not isinstance(cc, dict):
                continue
            custom = cast("dict[str, Any]", cc)
            query = custom.get("query")
            if not query:
                log.warning(
                    "custom_check %r on %s has no `query` — skipped",
                    custom.get("name"),
                    asset.model,
                )
                continue
            fname = f"{asset.model}__{str(custom.get('name', 'custom')).strip()}.sql"
            body = _absolutize_runtime_paths(_rewrite_refs(str(query), assets), repo_root)
            (tests_dir / fname).write_text(f"-- GENERATED from spec/ custom_checks\n{body}\n")
    # Use each model's configured `schema` verbatim (no `<target>_` prefix) so the layer
    # schemas match the SQLMesh target and the platform contract (fs.market_features etc.).
    macros_dir = project_dir / "macros"
    macros_dir.mkdir(parents=True, exist_ok=True)
    (macros_dir / "generate_schema_name.sql").write_text(
        "{% macro generate_schema_name(custom_schema_name, node) -%}\n"
        "    {%- if custom_schema_name is none -%}{{ target.schema }}"
        "{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}\n"
        "{%- endmacro %}\n",
        encoding="utf-8",
    )
    (project_dir / "dbt_project.yml").write_text(
        yaml.safe_dump(
            {
                "name": "ogip",
                "version": "0.1.0",
                "profile": "ogip",
                "model-paths": ["models"],
                # singular tests live in tests/ (generated from spec `custom_checks`)
                "test-paths": ["tests"],
                "models": {"ogip": {"+materialized": "table"}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "profiles.yml").write_text(
        yaml.safe_dump(
            {
                "ogip": {
                    "target": "dev",
                    "outputs": {"dev": {"type": "duckdb", "path": str(warehouse), "threads": 4}},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    import os

    packages: list[dict[str, object]] = []
    if with_packages:
        packages = list(_DBT_PACKAGES)
        if os.environ.get("OGIP_DBT_EXTRA_PACKAGES") == "1":
            packages += _DBT_PACKAGES_EXTRA
    (project_dir / "packages.yml").write_text(
        yaml.safe_dump({"packages": packages}, sort_keys=False), encoding="utf-8"
    )
    # dbt writes run artifacts + its user cookie into the project dir — never commit those.
    (project_dir / ".gitignore").write_text(
        "target/\ndbt_packages/\nlogs/\n.user.yml\n", encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        "# GENERATED dbt project — from `spec/` (ADR-0005), do not hand-edit\n\n"
        "Regenerate via `src/ogip/spec_compile` (`just spec-compile dbt`); "
        "edit `spec/sql/` instead.\n",
        encoding="utf-8",
    )
    return [asset.name for asset in assets]
