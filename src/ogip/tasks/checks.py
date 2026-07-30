"""Check callables — ODOS `checks:` bodies (design §4.6).

Contract: return a dict with a required `"passed": bool`; every other key is metadata.
Adapters turn it into the orchestrator's native check result. Like sensors, a check
reports failure in-band (`passed: False` + reason) instead of raising.
"""

from __future__ import annotations

from ogip.config import get_settings
from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["market_features_nonempty"]


@odos_task("checks.market_features_nonempty")
def market_features_nonempty() -> dict[str, object]:
    """FS layer has rows and popularity_score is never null (feature contract)."""
    warehouse = get_settings().platform.warehouse_path
    if not warehouse.exists():
        return {"passed": False, "reason": "warehouse not built yet"}
    import duckdb

    try:
        con = duckdb.connect(str(warehouse), read_only=True)
        try:
            rows = con.execute("select count(*) from fs.market_features").fetchone()
            nulls = con.execute(
                "select count(*) from fs.market_features where popularity_score is null"
            ).fetchone()
        finally:
            con.close()
    except Exception as exc:  # any warehouse access failure means check cannot run
        log.warning("market_features check: query failed ({e})", e=type(exc).__name__)
        return {"passed": False, "reason": f"query failed ({type(exc).__name__})"}
    n = int(rows[0]) if rows else 0
    bad = int(nulls[0]) if nulls else 0
    log.info("market_features check: rows={n} null_scores={b}", n=n, b=bad)
    return {"passed": n > 0 and bad == 0, "rows": n, "null_popularity_score": bad}
