"""dbt task command construction.

These assert the argv the registry builds, not dbt's behaviour — running dbt belongs to the
integration/e2e tiers. The point is that ONE code path serves both orchestrators, so the flags
are pinned here where a regression is cheap to see.

`_regenerate` (spec compilation) and `_run` (the actual `subprocess.run`) are mocked
throughout — these tests must not execute dbt or compile `spec/`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import call, patch

from ogip.tasks.dbt import dbt_build, dbt_command, dbt_deps

PROJECT = Path("transform/dbt")


def test_build_places_project_flags_after_the_subcommand():
    argv = dbt_command(PROJECT, "build")
    assert argv[:5] == ["uv", "run", "--group", "engines", "dbt"]
    assert argv[5] == "build"
    assert "--project-dir" in argv
    # dbt rejects --project-dir before the subcommand; the verb must come first.
    assert argv.index("build") < argv.index("--project-dir")


def test_extra_flags_are_appended_after_the_project_flags():
    argv = dbt_command(PROJECT, "build", "--full-refresh")
    assert argv[-1] == "--full-refresh"


def test_project_and_profiles_dirs_both_point_at_the_project():
    argv = dbt_command(PROJECT, "parse")
    assert argv[argv.index("--project-dir") + 1] == str(PROJECT)
    assert argv[argv.index("--profiles-dir") + 1] == str(PROJECT)


# ---------------------------------------------------------------------------
# dbt.deps — force vs. gated (Finding 1: the standalone `dbt-deps` bash task ran
# unconditionally; the internal `ensure_deps()` helper skipped when `dbt_packages/`
# already existed. Both behaviours must survive the collapse into one function.)
# ---------------------------------------------------------------------------


def test_dbt_deps_default_skips_when_dbt_packages_already_exists(tmp_path: Path) -> None:
    (tmp_path / "dbt_packages").mkdir()
    with (
        patch("ogip.tasks.dbt._regenerate") as mock_regenerate,
        patch("ogip.tasks.dbt._run") as mock_run,
    ):
        dbt_deps(project_dir=tmp_path)
    mock_regenerate.assert_called_once_with(tmp_path)
    mock_run.assert_not_called()


def test_dbt_deps_default_runs_when_dbt_packages_absent(tmp_path: Path) -> None:
    with (
        patch("ogip.tasks.dbt._regenerate") as mock_regenerate,
        patch("ogip.tasks.dbt._run") as mock_run,
    ):
        dbt_deps(project_dir=tmp_path)
    mock_regenerate.assert_called_once_with(tmp_path)
    mock_run.assert_called_once_with(tmp_path, "deps")


def test_dbt_deps_force_runs_unconditionally_even_when_packages_exist(tmp_path: Path) -> None:
    (tmp_path / "dbt_packages").mkdir()
    with (
        patch("ogip.tasks.dbt._regenerate") as mock_regenerate,
        patch("ogip.tasks.dbt._run") as mock_run,
    ):
        dbt_deps(project_dir=tmp_path, force=True)
    mock_regenerate.assert_called_once_with(tmp_path)
    mock_run.assert_called_once_with(tmp_path, "deps")


# ---------------------------------------------------------------------------
# dbt.build — the flag matrix that replaced six bash tasks (Finding 2). `_regenerate`
# and `_run` are the only dbt/spec-touching seams; `dbt_deps` itself runs for real
# (against `tmp_path`, so its `dbt_packages/` gate is exercised too) to prove the
# implicit regenerate-then-deps still happens ahead of the build.
# ---------------------------------------------------------------------------


def test_dbt_build_plain_runs_build_with_no_extra_flags(tmp_path: Path) -> None:
    with (
        patch("ogip.tasks.dbt._regenerate") as mock_regenerate,
        patch("ogip.tasks.dbt._run") as mock_run,
    ):
        dbt_build(project_dir=tmp_path)
    mock_regenerate.assert_called_once_with(tmp_path)
    assert mock_run.call_args_list == [
        call(tmp_path, "deps"),  # dbt_deps ran (dbt_packages/ absent under tmp_path)
        call(tmp_path, "build"),
    ]


def test_dbt_build_full_refresh_appends_the_flag(tmp_path: Path) -> None:
    with (
        patch("ogip.tasks.dbt._regenerate") as mock_regenerate,
        patch("ogip.tasks.dbt._run") as mock_run,
    ):
        dbt_build(project_dir=tmp_path, full_refresh=True)
    mock_regenerate.assert_called_once_with(tmp_path)
    assert mock_run.call_args_list == [
        call(tmp_path, "deps"),
        call(tmp_path, "build", "--full-refresh"),
    ]


def test_dbt_build_select_appends_the_select_flag(tmp_path: Path) -> None:
    with (
        patch("ogip.tasks.dbt._regenerate") as mock_regenerate,
        patch("ogip.tasks.dbt._run") as mock_run,
    ):
        dbt_build(project_dir=tmp_path, select="package:dbt_project_evaluator")
    mock_regenerate.assert_called_once_with(tmp_path)
    assert mock_run.call_args_list == [
        call(tmp_path, "deps"),
        call(tmp_path, "build", "--select", "package:dbt_project_evaluator"),
    ]


def test_dbt_build_select_and_state_appends_both_flags(tmp_path: Path) -> None:
    with (
        patch("ogip.tasks.dbt._regenerate") as mock_regenerate,
        patch("ogip.tasks.dbt._run") as mock_run,
    ):
        dbt_build(project_dir=tmp_path, select="state:modified+", state="dbt")
    mock_regenerate.assert_called_once_with(tmp_path)
    assert mock_run.call_args_list == [
        call(tmp_path, "deps"),
        call(tmp_path, "build", "--select", "state:modified+", "--state", "dbt"),
    ]
