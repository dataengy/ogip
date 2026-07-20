"""Registry semantics: registration, lookup, and the two failure modes that must be loud."""

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
    assert set(task_names()) >= {
        "cdc.catchup",
        "dbt.build",
        "dbt.deps",
        "dbt.parse",
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
        positional = [
            p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        assert not positional, f"{name} takes positional parameters: {positional}"
