<!-- ru-translation-of: AGENTS.md sha:6804e3f583d0 -->
<!-- Автоперевод. Источник — AGENTS.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [AGENTS.md](AGENTS.md)

# AGENTS.md — инструкции для AI-агентов, работающих в OGIP

**OGIP (Open Games Intelligence Platform)** — **Market Intelligence Platform**
портфолио-уровня: собирает публичные данные игрового рынка, преобразует их обычным SQL на DuckDB
и поставляет **ML-ready Parquet-датасеты** для Data Scientists, ML-инженеров и аналитиков
(**не** для BI-пользователей). Перед структурными изменениями прочитайте
[docs/architecture/overview.md](../docs/architecture/overview.md); решения фиксируйте как
[ADR в docs/adr/](../docs/adr/); мастер-план сборки — [.ai/PLAN.md](PLAN.md), живой статус —
в [.ai/STATUS.md](STATUS.md).

Произошёл от OGAP (`../Hushcrasher/`), но **намеренно проще** — путеводная звезда:
*«этот инженер может построить production-платформу данных для стартапа»*, а **не** *«следующий dbt»*.

## Общие правила (постоянные директивы владельца проекта)

1. **Имейте собственное мнение** — выбирайте один подход и защищайте его; не предлагайте меню вариантов.
2. **Предпочитайте простоту абстракциям** — никакой новой абстракции без двух конкретных мест вызова.
3. **Держите всё на production-уровне** — типизировано, протестировано, задокументировано, наблюдаемо.
4. **Объясняйте каждое значимое архитектурное изменение** (и оформляйте его как ADR).
5. **Сохраняйте существующее качество**; если что-то уже удовлетворяет требованию — оставьте как есть.
6. **Не привносите ломающую сложность.**
7. **После значимой работы резюмируйте каждое архитектурное улучшение.**

## Production-путь компактный и современный (держите его в фокусе)

