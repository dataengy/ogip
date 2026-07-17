#!/usr/bin/env python
"""Data-quality runner — executes the assertions declared in ``spec/dq`` + Bruin column
checks against the warehouse (ADR-0008 severity model: ``error`` blocks, ``warn`` records).

Phase 0 stub: no rules exist yet (they arrive with ``spec/`` in Phase 1 and the executor in
Phase 4). ``--fast`` is the pre-push subset. Exits 0 cleanly so the hook/gate is wired now.
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    fast = "--fast" in argv
    scope = "fast (pre-push subset)" if fast else "full"
    # TODO(phase-4): load spec/dq/policy.yml + Bruin checks, run against DuckDB, record results.
    print(f"[dq] {scope}: no data-quality rules defined yet (arrive in Phase 1/4) — OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
