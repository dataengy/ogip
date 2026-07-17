#!/usr/bin/env python
"""Sync ``.ai/tasks/*.md`` → GitHub Issues — one tracker, no second copy to maintain.

GitHub Issues/Projects is the single tracker (D12); ``.ai/tasks/`` is where the detail is
authored. This pushes the latter into the former: one issue per task file, created once and
updated in place thereafter.

Matching is by a hidden marker (``<!-- ogip-task: <slug> -->``) embedded in the issue body,
not by title — titles get edited, and a title-matched sync silently opens duplicates the
first time someone rewords a heading. Issues are listed and matched locally rather than via
``gh issue list --search``, whose index lags behind writes by seconds to minutes.

Usage::

    just tasks-sync              # create/update issues
    just tasks-sync --dry-run    # print the plan, touch nothing
    just tasks-sync --close-done # also close issues whose task file is marked done
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

REPO = Path(__file__).resolve().parent.parent.parent
TASKS_DIR = REPO / ".ai" / "tasks"
REPO_SLUG = "dataengy/ogip"
TRACKER_LABEL = "task"

MARKER_RE = re.compile(r"<!--\s*ogip-task:\s*(?P<slug>[a-z0-9._-]+)\s*-->")
H1_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(?P<status>.+?)\s*$", re.MULTILINE)
DONE_TOKENS = ("✅", "done", "shipped")


@dataclass(frozen=True)
class Task:
    """One `.ai/tasks/<slug>.md` file."""

    slug: str
    path: Path
    title: str
    done: bool
    body: str


@dataclass(frozen=True)
class Issue:
    """One existing GitHub issue that carries our marker."""

    number: int
    title: str
    state: str
    body: str


def _gh(args: list[str]) -> str:
    """Run `gh` and return stdout. A non-zero exit aborts — never a silent skip."""
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def marker(slug: str) -> str:
    return f"<!-- ogip-task: {slug} -->"


def _issue_body(task: Task) -> str:
    """Issue body = the task file verbatim, plus provenance and the match marker."""
    source = f".ai/tasks/{task.path.name}"
    link = f"https://github.com/{REPO_SLUG}/blob/main/{source}"
    return (
        f"{task.body.rstrip()}\n\n---\n"
        f"_Synced from [`{source}`]({link}) by `just tasks-sync` — "
        f"edit the task file, not this issue._\n\n"
        f"{marker(task.slug)}\n"
    )


def discover_tasks() -> list[Task]:
    """Read every task file. A file without an H1 is a bug in the file, so say so."""
    tasks: list[Task] = []
    for path in sorted(TASKS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")

        h1 = H1_RE.search(text)
        if h1 is None:
            raise SystemExit(f"{path}: no '# ' H1 heading — cannot derive an issue title")
        title = h1.group("title").strip()

        status_match = STATUS_RE.search(text)
        status = status_match.group("status").lower() if status_match else ""
        done = any(token in status for token in DONE_TOKENS)

        tasks.append(Task(slug=path.stem, path=path, title=title, done=done, body=text))
    return tasks


def existing_issues() -> dict[str, Issue]:
    """Map slug → issue, for every issue carrying our marker. Local match, no search index."""
    raw = _gh(
        [
            "issue",
            "list",
            "--repo",
            REPO_SLUG,
            "--state",
            "all",
            "--limit",
            "200",
            "--json",
            "number,title,state,body",
        ]
    )
    parsed: object = json.loads(raw)
    if not isinstance(parsed, list):
        raise SystemExit("gh issue list did not return a JSON array")
    entries = cast(list[dict[str, object]], parsed)

    found: dict[str, Issue] = {}
    for entry in entries:
        body = str(entry.get("body") or "")
        hit = MARKER_RE.search(body)
        if hit is None:
            continue
        found[hit.group("slug")] = Issue(
            number=int(str(entry["number"])),
            title=str(entry["title"]),
            state=str(entry["state"]).lower(),
            body=body,
        )
    return found


def _ensure_label(dry_run: bool) -> None:
    """Create the tracker label if the repo lacks it — `issue create --label` errors without it.

    `--force` makes this idempotent: it updates the label in place when it already exists.
    """
    raw = _gh(["label", "list", "--repo", REPO_SLUG, "--json", "name"])
    parsed: object = json.loads(raw)
    names = {str(item.get("name")) for item in cast(list[dict[str, object]], parsed)}
    if TRACKER_LABEL in names:
        return
    if dry_run:
        print(f"  [dry-run] LABEL   create '{TRACKER_LABEL}' (absent from repo)")
        return
    _gh(
        [
            "label",
            "create",
            TRACKER_LABEL,
            "--repo",
            REPO_SLUG,
            "--description",
            "Synced from .ai/tasks/ by just tasks-sync",
            "--color",
            "0e8a16",
            "--force",
        ]
    )
    print(f"  LABEL    created '{TRACKER_LABEL}'")


def _create(task: Task, dry_run: bool) -> int | None:
    """Create the issue and return its number (None under --dry-run, which creates nothing)."""
    body = _issue_body(task)
    if dry_run:
        print(f"  [dry-run] CREATE  {task.slug}  «{task.title}»")
        return None
    out = _gh(
        [
            "issue",
            "create",
            "--repo",
            REPO_SLUG,
            "--title",
            task.title,
            "--body",
            body,
            "--label",
            TRACKER_LABEL,
        ]
    ).strip()
    print(f"  CREATED  {task.slug}  → {out}")
    # `gh issue create` prints the issue URL; the trailing path segment is the number.
    number = out.rsplit("/", 1)[-1]
    if not number.isdigit():
        raise SystemExit(f"could not parse issue number from gh output: {out!r}")
    return int(number)


def _update(task: Task, issue: Issue, dry_run: bool) -> None:
    body = _issue_body(task)
    title_changed = issue.title != task.title
    body_changed = issue.body.strip() != body.strip()
    if not (title_changed or body_changed):
        print(f"  unchanged  {task.slug}  (#{issue.number})")
        return
    changed = [name for name, flag in (("title", title_changed), ("body", body_changed)) if flag]
    what = ", ".join(changed)
    if dry_run:
        print(f"  [dry-run] UPDATE  {task.slug}  (#{issue.number}) — {what}")
        return
    _gh(
        [
            "issue",
            "edit",
            str(issue.number),
            "--repo",
            REPO_SLUG,
            "--title",
            task.title,
            "--body",
            body,
        ]
    )
    print(f"  UPDATED  {task.slug}  (#{issue.number}) — {what}")


def _close(task: Task, number: int, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] CLOSE   {task.slug}  (#{number}) — task marked done")
        return
    _gh(["issue", "close", str(number), "--repo", REPO_SLUG, "--reason", "completed"])
    print(f"  CLOSED   {task.slug}  (#{number})")


def sync(dry_run: bool, close_done: bool) -> int:
    tasks = discover_tasks()
    if not tasks:
        print(f"no task files in {TASKS_DIR} — nothing to sync")
        return 0

    issues = existing_issues()
    mode = " · DRY-RUN" if dry_run else ""
    print(f"tasks: {len(tasks)} · issues carrying a marker: {len(issues)}{mode}")
    _ensure_label(dry_run)

    for task in tasks:
        issue = issues.get(task.slug)
        if issue is None:
            # A task can already be done the first time it is synced (back-filling shipped
            # work). Close it in the same pass, or it would sit open until the next run.
            number = _create(task, dry_run)
            if close_done and task.done and number is not None:
                _close(task, number, dry_run)
            continue
        _update(task, issue, dry_run)
        if close_done and task.done and issue.state != "closed":
            _close(task, issue.number, dry_run)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync .ai/tasks/*.md → GitHub Issues.")
    parser.add_argument("--dry-run", action="store_true", help="print the plan; change nothing")
    parser.add_argument(
        "--close-done",
        action="store_true",
        help="close issues whose task file Status says done/shipped",
    )
    args = parser.parse_args()
    return sync(dry_run=bool(args.dry_run), close_done=bool(args.close_done))


if __name__ == "__main__":
    sys.exit(main())
