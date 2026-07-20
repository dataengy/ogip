"""`python -m ogip.tasks <name> [--key=value ...]` — the shell boundary of the registry.

Bash callers (`jobs/dg-tasks.sh`) and any orchestrator that prefers a subprocess reach the
tasks through here, so there is exactly one place where a task name becomes a call.
"""

from __future__ import annotations

import sys

from ogip.logger import log, setup_logging
from ogip.tasks._registry import TaskNotFoundError, get_task, task_names

__all__ = ["main", "parse_args"]


def _coerce(raw: str) -> object:
    if raw in ("true", "false"):
        return raw == "true"
    if raw.isdigit():
        return int(raw)
    return raw


def parse_args(argv: list[str]) -> tuple[str, dict[str, object]]:
    """Split ``<name> --k=v ...`` into the task name and its keyword arguments."""
    if not argv:
        usage = "usage: python -m ogip.tasks <name> [--key=value ...]"
        raise SystemExit(f"{usage}\nknown: {', '.join(task_names())}")
    name, *rest = argv
    kwargs: dict[str, object] = {}
    for item in rest:
        if not item.startswith("--") or "=" not in item:
            raise SystemExit(f"expected --key=value, got {item!r}")
        key, _, value = item[2:].partition("=")
        kwargs[key] = _coerce(value)
    return name, kwargs


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    name, kwargs = parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        task = get_task(name)
    except TaskNotFoundError as exc:
        log.error("{e}", e=exc)
        return 2
    log.bind(task=name).info("running with {k}", k=kwargs)
    task(**kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
