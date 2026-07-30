"""`python -m ogip.tasks <name> [--key=value ...]` — the shell boundary of the registry.

Bash callers (`jobs/dg-tasks.sh`) and any orchestrator that prefers a subprocess reach the
tasks through here, so there is exactly one place where a task name becomes a call.

Exit codes are the contract a shell caller branches on:
  0 — the task ran and returned normally.
  1 — the task name resolved but the call itself failed: a CLI usage error (an unknown
      `--key`, or a value that doesn't match the parameter's declared type) exits via
      `SystemExit` with a message naming the problem; a task that raised while running is
      caught, logged with `log.exception` (full traceback), and turned into this same code
      so a bug inside a task never leaks a raw traceback past this boundary.
  2 — the task name is not in the registry.
"""

from __future__ import annotations

import inspect
import sys
import types
import typing
from collections.abc import Callable
from pathlib import Path

from ogip.logger import log, setup_logging
from ogip.tasks._registry import TaskNotFoundError, get_task, task_names

__all__ = ["main", "parse_args"]


def parse_args(argv: list[str]) -> tuple[str, dict[str, str]]:
    """Split ``<name> --k=v ...`` into the task name and its raw (string) argument values.

    Purely syntactic — this function knows nothing about any task's parameter types.
    Coercing those raw strings into the right Python types happens in `_bind_kwargs`, once
    the task is resolved, because the *target function's declared parameter type* is what
    must drive coercion — not the shape of the string.
    """
    if not argv:
        usage = "usage: python -m ogip.tasks <name> [--key=value ...]"
        raise SystemExit(f"{usage}\nknown: {', '.join(task_names())}")
    name, *rest = argv
    raw_kwargs: dict[str, str] = {}
    for item in rest:
        if not item.startswith("--") or "=" not in item:
            raise SystemExit(f"expected --key=value, got {item!r}")
        key, _, value = item[2:].partition("=")
        raw_kwargs[key] = value
    return name, raw_kwargs


def _coerce_value(param_name: str, raw: str, annotation: object) -> object:
    """Convert `raw` to whatever `annotation` says the parameter should be.

    - `bool` — accepts exactly ``true``/``false`` (case-sensitive); anything else is a
      `SystemExit` naming the parameter and the accepted values.
    - `int` — `int(raw)`, with a clear `SystemExit` on failure instead of a bare
      `ValueError` traceback.
    - `Path` — `Path(raw)`.
    - `str` — left as-is.
    - an optional/union annotation such as `str | None` — coerced as its single
      non-`None` member (e.g. as `str`); a union with more than one non-`None` member is
      ambiguous and falls through to "leave it alone".
    - no annotation, or a type not covered above — the raw string, unguessed.
    """
    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        members = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        if len(members) == 1:
            return _coerce_value(param_name, raw, members[0])
        return raw

    if annotation is bool:
        if raw not in ("true", "false"):
            raise SystemExit(f"--{param_name} expects 'true' or 'false', got {raw!r}")
        return raw == "true"
    if annotation is int:
        try:
            return int(raw)
        except ValueError:
            raise SystemExit(f"--{param_name} expects an int, got {raw!r}") from None
    if annotation is Path:
        return Path(raw)
    if annotation is str:
        return raw
    return raw


def _bind_kwargs(
    name: str, task: Callable[..., object], raw_kwargs: dict[str, str]
) -> dict[str, object]:
    """Coerce `raw_kwargs` by `task`'s declared parameter types; reject unknown keys.

    Annotations are resolved with `typing.get_type_hints` rather than read off
    `__annotations__` directly, so this works whether or not the task's module uses
    ``from __future__ import annotations`` (which turns annotations into strings).
    """
    params = inspect.signature(task).parameters
    unknown = sorted(key for key in raw_kwargs if key not in params)
    if unknown:
        accepted = ", ".join(sorted(params)) or "(none)"
        raise SystemExit(
            f"task {name!r} got unknown keyword(s) {', '.join(unknown)}; accepts: {accepted}"
        )
    hints = typing.get_type_hints(task)
    return {key: _coerce_value(key, raw, hints.get(key)) for key, raw in raw_kwargs.items()}


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    name, raw_kwargs = parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        task = get_task(name)
    except TaskNotFoundError as exc:
        log.error("{e}", e=exc)
        return 2
    kwargs = _bind_kwargs(name, task, raw_kwargs)
    log.bind(task=name).info("running with {k}", k=kwargs)
    try:
        task(**kwargs)
    except Exception:
        log.exception("task {t} failed", t=name)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
