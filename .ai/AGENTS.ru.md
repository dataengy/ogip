<!-- ru-translation-of: .ai/AGENTS.md sha:6804e3f583d0 -->
<!-- Автоперевод. Источник — .ai/AGENTS.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [AGENTS.md](AGENTS.md)

# AGENTS.md — инструкции для AI-агентов, работающих в OGIP

**OGIP (Open Games Intelligence Platform)** — **Market Intelligence
Platform** портфолио-уровня: собирает публичные данные игрового рынка, трансформирует их
простым SQL на DuckDB и поставляет **ML-ready Parquet-датасеты** для Data Scientists,
ML-инженеров и аналитиков (**не** для BI-пользователей). Перед структурными изменениями
читайте [docs/architecture/overview.md](../docs/architecture/overview.md); решения фиксируйте
как [ADR в docs/adr/](../docs/adr/); мастер-план сборки — [.ai/PLAN.md](PLAN.md), живой
статус — в [.ai/STATUS.md](STATUS.md).

Производный от OGAP (`../Hushcrasher/`), но **намеренно проще** — путеводная звезда:
*«этот инженер может построить production-платформу данных для стартапа»*, **а не** *«следующий dbt»*.

## Общие правила (постоянные директивы владельца проекта)

1. **Имейте мнение** — выбирайте один подход и защищайте его; не предлагайте меню вариантов.
2. **Предпочитайте простоту абстракциям** — никакой новой абстракции без двух конкретных мест вызова.
3. **Держите всё на production-уровне** — типизировано, протестировано, задокументировано, наблюдаемо.
4. **Объясняйте каждое значимое архитектурное изменение** (и фиксируйте его в ADR).
5. **Сохраняйте существующее качество**; если что-то уже удовлетворяет требованию — оставьте как есть.
6. **Не вносите ломающую сложность.**
7. **После значимой работы подводите итог по каждому архитектурному улучшению.**

## Production-путь — компактный и современный (держите его в фокусе)

