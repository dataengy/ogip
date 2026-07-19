# Python transform tasks

This is an isolated demo of dataframe tasks that can sit between SQL models in an
ML-oriented pipeline. It uses the existing `core.game` / `fs.market_features` shape:

```text
core.game -> pandas feature task -> polars training-set task -> ML-ready parquet
```

The functions are deliberately pure: a future SQL-transform-tool adapter can provide
the input relation and persist the returned dataframe without changing the feature
logic. They are not part of the default SQLMesh path.

```python
from experimental.python_tasks.tasks import build_pandas_features

features = build_pandas_features(core_game_dataframe)
```

The examples cover common ML preparation steps: robust numeric imputation, log scaling,
cross-sectional percentile features, a leakage-safe label, and a Polars aggregation
for genre-level training features. Keep labels and feature computation as separate
tasks in production so point-in-time rules can be audited.

## Feature-engineering set (`tasks.py`)

A small but representative ML feature pipeline, every function pure and deterministic:

| Function | Step |
|---|---|
| `build_pandas_features` | numeric imputation + log/critic/percentile signals + popularity label |
| `standardize_features` | z-score (`_z`); constant → 0 |
| `minmax_scale_features` | min-max to `[0,1]` (`_mm`) |
| `clip_outliers` | symmetric-quantile winsorizing |
| `add_interaction_features` | pairwise products (`<a>_x_<b>`) |
| `bucketize_feature` | rank-quantile ordinal bands |
| `one_hot_encode` | categorical indicators (+ `top_n` capping) |
| `add_release_cohort_features` | within-release-year rank + cohort mean |
| `train_test_split_frame` | deterministic hash-bucket split (leakage-safe, resumable) |
| `assemble_feature_matrix` | final numeric, NA-free X/y matrix |
| `build_polars_genre_features` | Polars genre aggregation (optional dependency) |

## Pipeline boundary (`pipeline.py`)

`build_ml_features(warehouse, outputs_dir) -> dict[str, int]` reads `core.game` from the DuckDB
warehouse, runs the tasks above, and writes `ml_features.parquet` + `ml_train.parquet` +
`ml_test.parquet`. It returns only row counts — **dataframes never cross this boundary**, so the
pyright-strict code in `pipelines/` integrates the demo without importing pandas. Every SQL-tool
pipeline (SQLMesh, dbt, OpenDBT, SQLMesh-over-dbt, Bruin, plain-SQL) calls it after its transform.
