"""Poll callables — the portable core of ODOS `on: poll` sensors (design §4.5, §7.2).

Each returns a cursor token (str) or None meaning "nothing to watch". The orchestrator
adapter owns cursor storage and comparison; these functions hold no state and NEVER raise
for an unavailable upstream — a dead landing DB is a skip, not a sensor crash.
"""

from __future__ import annotations

import os
from pathlib import Path

from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["landing_rowcount", "spec_sql_mtime"]

_REPO = Path(__file__).resolve().parents[3]
_SPEC_SQL = _REPO / "spec" / "sql"


@odos_task("sensors.landing_rowcount")
def landing_rowcount() -> str | None:
    """Total live rows in the Postgres `landing` schema, as a cursor token."""
    dsn = os.environ.get("OGIP_PG_DSN")
    if not dsn:
        log.info("landing_rowcount: OGIP_PG_DSN not set — no landing DB to watch")
        return None
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=5) as conn:
            row = conn.execute(
                "select coalesce(sum(n_live_tup), 0) from pg_stat_user_tables "
                "where schemaname = 'landing'"
            ).fetchone()
    except Exception as exc:  # any transport failure means "skip this tick"
        log.warning("landing_rowcount: landing DB unavailable ({e})", e=type(exc).__name__)
        return None
    return str(row[0] if row else 0)


@odos_task("sensors.spec_sql_mtime")
def spec_sql_mtime() -> str | None:
    """Newest mtime under spec/sql, as a cursor token; None when no spec files exist."""
    latest = max((p.stat().st_mtime for p in _SPEC_SQL.rglob("*.sql")), default=0.0)
    return f"{latest:.0f}" if latest else None
