"""ODOS task registry — see `_registry` for the contract, the sibling modules for the tasks."""

from ogip.tasks._registry import (
    TASKS,
    DuplicateTaskError,
    TaskNotFoundError,
    get_task,
    odos_task,
    task_names,
)

__all__ = [
    "TASKS",
    "DuplicateTaskError",
    "TaskNotFoundError",
    "get_task",
    "odos_task",
    "task_names",
]

# Importing the task modules is what populates the registry. Keep this at the bottom: the
# modules import `odos_task` from `ogip.tasks._registry`, not from this package.
from ogip.tasks import dbt as dbt
