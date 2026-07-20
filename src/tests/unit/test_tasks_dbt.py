"""dbt task command construction.

These assert the argv the registry builds, not dbt's behaviour — running dbt belongs to the
integration/e2e tiers. The point is that ONE code path serves both orchestrators, so the flags
are pinned here where a regression is cheap to see.
"""

from pathlib import Path

from ogip.tasks.dbt import dbt_command

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
