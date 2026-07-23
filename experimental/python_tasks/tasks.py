"""Pure pandas/Polars tasks over OGIP's existing game feature relations.

These functions intentionally use dataframe-in/dataframe-out boundaries, which map
cleanly to most Python-task APIs and keep orchestration concerns out of the demo.

The set spans a small ML feature-engineering pipeline: numeric imputation + signals
(``build_pandas_features``), scaling (``standardize_features`` / ``minmax_scale_features``),
categorical + cohort encodings (``one_hot_encode`` / ``add_release_cohort_features``),
interactions and bucketing (``add_interaction_features`` / ``bucketize_feature``), outlier
winsorizing (``clip_outliers``), a leakage-safe deterministic split
(``train_test_split_frame``), and a final matrix assembler (``assemble_feature_matrix``).
Every function is pure and deterministic — no RNG, no I/O, no orchestration — so a
SQL-transform-tool adapter can feed the input relation and persist the output unchanged.

This module lives under ``experimental/`` and is intentionally OUTSIDE pyright's strict
include set: pandas has no first-party stubs and strict mode floods on its dynamic API.
Callers on the checked path reach it only through ``pipeline.build_ml_features``, which
returns plain ``dict[str, int]`` — dataframes never cross into typed production code.
"""

from __future__ import annotations

import hashlib
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl


def build_pandas_features(games: pd.DataFrame) -> pd.DataFrame:
    """Build deterministic game features and a next-period popularity label.

    The label is based on the supplied snapshot's ``added_count``. In a real daily
    pipeline this task should receive a future snapshot for the label, never the
    current row, to prevent training/serving leakage.
    """
    import pandas as pd

    required = {"game_sk", "rating", "ratings_count", "metacritic", "added_count"}
    missing = required.difference(games.columns)
    if missing:
        raise ValueError(f"core.game is missing columns: {sorted(missing)}")

    result = games.copy()
    for column in ("rating", "ratings_count", "metacritic", "added_count"):
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)
    result["rating_log_count"] = result["rating"] * (result["ratings_count"] + 1).map(math.log1p)
    result["critic_score"] = (result["metacritic"] / 100.0).clip(0.0, 1.0)
    result["added_percentile"] = result["added_count"].rank(pct=True, method="average")
    result["popular_label"] = (result["added_percentile"] >= 0.75).astype("int8")
    return result


