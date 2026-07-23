"""Registry semantics: registration, lookup, and the two failure modes that must be loud."""

from pathlib import Path

import pytest

from ogip.tasks import (
    TASKS,
    DuplicateTaskError,
    TaskNotFoundError,
    get_task,
    odos_task,
    task_names,
)


@pytest.fixture(autouse=True)
def _restore_registry():
    """Tests here register probe tasks into the module-global registry.

    Without this, a second run in the same process (pytest --lf, xdist reruns) hits
    DuplicateTaskError on a name a previous test left behind, and later tests see probe
    entries in the project vocabulary. Snapshot and restore around every test.
    """
    saved = dict(TASKS)
    yield
    TASKS.clear()
    TASKS.update(saved)


def test_registered_task_is_retrievable_by_name():
    @odos_task("probe.echo")
    def _echo(value: str) -> str:
        return value

    assert get_task("probe.echo")("hi") == "hi"
    assert "probe.echo" in task_names()


def test_unknown_name_raises_with_the_known_names_listed():
    with pytest.raises(TaskNotFoundError) as excinfo:
        get_task("probe.nope")
    assert "probe.nope" in str(excinfo.value)


def test_unknown_name_error_message_matches_the_raised_arg_verbatim():
    """KeyError.__str__ would quote-wrap and backslash-escape this; guard against that.

    The crisp invariant: ``__str__`` returns the message verbatim, i.e. exactly
    ``exc.args[0]`` — not ``repr(exc.args[0])``, which is what the base
    ``KeyError.__str__`` would produce for a single-argument instance.
    """
    with pytest.raises(TaskNotFoundError) as excinfo:
        get_task("probe.nope")
    exc = excinfo.value
    assert str(exc) == exc.args[0]
    assert "probe.nope" in str(exc)
    assert "known:" in str(exc)


def test_two_arg_construction_falls_back_to_base_keyerror_str():
    """Only the single-composed-message shape is special-cased.

    Any other arity — e.g. two positional args — must fall back to the base
    ``KeyError.__str__`` behaviour (a repr of the args tuple) so extra args
    aren't silently dropped.
    """
    exc = TaskNotFoundError("probe.nope", "extra")
    assert str(exc) == str(KeyError("probe.nope", "extra"))
    assert str(exc) == repr(("probe.nope", "extra"))


def test_duplicate_registration_is_rejected():
    @odos_task("probe.dup")
    def _first() -> None: ...

    with pytest.raises(DuplicateTaskError):

        @odos_task("probe.dup")
        def _second() -> None: ...


def test_task_names_is_sorted():
    @odos_task("probe.zzz")
    def _zzz() -> None: ...

    @odos_task("probe.aaa")
    def _aaa() -> None: ...

    names = task_names()
    assert names == sorted(names)
    assert names.index("probe.aaa") < names.index("probe.zzz")


def test_the_whole_project_vocabulary_is_registered():
    """The closed vocabulary an ODOS spec may address. Adding a name is a deliberate act."""
    assert set(task_names()) == {
        "cdc.catchup",
        "dbt.build",
        "dbt.deps",
        "dbt.parse",
        "ingest.all",
        "ingest.metacritic",
        "ingest.opencritic",
        "ingest.psn",
        "ingest.steamcharts",
        "ingest.parse_to_landing",
        "ingest.rawg",
        "integrations.trigger_prefect",
        "snapshot.write",
    }


def test_every_registered_task_is_keyword_only_or_zero_arg():
    """ODOS passes `args:` as a mapping, so tasks must not rely on positional parameters."""
    import inspect

    for name, fn in TASKS.items():
        params = inspect.signature(fn).parameters.values()
        positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        assert not positional, f"{name} takes positional parameters: {positional}"


def test_cli_parse_args_splits_name_and_raw_string_kwargs():
    """`parse_args` is purely syntactic — it must not guess types from the string shape.

    Coercion happens later, in `main`, once the task is resolved and its declared
    parameter types are known (Finding 1).
    """
    from ogip.tasks.__main__ import parse_args

    name, kwargs = parse_args(["dbt.build", "--full_refresh=true", "--select=tag:daily"])
    assert name == "dbt.build"
    assert kwargs == {"full_refresh": "true", "select": "tag:daily"}


def test_cli_rejects_an_unknown_task_name_with_a_nonzero_exit():
    from ogip.tasks.__main__ import main

    assert main(["definitely.not.a.task"]) == 2


def test_cli_rejects_a_bare_flag_without_a_value():
    from ogip.tasks.__main__ import parse_args

    with pytest.raises(SystemExit):
        parse_args(["dbt.build", "--full_refresh"])


