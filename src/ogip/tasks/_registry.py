"""The ODOS task registry — a closed vocabulary of orchestrator-agnostic callables.

A task is a plain typed function. It imports no orchestrator, so Dagster can wrap it in an
`@op` and Prefect in a `@task` without either owning the behaviour. Names are the contract:
ODOS specs address tasks by registry name, and the compiler validates the name at compile
time rather than letting a bad reference surface at runtime.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

__all__ = [
    "TASKS",
    "DuplicateTaskError",
    "TaskNotFoundError",
    "get_task",
    "odos_task",
    "task_names",
]


class TaskNotFoundError(KeyError):
    """No task is registered under that name.

    Subclasses ``KeyError`` so callers may reasonably catch that base class, but
    ``KeyError.__str__`` special-cases a single argument and returns ``repr(arg)``
    instead of ``str(arg)`` — which would quote-wrap and backslash-escape the
    carefully composed "known tasks" message in tracebacks, logs, and the CLI.
    Override ``__str__`` so the message reaches those surfaces unmangled. Only the
    single-composed-message shape gets special-cased; any other arity falls back to
    the base ``KeyError.__str__`` behaviour so extra args aren't silently dropped.
    """

    def __str__(self) -> str:
        return str(self.args[0]) if len(self.args) == 1 else super().__str__()


class DuplicateTaskError(RuntimeError):
    """Two functions claimed the same registry name."""


TASKS: dict[str, Callable[..., object]] = {}

F = TypeVar("F", bound=Callable[..., object])


def odos_task(name: str) -> Callable[[F], F]:
    """Register ``fn`` under ``name``. Duplicate names are a bug, not a last-one-wins."""

    def register(fn: F) -> F:
        if name in TASKS:
            raise DuplicateTaskError(f"task {name!r} is already registered")
        TASKS[name] = fn
        return fn

    return register


def get_task(name: str) -> Callable[..., object]:
    """Look up a task, listing the vocabulary when the name is wrong."""
    try:
        return TASKS[name]
    except KeyError:
        known = ", ".join(task_names())
        raise TaskNotFoundError(f"unknown task {name!r}; known: {known}") from None


def task_names() -> list[str]:
    return sorted(TASKS)
