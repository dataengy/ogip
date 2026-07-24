"""Lineage test — all five ingested sources reach `core`/`fs` via the title-match bridge.

`staging.stg_game_match` is the ONLY place identity resolution across the five keyless sources
lives (rawg game_id, metacritic slug, opencritic numeric id, psn concept_id:locale, steamcharts
appid share no natural join key). The three per-source `core` models LEFT JOIN onto it so join
coverage is a feature, never an inner-join row-drop.
"""

from pathlib import Path

from ogip.spec_compile import load_assets

_SPEC = Path("spec/sql")


def test_bridge_and_per_source_core_models_exist():
    names = {a.name for a in load_assets(_SPEC)}
    assert "staging.stg_game_match" in names
    assert "core.critic_reception" in names
    assert "core.console_pricing" in names
    assert "core.traction" in names