def standardize_features(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Z-score standardize ``columns`` in place-safe copy: ``(x - mean) / std``.

    A zero-variance column (constant) maps to all-zeros rather than dividing by zero — the
    signal it carries is nil, so a constant is the honest standardized value. New columns are
    suffixed ``_z`` so the raw feature survives for auditing.
    """
    result = features.copy()
    for column in columns:
        series = result[column].astype("float64")
        std = float(series.std(ddof=0))
        result[f"{column}_z"] = 0.0 if std == 0.0 else (series - float(series.mean())) / std
    return result


def minmax_scale_features(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Min-max scale ``columns`` to ``[0, 1]`` (``_mm`` suffix); constant columns → 0.0."""
    result = features.copy()
    for column in columns:
        series = result[column].astype("float64")
        low, high = float(series.min()), float(series.max())
        span = high - low
        result[f"{column}_mm"] = 0.0 if span == 0.0 else (series - low) / span
    return result


def clip_outliers(
    features: pd.DataFrame, columns: list[str], quantile: float = 0.99
) -> pd.DataFrame:
    """Winsorize ``columns`` to the symmetric ``[1-q, q]`` quantile band (robust to tails)."""
    if not 0.5 < quantile < 1.0:
        raise ValueError(f"quantile must be in (0.5, 1.0), got {quantile}")
    result = features.copy()
    for column in columns:
        series = result[column].astype("float64")
        lower, upper = series.quantile(1.0 - quantile), series.quantile(quantile)
        result[column] = series.clip(lower=lower, upper=upper)
    return result


def add_interaction_features(features: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """Add pairwise product interaction terms (``<a>_x_<b>``) — cheap non-linear signal."""
    result = features.copy()
    for left, right in pairs:
        result[f"{left}_x_{right}"] = result[left].astype("float64") * result[right].astype(
            "float64"
        )
    return result


def bucketize_feature(features: pd.DataFrame, column: str, bins: int = 4) -> pd.DataFrame:
    """Quantile-bucket ``column`` into ``bins`` ordinal bands (``<column>_bucket``).

    Uses rank-based quantiles so ties and skew never collapse the edges; the output is a
    0-based integer band, model-ready as an ordinal or a categorical.
    """
    if bins < 2:
        raise ValueError(f"bins must be >= 2, got {bins}")
    result = features.copy()
    ranks = result[column].rank(pct=True, method="average")
    edges = [i / bins for i in range(1, bins)]
    band = ranks.map(lambda p: sum(1 for e in edges if p > e))
    result[f"{column}_bucket"] = band.astype("int16")
    return result


def one_hot_encode(features: pd.DataFrame, column: str, *, top_n: int = 0) -> pd.DataFrame:
    """One-hot encode a categorical ``column`` (``<column>=<value>`` int8 indicator columns).

    ``top_n > 0`` keeps only the most frequent ``top_n`` categories (long-tail folded into an
    implicit all-zero rest), bounding feature-matrix width on high-cardinality columns.
    """
    import pandas as pd

    result = features.copy()
    values = result[column].astype("string").fillna("__na__")
    if top_n > 0:
        keep = set(values.value_counts().head(top_n).index)
        values = values.where(values.isin(keep), other="__other__")
    dummies = pd.get_dummies(values, prefix=column, prefix_sep="=", dtype="int8")
    return pd.concat([result, dummies], axis=1)


def add_release_cohort_features(features: pd.DataFrame) -> pd.DataFrame:
    """Add release-year cohort features: within-cohort rating rank + cohort mean rating.

    Cross-sectional cohort signals — how a game ranks against its release-year peers — without
    any time-series leakage, since the cohort is a static attribute of the row.
    """
    result = features.copy()
    if "release_year" not in result.columns:
        raise ValueError("core.game is missing column: 'release_year'")
    rating = result["rating"].astype("float64")
    grouped = rating.groupby(result["release_year"])
    result["cohort_rating_mean"] = grouped.transform("mean")
    result["cohort_rating_rank"] = grouped.rank(pct=True, method="average")
    return result


def train_test_split_frame(
    features: pd.DataFrame, *, key: str = "game_sk", test_frac: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic, hash-based train/test split — reproducible without an RNG seed.

    Bucketing on ``md5(key)`` means the same row always lands in the same split across runs
    and machines (unlike ``sample``), and a new snapshot's existing rows keep their assignment
    — the property a leakage-safe, resumable ML pipeline needs.
    """
    if not 0.0 < test_frac < 1.0:
        raise ValueError(f"test_frac must be in (0, 1), got {test_frac}")
    threshold = int(test_frac * 10_000)

    def _in_test(value: object) -> bool:
        # md5 is a split-bucket hash here, not a security primitive.
        digest = hashlib.md5(str(value).encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 10_000 < threshold

    mask = features[key].map(_in_test)
    return features[~mask].copy(), features[mask].copy()


def assemble_feature_matrix(
    features: pd.DataFrame, feature_columns: list[str], label: str
) -> pd.DataFrame:
    """Select the model matrix: ``feature_columns`` + ``label``, numeric, NA-free, ordered.

    The final boundary before training — asserts every requested feature exists, coerces to
    numeric, and drops rows with a missing label (an unlabelled row is not a training example).
    """
    missing = {*feature_columns, label}.difference(features.columns)
    if missing:
        raise ValueError(f"feature matrix is missing columns: {sorted(missing)}")
    import pandas as pd

    matrix = features[[*feature_columns, label]].copy()
    for column in feature_columns:
        matrix[column] = pd.to_numeric(matrix[column], errors="coerce").fillna(0.0)
    return matrix.dropna(subset=[label]).reset_index(drop=True)


def build_polars_genre_features(games: pl.DataFrame) -> pl.DataFrame:
    """Aggregate raw nested RAWG genres into a Polars ML feature table.

    Polars is imported only under ``TYPE_CHECKING`` for the annotation and lazily at call
    time, so it stays an optional demo dependency. The SQL-transform-tool adapter can pass
    its native Polars dataframe directly.
    """
    import polars as pl

    if not isinstance(games, pl.DataFrame):
        raise TypeError("build_polars_genre_features expects a polars.DataFrame")
    required = {"game_id", "genres"}
    missing = required.difference(games.columns)
    if missing:
        raise ValueError(f"rawg__games is missing columns: {sorted(missing)}")
    return (
        games.select("game_id", "genres")
        .explode("genres")
        .unnest("genres")
        .group_by(["id", "name"])
        .agg(pl.len().alias("game_count"))
        .rename({"id": "genre_id", "name": "genre_name"})
        .sort("genre_id")
    )
