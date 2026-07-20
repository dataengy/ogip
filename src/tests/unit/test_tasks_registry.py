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


def test_duplicate_registration_is_rejected():
    @odos_task("probe.dup")
    def _first() -> None: ...

    with pytest.raises(DuplicateTaskError):

        @odos_task("probe.dup")
        def _second() -> None: ...


def test_task_names_is_sorted():
    assert task_names() == sorted(task_names())
