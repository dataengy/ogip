<!-- ru-translation-of: .ai/tasks/dbt-packages.md sha:3b53fa06d3f7 -->
<!-- Автоперевод. Источник — .ai/tasks/dbt-packages.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [dbt-packages.md](dbt-packages.md)

# Задача — Пакеты dbt (известные пакеты dbt-hub) + джобы, которые их используют

**Статус:** 🟡 в работе — 8 core-пакетов ставятся на dbt-duckdb; `dbt deps` вшит в сборки;
добавлена джоба dbt_project_evaluator. Дополнительные/опинионированные пакеты + отдельные тулы = follow-up'ы.

## Пакеты (эмитятся компилятором `to_dbt.py` в `packages.yml` сгенерированного проекта)

SSoT — это `spec/`, поэтому dbt-проект генерируется — включая `packages.yml`. Диапазоны версий
(а не пины), чтобы dbt разрешал новейший совместимый релиз.

**Core (по умолчанию, `dbt deps` проверен зелёным на dbt-duckdb):** dbt_utils · codegen · audit_helper ·
dbt_project_evaluator · dbt_external_tables · **godatadriven/dbt_date** (calogica устарел) ·
dbt_expectations · dbt_profiler.

**Opt-in (`OGIP_DBT_EXTRA_PACKAGES=1`):** automate_dv (Data Vault — нужны модели DV-формы),
elementary (наблюдаемость — нужна собственная схема/on-run-хуки). По умолчанию выключены, чтобы
обычная сборка оставалась быстрой и без навязанных мнений.

## Обвязка

- `jobs/dg-tasks.sh`: `ensure_deps()` запускает `dbt deps` один раз (идемпотентно — пропускает,
  если `dbt_packages/` уже есть); задачи build/update его вызывают. Новая задача `dbt-evaluate`
  запускает `dbt build --select package:dbt_project_evaluator`.
- Dagster: `dbt_project_evaluator_job` + еженедельное расписание.

## Не пакеты dbt-hub (отдельные тулы — оценены, не подключены)

- **dbt-colibri** — просмотрщик lineage/доков, а не dbt-пакет; работает поверх dbt-манифеста.
  Подходит как опциональный docs-шаг, а не в `packages.yml`.
- **chio-labs/sqlbuild** — самостоятельный инструмент сборки SQL; пересекается с нашим
  spec→engine компилятором. Место ему в `docs/comparisons/` (plain-sql-vs-frameworks), а не на
  продакшен-пути.

## Follow-up'ы

- Продемонстрировать пакет в модели/тесте через `spec/` (например, проверку `dbt_expectations`) —
  требует изменения spec (SSoT), поэтому идёт через lane spec/core-pipeline.
- Для реальных прогонов elementary/automate_dv нужны настройка схемы / DV-модели.
