"""Regression test — a game priced in more than one PSN storefront must not fan out (or mix
currencies) in `fs.market_features`.

`core.console_pricing`'s declared grain is `(game_sk, locale)` — a game can legitimately have
one row per regional storefront. `fs.market_features` is documented as one row per `game_sk`;
joining straight onto `core.console_pricing` would multiply rows for any game priced in more
than one locale, and averaging/mixing prices across locales would blend currencies into a
meaningless number. `spec/sql/fs/market_features.sql`'s `pricing_by_game` CTE restricts to the
`en-us` storefront before joining, so the feature stays single-row and single-currency
(`psn_price_usd` / `psn_currency`). This test seeds a synthetic PSN staging table with the SAME
game priced in TWO locales and runs the real committed model bodies (`spec/sql/**`, copied
verbatim — not reimplemented) through the plain-SQL runner already used by
`src/tests/unit/test_spec_compile.py`.
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
# ("Vertex Racer") priced in TWO PSN locales; the other three sources get an unrelated title so
# `core.critic_reception` / `core.traction` still build without matching this game (out of
# scope for this test).
_STG_GAMES = """/* @bruin
name: staging.stg_games
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    (1, 'Vertex Racer', 'vertex-racer', date '2021-09-10', 4.0, 300, 75, 20, 1000)
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
    ('Unrelated Game', 70)
) as t(name, metascore)
"""

_STG_OPENCRITIC = """/* @bruin
name: staging.stg_opencritic_games
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    ('Unrelated Game', 72)
) as t(name, score)
"""

# The regression fixture: the SAME title priced in two locales, one of them `en-us`.
_STG_PSN = """/* @bruin
name: staging.stg_psn_concepts
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    ('Vertex Racer', 'en-us', cast(39.99 as double), 'USD')
    , ('Vertex Racer', 'en-gb', cast(34.99 as double), 'GBP')
) as t(name, locale, price, currency)
"""

_STG_STEAMCHARTS = """/* @bruin
name: staging.stg_steamcharts_apps
type: duckdb.sql
materialization:
  type: table
@bruin */
select * from (values
    ('Unrelated Game', 100, 150, 2000)
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


def test_multi_locale_psn_pricing_does_not_fan_out_market_features(
    synthetic_spec: Path, tmp_path: Path
) -> None:
    warehouse = tmp_path / "wh.duckdb"
    run_plain_sql(synthetic_spec, warehouse)

    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        # Sanity: the fixture really does carry 2 locale rows for this game in `core` — proves
        # the fan-out risk is real, not accidentally absent from the test data.
        pricing_rows = con.execute(
            "select count(*) from core.console_pricing where game_sk = md5('1')"
        ).fetchone()
        assert pricing_rows == (2,)

        total = con.execute("select count(*) from fs.market_features").fetchone()
        assert total == (1,), "one rawg game must yield exactly one fs.market_features row"

        rows = con.execute(
            "select psn_price_usd, psn_currency from fs.market_features where game_sk = md5('1')"
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 1, "PSN locale fan-out must not multiply the game_sk row"
    assert rows[0] == (39.99, "USD"), "must reflect the en-us row, not the cheaper en-gb one"