`Python → Prefect → Sources → [dlt direct | scrape→raw] → Raw Parquet (PyArrow, FS/R2) → DuckDB → dbt (primary) / Bruin (co-primary) → analytics → FS → ML outputs.`
Инжест по умолчанию = **dlt** (семейство `BaseSource`); **ingestr** опционален для CDC;
скрейпленные источники ложатся сразу в raw Parquet (Postgres `landing` — отложенный
резильентный ярус, #18). Production-движки трансформаций — **dbt (primary)** и **Bruin
(co-primary)** — оба генерируются из `spec/`, работают на DuckDB и оркеструются Prefect
([ADR-0020](../docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md)). Каждый прочий движок
(SQLMesh, plain-SQL-раннер, OpenDBT, SQLMesh-over-dbt) и каждый *инструмент* semantic/BI/feature-store
(MetricFlow, Cube, Evidence, Feast, Airbyte) живёт в `experimental/` или
`docs/comparisons/`, **потребляет** `spec/` и никогда не стоит на дефолтном пути `make`/пайплайна.

## Жёсткие правила

1. **Именование слоёв — закон** (раздел ARCHITECTURE): **raw (Layer 0)** `<system>__<table>` — 1:1 AS-IS,
   добавляются только опциональные `_ingested_at`/`etl_batch_id`; `stg_*`; core-сущности/бриджи (+ DV-суффиксы
   только для кросс-источниковой идентичности `game`); star `*_fact`/`*_dim`; **activity model**
   `am_<entity>_stream` (Activity Schema); витрины с обязательным префиксом `owt_*`/`agg_*`; feature
   store `fs_<entity>_<feature_group>`. **Никакой medallion-лексики.**
2. **`spec/` — SSoT, не зависящий от движков.** SQL пишется в **формате Bruin asset**
   (тело SQL + YAML `@bruin`: `depends`→lineage, `columns[].checks`→DQ, `owner`/`tags`→
   метаданные); контракты источников — в **ODCS**. Чтение `spec/` не должно требовать бинарника
   какого-либо движка. **Спек-компилятор** рендерит spec → проекты движков; основные runtime-движки —
   **dbt + Bruin** ([ADR-0020](../docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md));
   остальные — рендеры для сравнения. Специфика движков живёт только в компиляторе и
   `spec/sql/_ext/<engine>/`.
3. **SSoT-конфиг**: каждый несекретный дефолт объявляется ОДИН раз, в `config/config.yml`;
   `.env` рендерится `config/.env-render.py`. Никогда не дублируйте значение, которым владеет другая поверхность.
4. **Планка качества**: Ruff чистый, Pyright **strict** — 0 ошибок, pytest зелёный (`make check` = CI).
   Типизированный Python, Pydantic v2 на границах, httpx + tenacity, loguru. **Логирование: используйте домашний
   алиас `log`** — `from ogip.logger import log` и `log.info(...)` везде (никогда `logger.`);
   `logger` остаётся экспортированным только для совместимости со сторонними библиотеками.
5. **Секреты** (минимально и максимально легко): имена слотов объявляются один раз в `config/config.yml`;
   отрендеренный `.env` всегда в gitignore (шаблоны несут только пустые слоты). По умолчанию = **gitignored `.env`**
   локально/на VPS + **секреты GitHub Actions** в CI — без vault, без GPG. Bitwarden CLI и git-secret —
   опционально (задокументировано). Никогда не коммитьте секреты открытым текстом и не зашивайте ключи в raw-данные.
6. **Контракты прежде всего**: изменения датасетов обновляют ODCS-контракт в `spec/contracts/<source>/`
   вместе с кодом.
7. **Портируемый SQL**: DuckDB/Postgres-first; движко-специфичные переопределения изолированы в
   `spec/sql/_ext/<engine>/`.
8. **Оркестратор ≠ трансформация** ([ADR-0021](../docs/adr/ADR-0021-orchestrator-transform-dq-boundary.md)):
   никогда не реализуйте в оркестраторе (Dagster, Prefect) то, что умеет движок трансформаций.
   **Качество данных выражается один раз** — как `checks:` в `spec/`, компилируемые в тесты dbt/SQLMesh, — а
   оркестратор лишь *отображает* результаты (`dagster-dbt` автоматически мапит dbt-тесты → asset checks).
   Никаких рукописных `asset_check`, зеркалящих dbt-тест. Оркестратор-нативные проверки — только для того,
   что движок действительно не может выразить (кросс-системная freshness, SLA прогонов), с указанием причины.
9. **Каждая новая директория получает `README.md`.** Архитектурные изменения получают ADR.

## Профили запуска и оркестрации

Выбираются через `config/config.yml → run_profiles` + `just run-profile <name>`:
**`prefect-dbt` (по умолчанию, primary)** · **`prefect-bruin` (co-primary)** ·
**`prefect-over-dagster`** (Prefect + dbt-под-Dagster; `make run-dagster-dbt`) — три
демо-гарантированных сетапа. Экспериментальные (`experimental: true`, баннер, e2e за
`OGIP_E2E_ALL_ENGINES=1`): `prefect-sqlmesh` · `prefect-sql` · `prefect-opendbt` ·
`prefect-sqlmesh-over-dbt` · `prefect-dagster-dlt-dbt`. Хранилище: `local` (по умолчанию) ·
`r2` · `minio` · `s3`. Runtime Prefect: `ephemeral` (по умолчанию) · `server`. Секреты: gitignored
`.env` (по умолчанию) + секреты GitHub Actions (CI); `bitwarden`/`git-secret` — опционально. Проекты
dbt/SQLMesh/Bruin **генерируются из `spec/`** компилятором, никогда не форкаются вручную.

## Конвенции репозитория

| Где | Что |
|---|---|
| `.run/` | ВЕСЬ runtime: venv (`UV_PROJECT_ENVIRONMENT=.run/venv`), кэши, DuckDB-хранилище, выводы (gitignored) |
| `.tmp/` | ВСЕ временные/рабочие скрипты **и прочие временные файлы** (gitignored) + отслеживаемые `README.md` + `Justfile`; one-shot'ы в `.tmp/.once/`; долговечные **выпускайте** → в `integrations/`, навыки или `src/`/common |
| `../Hushcrasher.attic/` | Внешнее кладбище удалённого легаси (никогда не удалять на месте) |
| `Makefile` | **лаунчер пайплайнов**: один таргет на пайплайн (`run-<engine>`, 1 операция = 1 пайплайн); catch-all пробрасывает любой другой `make <op>` → `just <op>` |
| `Justfile` | **каждая** операция разработчика/инфры/спеки: гейты (lint/typecheck/test/check/ci), up/down/obs/storage, run-profile, spec-compile, CI-шаги, генераторы |
| `.ai/` | агентный хаб: AGENTS/CLAUDE/README/STATUS/PLAN + `tasks/`; корневой `AGENTS.md` — симлинк сюда |
| **Git LFS** | **большие тестовые датасеты** (записанные фикстуры, сэмплированные дампы, parquet-кейсы) — LFS-указатели, никогда не сырые блобы; паттерны в `.gitattributes` (с привязкой к формату: бинарные форматы на путях фикстур; маленькие JSON/текстовые фикстуры остаются обычным git, чтобы диффы читались). Один раз на клон: `make lfs-install`. Принуждается неотключаемо через `.ci/run.sh lfs-guard` (сырой блоб >512KB или сырой блоб под LFS-атрибутом → CI красный); локально: `just lfs-guard` |

Рабочий процесс: **поэтапная поставка с гейтами одобрения пользователя** (план в [PLAN.md](PLAN.md),
ближайшие действия в [TODO.md](TODO.md), статус в [STATUS.md](STATUS.md), пофазовые файлы задач в
[tasks/](tasks/)). Задачи синхронизируются в **GitHub Issues/Projects** через `just tasks-sync` (единый
трекер). Коммиты: Conventional Commits, с разбивкой по категориям; никакого push без спроса.
