<!-- ru-translation-of: .ai/tasks/run-dagster-dbt-profile.md sha:7e07e8aa72bd -->
<!-- Автоперевод. Источник — .ai/tasks/run-dagster-dbt-profile.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [run-dagster-dbt-profile.md](run-dagster-dbt-profile.md)

# Задача — `make run-dagster-dbt`: открыть наружу связку Prefect + dbt-под-Dagster

**Статус:** 📋 готово к работе · **Приоритет:** P1 (фаза финализации B, шаг 9) ·
**Issue:** [#44](https://github.com/dataengy/ogip/issues/44)

Связка уже существует: `experimental/pipelines/dagster/flow.py` — Prefect-флоу, который
запускает через шелл `dg launch` (dlt-ассет + dbt-подграф) внутри `experimental/orchestration/dagster_ogip`
(собственное uv-окружение), при этом за Prefect остаются ML/publish-шаги — подключено к профилю
`prefect-over-dagster` с таргетом `make run-over-dagster`. Не хватает: алиаса, названного в цели
финализации, + проверенного зелёного прогона.

## Порядок работ

1. [ ] Алиас в Makefile `run-dagster-dbt` → `run-over-dagster` (+ строка в help; таблица профилей в README).
2. [ ] `uv sync` в `experimental/orchestration/dagster_ogip` (вложенный проект, собственный venv).
3. [ ] Проверить выборки ассетов (`_DLT_ASSET`, `_DBT_SUBGRAPH`) против текущих определений dagster.
4. [ ] Зелёный E2E-прогон: exit 0 + число строк на выходе на sample-данных.
5. [ ] Перепроверить после влития PR #34 — flatten/warehouse-split может переименовать ключи ассетов.

## Приёмка

`make run-dagster-dbt` зелёный из голого checkout (после `make render-env` + uv sync),
и профиль задокументирован рядом с остальными run-профилями.
