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
