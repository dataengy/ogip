#!/usr/bin/env python
"""Sync `.ai/tasks/*.md` → GitHub Issues (ADR-0013 / D12).

Idempotent by a stable marker: each issue body carries ``<!-- ogip-task:<slug> -->`` and each
task file gets a ``<!-- github-issue: #N -->`` backlink. Re-runs update instead of duplicating.

Usage: ``uv run python integrations/github/tasks_sync.py [--dry-run]``
Requires the `gh` CLI (auth via the ambient GitHub token — never a secret in this repo).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ogip.logger import logger, setup_logging

REPO = Path(__file__).resolve().parents[2]
TASKS_DIR = REPO / ".ai" / "tasks"
BACKLINK = re.compile(r"<!--\s*github-issue:\s*#(\d+)\s*-->")


@dataclass(frozen=True)
class Task:
    slug: str
    title: str
    body: str
    path: Path
    issue: int | None

    @property
    def marker(self) -> str:
        return f"<!-- ogip-task:{self.slug} -->"


def _gh(*args: str, stdin: str | None = None) -> str:
    proc = subprocess.run(
        ["gh", *args], input=stdin, capture_output=True, text=True, cwd=REPO, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def load_tasks() -> list[Task]:
    tasks: list[Task] = []
    for path in sorted(TASKS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        heading = next((ln for ln in text.splitlines() if ln.startswith("# ")), f"# {path.stem}")
        title = heading.removeprefix("# ").removeprefix("Task — ").strip()
        found = BACKLINK.search(text)
        tasks.append(
            Task(
                slug=path.stem,
                title=title,
                body=text,
                path=path,
                issue=int(found.group(1)) if found else None,
            )
        )
    return tasks


def existing_issue_for(task: Task) -> int | None:
    """Find an already-synced issue by marker (survives a lost backlink)."""
    raw = _gh("issue", "list", "--state", "all", "--limit", "200", "--json", "number,body")
    for item in json.loads(raw or "[]"):
        if task.marker in (item.get("body") or ""):
            number = item.get("number")
            return int(number) if number is not None else None
    return None


def issue_body(task: Task) -> str:
    note = f"_Synced from `.ai/tasks/{task.path.name}` — edit the file, not the issue._"
    return f"{task.marker}\n\n{note}\n\n{task.body}"


def write_backlink(task: Task, number: int) -> None:
    if BACKLINK.search(task.body):
        return
    task.path.write_text(f"{task.body.rstrip()}\n\n<!-- github-issue: #{number} -->\n", "utf-8")


def sync(*, dry_run: bool) -> int:
    tasks = load_tasks()
    logger.info("tasks-sync: {n} task file(s)", n=len(tasks))
    for task in tasks:
        number = task.issue or existing_issue_for(task)
        if dry_run:
            action = "update" if number else "create"
            logger.info("[dry-run] {a} #{n} — {t}", a=action, n=number or "?", t=task.title)
            continue
        body = issue_body(task)
        if number:
            _gh("issue", "edit", str(number), "--title", task.title, "--body-file", "-", stdin=body)
            logger.info("updated #{n} — {t}", n=number, t=task.title)
        else:
            url = _gh("issue", "create", "--title", task.title, "--body-file", "-", stdin=body)
            number = int(url.rstrip("/").rsplit("/", 1)[-1])
            logger.info("created #{n} — {t}", n=number, t=task.title)
        write_backlink(task, number)
    return 0


if __name__ == "__main__":
    setup_logging()
    raise SystemExit(sync(dry_run="--dry-run" in sys.argv[1:]))
