"""Typed boundary between the SQL warehouse and the pandas/Polars feature tasks.

Every SQL-tool pipeline (SQLMesh, dbt, OpenDBT, SQLMesh-over-dbt, Bruin, plain-SQL) builds the
same `core.game` relation. This module reads it out of DuckDB, runs the pure feature tasks
(`tasks.py`), and writes an ML-ready training matrix to Parquet — returning only a
`dict[str, int]` of row counts. Dataframes never cross this boundary, so the pyright-strict
production code in `pipelines/` calls `build_ml_features` without ever importing pandas.

Off the default SQLMesh path by design; a pipeline opts in by calling this after its transform.
"""

from __future__ import annotations

from pathlib import Path

from .tasks import (
    add_interaction_features,
    add_release_cohort_features,
    assemble_feature_matrix,
    bucketize_feature,
    build_pandas_features,
    minmax_scale_features,
    standardize_features,
    train_test_split_frame,
)

# The model matrix the demo assembles — a stable contract for the ML-ready output.
_FEATURE_COLUMNS = [
    "rating_z",
    "ratings_count_z",
    "critic_score",
    "added_percentile",
    "added_count_bucket",
    "rating_x_metacritic",
    "cohort_rating_mean",
    "cohort_rating_rank",
]
_LABEL = "popular_label"
_SOURCE_RELATION = "core.game"


def build_ml_features(
    warehouse: Path, outputs_dir: Path, *, relation: str = _SOURCE_RELATION
) -> dict[str, int]:
    """Read ``relation`` from DuckDB, engineer features, write train/test Parquet.

    Returns row counts keyed by output file — the only type that crosses back to the typed
    caller. Writes ``ml_features.parquet`` (full matrix), ``ml_train.parquet``, and
    ``ml_test.parquet`` under ``outputs_dir``.
    """
    import duckdb

    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        games = con.execute(f"select * from {relation}").df()
    finally:
        con.close()

    features = build_pandas_features(games)
    features = standardize_features(features, ["rating", "ratings_count"])
    features = minmax_scale_features(features, ["metacritic"])
    features = add_interaction_features(features, [("rating", "metacritic")])
    features = bucketize_feature(features, "added_count", bins=4)
    features = add_release_cohort_features(features)

    # Split on the full frame (which still carries `game_sk`), THEN assemble each side into a
    # clean X/y matrix — assembling first would drop the id the deterministic split hashes on.
    matrix = assemble_feature_matrix(features, _FEATURE_COLUMNS, _LABEL)
    train_features, test_features = train_test_split_frame(features, test_frac=0.2)
    train = assemble_feature_matrix(train_features, _FEATURE_COLUMNS, _LABEL)
    test = assemble_feature_matrix(test_features, _FEATURE_COLUMNS, _LABEL)

    outputs_dir.mkdir(parents=True, exist_ok=True)
    written = {
        "ml_features.parquet": matrix,
        "ml_train.parquet": train,
        "ml_test.parquet": test,
    }
    counts: dict[str, int] = {}
    for name, frame in written.items():
        frame.to_parquet(outputs_dir / name, index=False)
        counts[name] = len(frame)
    return counts
