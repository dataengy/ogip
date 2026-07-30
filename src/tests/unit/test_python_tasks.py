"""Tests for the isolated dataframe-task integration demo."""
# Polars is an OPTIONAL demo dependency without strict-clean stubs, so its dataframe API
# reads as partially-unknown under pyright strict. Relax only the unknown-type family for
# this one test file; pandas (with pandas-stubs) and everything else stay fully checked.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import pandas as pd
import pytest
from experimental.python_tasks.tasks import (
    add_interaction_features,
    add_release_cohort_features,
    assemble_feature_matrix,
    bucketize_feature,
    build_pandas_features,
    build_polars_genre_features,
    clip_outliers,
    minmax_scale_features,
    one_hot_encode,
    standardize_features,
    train_test_split_frame,
)


@pytest.fixture
def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_sk": ["a", "b", "c", "d", "e", "f", "g", "h"],
            "rating": [4.0, 3.0, 5.0, 2.0, 4.5, 3.5, 1.0, 5.0],
            "ratings_count": [10, 20, 30, 5, 40, 15, 2, 50],
            "metacritic": [80, 60, 100, 40, 90, 70, 20, 95],
            "added_count": [1, 2, 3, 4, 5, 6, 7, 8],
            "release_year": [2019, 2019, 2020, 2020, 2021, 2021, 2021, 2020],
            "platform": ["pc", "ps", "pc", "xbox", "pc", "ps", "pc", "xbox"],
        }
    )


def test_pandas_features_are_ml_ready() -> None:
    result = build_pandas_features(
        pd.DataFrame(
            {
                "game_sk": ["a", "b", "c", "d"],
                "rating": [4.0, None, 3.0, 5.0],
                "ratings_count": [10, 0, 20, 30],
                "metacritic": [80, None, 60, 100],
                "added_count": [1, 2, 3, 4],
            }
        )
    )
    assert result["rating_log_count"].notna().all()
    assert result["critic_score"].between(0, 1).all()
    assert result["popular_label"].sum() == 2


def test_pandas_task_reports_contract_drift() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        build_pandas_features(pd.DataFrame({"game_sk": ["a"]}))


def test_standardize_is_zero_mean_unit_variance(sample: pd.DataFrame) -> None:
    result = standardize_features(sample, ["rating", "ratings_count"])
    assert abs(float(result["rating_z"].mean())) < 1e-9
    assert abs(float(result["rating_z"].std(ddof=0)) - 1.0) < 1e-9


def test_standardize_constant_column_is_all_zero() -> None:
    df = pd.DataFrame({"x": [5.0, 5.0, 5.0]})
    assert (standardize_features(df, ["x"])["x_z"] == 0.0).all()


def test_minmax_scales_into_unit_range(sample: pd.DataFrame) -> None:
    result = minmax_scale_features(sample, ["metacritic"])
    assert float(result["metacritic_mm"].min()) == 0.0
    assert float(result["metacritic_mm"].max()) == 1.0


def test_clip_outliers_winsorizes_tails() -> None:
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 1000.0]})
    result = clip_outliers(df, ["x"], quantile=0.9)
    assert float(result["x"].max()) < 1000.0


def test_interaction_features_are_products(sample: pd.DataFrame) -> None:
    result = add_interaction_features(sample, [("rating", "metacritic")])
    assert result["rating_x_metacritic"].iloc[0] == 4.0 * 80


def test_bucketize_produces_ordinal_bands(sample: pd.DataFrame) -> None:
    result = bucketize_feature(sample, "added_count", bins=4)
    assert set(result["added_count_bucket"].unique()) <= {0, 1, 2, 3}
    assert result["added_count_bucket"].min() == 0


def test_one_hot_encode_and_top_n(sample: pd.DataFrame) -> None:
    result = one_hot_encode(sample, "platform")
    assert "platform=pc" in result.columns
    assert int(result["platform=pc"].sum()) == 4
    capped = one_hot_encode(sample, "platform", top_n=1)
    assert "platform=pc" in capped.columns  # most frequent kept
    assert "platform=__other__" in capped.columns  # tail folded


def test_release_cohort_features(sample: pd.DataFrame) -> None:
    result = add_release_cohort_features(sample)
    # 2019 cohort mean = (4.0 + 3.0) / 2 = 3.5
    assert result["cohort_rating_mean"].iloc[0] == 3.5
    assert result["cohort_rating_rank"].between(0, 1).all()


def test_train_test_split_is_deterministic(sample: pd.DataFrame) -> None:
    train_a, test_a = train_test_split_frame(sample, test_frac=0.25)
    _train_b, test_b = train_test_split_frame(sample, test_frac=0.25)
    assert list(test_a["game_sk"]) == list(test_b["game_sk"])  # same across runs
    assert len(train_a) + len(test_a) == len(sample)  # partition, no overlap/loss
    assert set(train_a["game_sk"]).isdisjoint(set(test_a["game_sk"]))


def test_assemble_feature_matrix_selects_and_cleans(sample: pd.DataFrame) -> None:
    features = build_pandas_features(sample)
    matrix = assemble_feature_matrix(
        features, ["rating_log_count", "critic_score", "added_percentile"], "popular_label"
    )
    assert list(matrix.columns) == [
        "rating_log_count",
        "critic_score",
        "added_percentile",
        "popular_label",
    ]
    assert matrix.notna().all().all()


def test_assemble_feature_matrix_reports_missing() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        assemble_feature_matrix(pd.DataFrame({"a": [1]}), ["a"], "nope")


def test_polars_genre_task() -> None:
    pl = pytest.importorskip("polars")
    result = build_polars_genre_features(
        pl.DataFrame(
            {
                "game_id": [1, 2],
                "genres": [
                    [{"id": 4, "name": "Action"}],
                    [{"id": 4, "name": "Action"}, {"id": 5, "name": "RPG"}],
                ],
            }
        )
    )
    assert result.to_dict(as_series=False) == {
        "genre_id": [4, 5],
        "genre_name": ["Action", "RPG"],
        "game_count": [2, 1],
    }
