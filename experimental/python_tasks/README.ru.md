<!-- ru-translation-of: experimental/python_tasks/README.md sha:a30d5ff6c0bf -->
<!-- Автоперевод. Источник — experimental/python_tasks/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# Python transform-задачи

Это изолированное демо dataframe-задач, которые могут стоять между SQL-моделями в
ML-ориентированном пайплайне. Оно использует существующую форму `core.game` / `fs.market_features`:

```text
core.game -> pandas feature task -> polars training-set task -> ML-ready parquet
```

Функции намеренно чистые: будущий адаптер SQL-transform-инструмента сможет подать входное
отношение и сохранить возвращённый dataframe, не меняя логику фичей. В путь SQLMesh по
умолчанию они не входят.

```python
from experimental.python_tasks.tasks import build_pandas_features

features = build_pandas_features(core_game_dataframe)
```

Примеры покрывают типовые шаги подготовки данных для ML: робастную импутацию числовых
значений, логарифмическое масштабирование, кросс-секционные перцентильные фичи, защищённый от
утечки (leakage-safe) label и Polars-агрегацию для обучающих фичей уровня жанра. В продакшене
держите вычисление label'ов и фичей отдельными задачами, чтобы point-in-time-правила можно
было аудировать.

## Набор фиче-инжиниринга (`tasks.py`)

Небольшой, но репрезентативный ML-пайплайн фичей; каждая функция чистая и детерминированная:

| Функция | Шаг |
|---|---|
| `build_pandas_features` | импутация числовых значений + сигналы log/critic/перцентили + label популярности |
| `standardize_features` | z-score (`_z`); константа → 0 |
| `minmax_scale_features` | min-max в `[0,1]` (`_mm`) |
| `clip_outliers` | симметричная квантильная винзоризация |
| `add_interaction_features` | попарные произведения (`<a>_x_<b>`) |
| `bucketize_feature` | ординальные полосы по ранговым квантилям |
| `one_hot_encode` | категориальные индикаторы (+ ограничение `top_n`) |
| `add_release_cohort_features` | ранг внутри года релиза + среднее по когорте |
| `train_test_split_frame` | детерминированный сплит по hash-бакетам (без утечки, возобновляемый) |
| `assemble_feature_matrix` | финальная числовая матрица X/y без NA |
| `build_polars_genre_features` | Polars-агрегация по жанрам (опциональная зависимость) |

## Граница пайплайна (`pipeline.py`)

`build_ml_features(warehouse, outputs_dir) -> dict[str, int]` читает `core.game` из
DuckDB-хранилища, выполняет задачи выше и пишет `ml_features.parquet` + `ml_train.parquet` +
`ml_test.parquet`. Возвращает только счётчики строк — **dataframe'ы никогда не пересекают эту
границу**, поэтому pyright-strict-код в `pipelines/` интегрирует демо, не импортируя pandas.
Каждый SQL-tool-пайплайн (SQLMesh, dbt, OpenDBT, SQLMesh-over-dbt, Bruin, plain-SQL) вызывает
её после своего transform.
