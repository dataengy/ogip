"""Part 2b: `spec/sql` must carry a comprehensive DQ check set (ODTS §5-6).

Part 2a taught the compiler to project `@bruin` `checks:` into SQLMesh audits; this pins that
the SSoT actually USES that vocabulary broadly across raw/staging/core/fs, not just the
handful of models Part 1 happened to annotate. A low total means checks were dropped/forgotten
somewhere in the enrichment pass, not that the compiler regressed (Part 2a already covers the
compiler itself in `test_to_sqlmesh_audits.py`).
"""

from __future__ import annotations

import re
from pathlib import Path

from ogip.spec_compile import compile_to_sqlmesh

REPO = Path(__file__).resolve().parents[3]
SPEC_SQL = REPO / "spec" / "sql"

_AUDIT_CALL = re.compile(r"^\s{4}[a-z_]+\(", re.M)


def _compiled_text(tmp_path: Path) -> str:
    models_dir = tmp_path / "models"
    compile_to_sqlmesh(SPEC_SQL, models_dir)
    return "\n".join(f.read_text() for f in sorted(models_dir.rglob("*.sql")))


def test_sqlmesh_compiler_emits_at_least_twenty_audits(tmp_path: Path) -> None:
    text = _compiled_text(tmp_path)
    assert len(_AUDIT_CALL.findall(text)) >= 20


def test_raw_layer_asserts_not_null_on_natural_keys_and_scraper_provenance(
    tmp_path: Path,
) -> None:
    models_dir = tmp_path / "models"
    compile_to_sqlmesh(SPEC_SQL, models_dir)
    # rawg's raw natural key is `id` (the RAWG API field), not `game_id` — that alias is only
    # introduced by staging.stg_games.
    rawg = (models_dir / "raw" / "rawg__games.sql").read_text()
    assert "not_null(columns := (id))" in rawg
    assert "unique_values" not in rawg  # raw is 1:1 AS-IS — uniqueness is a staging concern

    opencritic = (models_dir / "raw" / "opencritic__game.sql").read_text()
    assert "not_null(columns := (game_id))" in opencritic
    assert "not_null(columns := (content_hash))" in opencritic
    assert "not_null(columns := (source_url))" in opencritic

    steamcharts = (models_dir / "raw" / "steamcharts__app.sql").read_text()
    assert "not_null(columns := (appid))" in steamcharts
    assert "not_null(columns := (content_hash))" in steamcharts

    psn = (models_dir / "raw" / "psn__concept.sql").read_text()
    assert "not_null(columns := (row_key))" in psn
    assert "not_null(columns := (source_url))" in psn

    metacritic = (models_dir / "raw" / "metacritic__game.sql").read_text()
    assert "not_null(columns := (slug))" in metacritic
    assert "not_null(columns := (content_hash))" in metacritic


def test_staging_layer_scores_are_bounded_and_counts_are_non_negative(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    compile_to_sqlmesh(SPEC_SQL, models_dir)

    stg_metacritic = (models_dir / "staging" / "stg_metacritic_games.sql").read_text()
    assert "accepted_range(column := metascore, min_v := 0, max_v := 100)" in stg_metacritic
    assert "accepted_range(column := review_count, min_v := 0)" in stg_metacritic

    stg_opencritic = (models_dir / "staging" / "stg_opencritic_games.sql").read_text()
    assert "accepted_range(column := score, min_v := 0, max_v := 100)" in stg_opencritic

    stg_steamcharts = (models_dir / "staging" / "stg_steamcharts_apps.sql").read_text()
    assert "accepted_range(column := current_players, min_v := 0)" in stg_steamcharts
    assert "accepted_range(column := peak_24h, min_v := 0)" in stg_steamcharts
    assert "accepted_range(column := peak_all, min_v := 0)" in stg_steamcharts


def test_fs_market_features_bounds_critic_score_unit_interval(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    compile_to_sqlmesh(SPEC_SQL, models_dir)
    fs = (models_dir / "fs" / "market_features.sql").read_text()
    assert "accepted_range(column := critic_score, min_v := 0, max_v := 1)" in fs