`Python → Prefect → Sources → [dlt direct | scrape→raw] → Raw Parquet (PyArrow, FS/R2) → DuckDB → dbt (primary) / Bruin (co-primary) → analytics → FS → ML outputs.`
Инжест по умолчанию = **dlt** (семейство `BaseSource`); **ingestr** опционален для CDC;
скрейпленные источники кладут raw Parquet напрямую (Postgres `landing` — отложенный
резильентный слой, #18). Production-движки трансформаций — **dbt (основной)** и **Bruin
(co-primary)** — оба генерируются из `spec/` и работают на DuckDB, последовательность задаёт Prefect
([ADR-0020](../docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md)). Любой другой движок
(SQLMesh, plain-SQL runner, OpenDBT, SQLMesh-over-dbt) и любой semantic/BI/feature-store-*инструмент*
(MetricFlow, Cube, Evidence, Feast, Airbyte) живёт в `experimental/` или
`docs/comparisons/`, **потребляет** `spec/` и никогда не находится на дефолтном пути `make`/пайплайна.

## Жёсткие правила

1. **Именование слоёв — закон** (ARCHITECTURE §): **raw (Layer 0)** `<system>__<table>` — 1:1 AS-IS,
   добавляются только опциональные `_ingested_at`/`etl_batch_id`; `stg_*`; core-сущности/бриджи (+ DV-суффиксы
   только для кросс-источниковой идентичности `game`); star `*_fact`/`*_dim`; **activity model**
   `am_<entity>_stream` (Activity Schema); marts с обязательным префиксом `owt_*`/`agg_*`; feature
   store `fs_<entity>_<feature_group>`. **Никакой medallion-лексики.**
2. **`spec/` — SSoT и engine-agnostic.** SQL пишется в **формате Bruin asset**
   (тело SQL + YAML `@bruin`: `depends`→lineage, `columns[].checks`→DQ, `owner`/`tags`→
   метаданные); контракты источников — в **ODCS**. Чтение `spec/` не должно требовать бинарника
   какого-либо движка. **Spec-компилятор** рендерит spec → проекты движков; основные runtime-движки —
   **dbt + Bruin** ([ADR-0020](../docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md));
   остальные — сравнительные рендеры. Специфика движков живёт только в компиляторе и
   `spec/sql/_ext/<engine>/`.
3. **SSoT-конфиг**: каждый несекретный дефолт объявляется ОДИН раз — в `config/config.yml`;
   `.env` рендерится скриптом `config/.env-render.py`. Никогда не дублируйте значение, которым владеет другая поверхность.
4. **Планка качества**: Ruff чистый, Pyright **strict** — 0 ошибок, pytest зелёный (`make check` = CI).
   Типизированный Python, Pydantic v2 на границах, httpx + tenacity, loguru. **Логирование: используйте домашний
   алиас `log`** — `from ogip.logger import log` и `log.info(...)` везде (никогда `logger.`);
   `logger` остаётся экспортированным только для совместимости с third-party.
5. **Секреты** (минимально и максимально легко): имена слотов объявляются один раз в `config/config.yml`; отрендеренный
   `.env` всегда в gitignore (шаблоны содержат только пустые слоты). Дефолт = **gitignored `.env`**
   локально/на VPS + **секреты GitHub Actions** в CI — без vault, без GPG. Bitwarden CLI и git-secret —
   opt-in (задокументированы). Никогда не коммитьте секреты открытым текстом и не зашивайте ключи в raw-данные.
6. **Сначала контракты**: изменения датасетов обновляют ODCS-контракт в `spec/contracts/<source>/`
   вместе с кодом.
7. **Портабельный SQL**: DuckDB/Postgres-first; специфичные для движков переопределения изолированы в
   `spec/sql/_ext/<engine>/`.
8. **Оркестратор ≠ трансформация** ([ADR-0021](../docs/adr/ADR-0021-orchestrator-transform-dq-boundary.md)):
   никогда не реализуйте в оркестраторе (Dagster, Prefect) то, что умеет движок трансформаций.
   **Data quality выражается один раз** — как `checks:` в `spec/`, компилируемые в тесты dbt/SQLMesh, — а
   оркестратор только *отображает* результаты (`dagster-dbt` автоматически мапит dbt-тесты → asset checks).
   Никаких рукописных `asset_check`, зеркалящих dbt-тест. Оркестраторные проверки — только для того, что
   движок действительно не может выразить (кросс-системная freshness, SLA прогонов), с зафиксированной причиной.
9. **Каждая новая директория получает `README.md`.** Архитектурные изменения получают ADR.

## Профили запуска и оркестрации

Выбираются через `config/config.yml → run_profiles` + `just run-profile <name>`:
**`prefect-dbt` (дефолт, основной)** · **`prefect-bruin` (co-primary)** ·
**`prefect-over-dagster`** (Prefect + dbt-под-Dagster; `make run-dagster-dbt`) — три
demo-гарантированные конфигурации. Экспериментальные (`experimental: true`, баннер, e2e за
`OGIP_E2E_ALL_ENGINES=1`): `prefect-sqlmesh` · `prefect-sql` · `prefect-opendbt` ·
`prefect-sqlmesh-over-dbt` · `prefect-dagster-dlt-dbt`. Хранилище: `local` (дефолт) ·
`r2` · `minio` · `s3`. Prefect runtime: `ephemeral` (дефолт) · `server`. Секреты: gitignored
`.env` (дефолт) + секреты GitHub Actions (CI); `bitwarden`/`git-secret` — opt-in. Проекты dbt/SQLMesh/Bruin
**генерируются из `spec/`** компилятором и никогда не форкаются вручную.

## Соглашения репозитория

| Где | Что |
|---|---|
| `.run/` | ВЕСЬ runtime: venv (`UV_PROJECT_ENVIRONMENT=.run/venv`), кэши, DuckDB-хранилище, выходные данные (gitignored) |
| `.tmp/` | ВСЕ временные/рабочие скрипты **и прочие временные файлы** (gitignored) + отслеживаемые `README.md` + `Justfile`; одноразовые — в `.tmp/.once/`; **выпускайте** долговечные → `integrations/`, скиллы или `src/`/common |
| `../Hushcrasher.attic/` | Внешнее кладбище удалённого легаси (никогда не удаляйте на месте) |
| `Makefile` | **лаунчер пайплайнов**: одна цель на пайплайн (`run-<engine>`, 1 op = 1 пайплайн); catch-all пробрасывает любой другой `make <op>` → `just <op>` |
| `Justfile` | **каждая** операция разработчика/инфраструктуры/spec: гейты (lint/typecheck/test/check/ci), up/down/obs/storage, run-profile, spec-compile, шаги CI, генераторы |
| `.ai/` | agentic-хаб: AGENTS/CLAUDE/README/STATUS/PLAN + `tasks/`; корневой `AGENTS.md` — симлинк сюда |
| **Git LFS** | **крупные тестовые датасеты** (записанные фикстуры, сэмплированные дампы, parquet-кейсы) — это LFS-указатели, никогда не raw-блобы — паттерны в `.gitattributes` (со скоупом по формату: бинарные форматы на путях фикстур; мелкие JSON/текстовые фикстуры остаются в обычном git, чтобы диффы читались). Один раз на клон: `make lfs-install`. Принуждается без возможности пропуска через `.ci/run.sh lfs-guard` (raw-блоб >512KB или raw-блоб с LFS-атрибутом → CI красный); локально: `just lfs-guard` |

Рабочий процесс: **пофазная поставка с гейтами одобрения пользователя** (план в [PLAN.md](PLAN.md),
ближайшие действия в [TODO.md](TODO.md), статус в [STATUS.md](STATUS.md), пофазные task-файлы в
[tasks/](tasks/)). Задачи синхронизируются с **GitHub Issues/Projects** через `just tasks-sync` (единый
трекер). Коммиты: Conventional Commits, разбиение по категориям; никаких push без спроса.
