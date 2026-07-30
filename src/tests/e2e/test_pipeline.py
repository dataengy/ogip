"""E2E — run the Prefect job end-to-end and assert the ML-ready outputs (D17).

No Docker needed: the flow runs ephemerally, ingesting the synthetic RAWG fixture (demo mode).
"""

from __future__ import annotations

import duckdb
import pytest

from ogip.config import get_settings

pytestmark = pytest.mark.e2e


def test_prefect_pipeline_produces_ml_outputs() -> None:
    from pipelines.flows.main import ingest_transform_publish

    counts = ingest_transform_publish()
    assert counts["games.parquet"] > 0
    assert counts["market_features.parquet"] > 0

    outdir = get_settings().platform.outputs_dir
    games = outdir / "games.parquet"
    features = outdir / "market_features.parquet"
    assert games.exists() and features.exists()

    game_cols = set(duckdb.sql(f"select * from read_parquet('{games}') limit 0").columns)
    assert {"game_sk", "title", "rating", "metacritic"} <= game_cols

    rows = duckdb.sql(
        f"select popularity_score from read_parquet('{features}') where popularity_score is null"
    ).fetchall()
    assert rows == []  # feature never null (non_negative check contract)

    # The ML feature step is wired INTO the flow (via @materialize), not just callable standalone.
    assert any(k.startswith("ml::") for k in counts), "ML step did not run in the flow"
    assert (outdir / "ml_features.parquet").exists()