# ---------------------------------------------------------------------------
# Type-driven coercion (Finding 1) — the CLI must coerce `--key=value` by the target
# task's *declared parameter type*, not by guessing from the string's shape. Every task
# below is a probe registered for the duration of one test; the autouse fixture above
# restores the real registry afterwards.
# ---------------------------------------------------------------------------


def test_cli_coerces_a_path_annotated_kwarg_to_an_actual_path():
    """The bug that broke every dbt task: `project_dir: Path` must become a real `Path`."""
    from ogip.tasks.__main__ import main

    captured: dict[str, object] = {}

    @odos_task("probe.path_arg")
    def _path_arg(*, project_dir: Path) -> None:
        captured["project_dir"] = project_dir

    assert main(["probe.path_arg", "--project_dir=transform/dbt"]) == 0
    assert captured["project_dir"] == Path("transform/dbt")
    assert isinstance(captured["project_dir"], Path)


def test_cli_keeps_a_str_annotated_all_digit_value_as_str():
    """An all-digit value must not silently become an `int` when the parameter says `str`."""
    from ogip.tasks.__main__ import main

    captured: dict[str, object] = {}

    @odos_task("probe.str_arg")
    def _str_arg(*, select: str) -> None:
        captured["select"] = select

    assert main(["probe.str_arg", "--select=12345"]) == 0
    assert captured["select"] == "12345"
    assert isinstance(captured["select"], str)


def test_cli_coerces_int_and_bool_annotated_kwargs_by_the_tasks_signature():
    from ogip.tasks.__main__ import main

    captured: dict[str, object] = {}

    @odos_task("probe.typed_args")
    def _typed_args(*, retries: int, dry_run: bool = False) -> None:
        captured["retries"] = retries
        captured["dry_run"] = dry_run

    assert main(["probe.typed_args", "--retries=3", "--dry_run=false"]) == 0
    assert captured == {"retries": 3, "dry_run": False}


def test_cli_bool_annotated_kwarg_rejects_a_non_true_false_value():
    from ogip.tasks.__main__ import main

    @odos_task("probe.bool_arg")
    def _bool_arg(*, dry_run: bool = False) -> None:
        raise AssertionError("must not run: the bad value should be rejected before this")

    with pytest.raises(SystemExit) as excinfo:
        main(["probe.bool_arg", "--dry_run=yes"])
    message = str(excinfo.value)
    assert "dry_run" in message
    assert "yes" in message


def test_cli_unknown_keyword_fails_listing_the_accepted_names():
    from ogip.tasks.__main__ import main

    @odos_task("probe.known_args")
    def _known_args(*, alpha: str = "a", beta: str = "b") -> None:
        raise AssertionError("must not run: the unknown keyword should be rejected first")

    with pytest.raises(SystemExit) as excinfo:
        main(["probe.known_args", "--gamma=1"])
    message = str(excinfo.value)
    assert "gamma" in message
    assert "alpha" in message
    assert "beta" in message


def test_cli_a_task_that_raises_returns_exit_1_instead_of_propagating():
    """Finding 2: a task's own exception must not escape `main` as a raw traceback."""
    from ogip.tasks.__main__ import main

    @odos_task("probe.boom")
    def _boom() -> None:
        raise RuntimeError("boom")

    assert main(["probe.boom"]) == 1


def test_both_lanes_reach_ingestion_through_the_same_registry_task():
    """The drift guard this whole registry exists for.

    `jobs/dg-tasks.sh` and `pipelines/_shared/steps.py` once had independent ingestion bodies —
    one conditional and routed through Dagster, one unconditional and straight to dlt. Identity,
    not equivalence: the two lanes must resolve to the SAME object, so a change to one cannot
    miss the other.
    """
    from pipelines._shared import steps

    assert steps.ingest_raw is get_task("ingest.all")


def test_every_dg_tasks_branch_dispatches_to_the_registry():
    """Bash may alias registry calls; it may not carry logic of its own.

    Asserts the shape of each `case` branch rather than the absence of a substring: a branch
    that grows a second command, or invokes a tool directly, fails here regardless of
    formatting.
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    script = (
        repo / "experimental" / "orchestration" / "dagster_ogip" / "jobs" / "dg-tasks.sh"
    ).read_text(encoding="utf-8")
    body = script.split('case "$task" in', 1)[1].split("esac", 1)[0]

    branches = re.findall(r"^\s*([a-z0-9-]+)\)\s*(.+?)\s*;;\s*$", body, re.MULTILINE)
    assert len(branches) >= 8, f"expected the full task list, parsed {len(branches)} branches"
    for name, command in branches:
        assert command.startswith("ogip_task "), (
            f"branch {name!r} does not dispatch to the registry: {command!r}"
        )
