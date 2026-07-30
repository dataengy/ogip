"""Regression test — `fs.market_features` coverage flags must reflect an actual match, not the
bridge row's existence.

`core.critic_reception` / `core.console_pricing` / `core.traction` are each a LEFT JOIN of
`staging.stg_game_match` (every rawg title, matched or not) onto one source. Their `game_sk` is
therefore projected straight off the bridge row and is NEVER null — a coverage flag written as
``<source>.game_sk is not null`` would be true even for a rawg game with zero matches in that
source. `spec/sql/fs/market_features.sql` instead tests the actual measured column
(``coalesce(cr.metacritic_score, cr.opencritic_score) is not null`` etc.). This test seeds a
synthetic warehouse with one game that matches every source and one that matches none, and runs
the real committed model bodies (`spec/sql/**`, copied verbatim — not reimplemented) through the
plain-SQL runner already used by `src/tests/unit/test_spec_compile.py`.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from transform.runner import run_plain_sql

_REPO = Path(__file__).resolve().parents[3]
_SPEC_SQL = _REPO / "spec" / "sql"

# Real committed model bodies, copied verbatim into the synthetic spec tree below — this test
# exercises the actual pipeline SQL, not a reimplementation of it, so it tracks drift.
_COPIED_MODELS = [
    "staging/stg_game_match.sql",
    "core/game.sql",
    "core/critic_reception.sql",
    "core/console_pricing.sql",
    "core/traction.sql",
    "fs/market_features.sql",
]

# Synthetic replacements for the raw->staging layer (skips `read_parquet(...)`) — one rawg game
# ("Neon Drift") matched in every source, one ("Solo Quest") matched in none.
_STG_GAMES = """/* @bruin
name: staging.stg_games
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    (1, 'Neon Drift', 'neon-drift', date '2023-05-01', 4.2, 120, 81, 12, 500)
    , (2, 'Solo Quest', 'solo-quest', date '2022-01-15', 3.5, 40, cast(null as integer), 6, 90)
) as t(
    game_id, name, slug, released_date, rating, ratings_count, metacritic, playtime_hours
    , added_count
)
"""

_STG_METACRITIC = """/* @bruin
name: staging.stg_metacritic_games
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    ('Neon Drift', 88)
) as t(name, metascore)
"""

_STG_OPENCRITIC = """/* @bruin
name: staging.stg_opencritic_games
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    ('Neon Drift', 90)
) as t(name, score)
"""

_STG_PSN = """/* @bruin
name: staging.stg_psn_concepts
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    ('Neon Drift', 'en-us', cast(59.99 as double), 'USD')
) as t(name, locale, price, currency)
"""

_STG_STEAMCHARTS = """/* @bruin
name: staging.stg_steamcharts_apps
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    ('Neon Drift', 1200, 1500, 20000)
) as t(name, current_players, peak_24h, peak_all)
"""

_SYNTHETIC = {
    "staging/stg_games.sql": _STG_GAMES,
    "staging/stg_metacritic_games.sql": _STG_METACRITIC,
    "staging/stg_opencritic_games.sql": _STG_OPENCRITIC,
    "staging/stg_psn_concepts.sql": _STG_PSN,
    "staging/stg_steamcharts_apps.sql": _STG_STEAMCHARTS,
}


@pytest.fixture
def synthetic_spec(tmp_path: Path) -> Path:
    spec = tmp_path / "sql"
    for rel, text in _SYNTHETIC.items():
        path = spec / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for rel in _COPIED_MODELS:
        path = spec / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((_SPEC_SQL / rel).read_text(encoding="utf-8"), encoding="utf-8")
    return spec


def test_unmatched_game_gets_false_coverage_flags_and_null_features(
    synthetic_spec: Path, tmp_path: Path
) -> None:
    warehouse = tmp_path / "wh.duckdb"
    run_plain_sql(synthetic_spec, warehouse)

    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        rows = con.execute(
            "select title, has_critic_reception, has_console_pricing, has_traction, "
            "metacritic_score, opencritic_score, avg_critic_score, psn_price_usd, "
            "psn_currency, peak_players "
            "from fs.market_features order by title"
        ).fetchall()
    finally:
        con.close()

    assert [r[0] for r in rows] == ["Neon Drift", "Solo Quest"]

    neon = next(r for r in rows if r[0] == "Neon Drift")
    assert neon[1:4] == (True, True, True), "matched game must show true coverage flags"
    assert all(v is not None for v in neon[4:]), "matched game must have every feature populated"

    solo = next(r for r in rows if r[0] == "Solo Quest")
    assert solo[1:4] == (False, False, False), (
        "unmatched game must show false coverage flags, not always-true"
    )
    assert all(v is None for v in solo[4:]), "unmatched game must have every feature null"
