<!-- ru-translation-of: .ai/TODO.md sha:059085535750 -->
<!-- Автоперевод. Источник — .ai/TODO.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [TODO.md](TODO.md)

# OGIP — TODO

Короткие, упорядоченные, ближайшие действия. Каждое ссылается на подробный task-файл в [tasks/](tasks/)
и/или фазу в [PLAN.md](PLAN.md) · [../docs/ROADMAP.md](../docs/ROADMAP.md). Поставка —
**сначала walking skeleton** (D14): тонкий вертикальный срез end-to-end, затем тиражирование по тулсетам.
Синхронизация с GitHub Issues/Projects — `just tasks-sync`. Держите этот список коротким.

- [x] **Go / no-go** — одобрено; spec-компилятор сохранён (тонкий шим Bruin→SQLMesh в M0).
- [x] **Phase 0 — Скаффолд и идентичность** — отгружено, CI зелёный → `tasks/phase-0-scaffold.md`
- [x] **M0 — walking skeleton** (RAWG → dlt raw → SQLMesh → ML parquet → ноутбук, Prefect;
      e2e в CI) — отгружено, CI 7/7 → `tasks/m0-walking-skeleton.md` _(Evidence + Docker `make up` отложены до M1)_
- [ ] **P1 · Резильентный срез скрейпинга** — асинхронный `ScraperSource`
      ([ADR-0014](../docs/adr/ADR-0014-resilient-scraping-concurrency.md)) + Postgres landing +
      HLTB end to end → `tasks/scraping-resilient.md` _(lane `ingestion`)_
- [ ] **P1 · Финализировать R2 + VPS-деплой** — staged-вызовы s3 + lake root в spec-компиляторе +
      `integrations/prefect/deploy.py` + реальный бакет R2 + деплой на хост/smoke
      → `tasks/r2-vps-finalize.md` _(lane `core-pipeline`; зонтик над остатком
      `tasks/{s3-object-storage,vps-deploy-tooling}.md`)_
- [ ] **P2 · Бэклог источников** — кандидаты, сопоставленные с моделями игрового рынка (pricing · scope ·
      budget · traction · quality) → `tasks/sources-backlog.md`
- [x] **P2 · Демо интеграции Python-задач** — pandas/Polars ML-фича-задачи над данными RAWG/core,
      с границами датафреймов в форме адаптеров → `tasks/python-task-integration.md`
- [ ] **Семантический слой `spec/` (Bruin Semantic Layer)** — engine-agnostic семантическое
      описание в `spec/` _(средний приоритет)_ → `tasks/spec-semantic-layer.md`
- [ ] **M1–M4 — тиражировать срез** по `prefect-bruin` · `prefect-dbt` ·
      `prefect-sqlmesh-over-dbt` · `prefect-dagster-dlt-dbt`; добавить визуализатор Evidence
      _(понижено ниже P1-задач)_ → `tasks/m1-m4-toolsets.md`
- [ ] **Расширение (фазы 4–10)**: DQ, глубина star/am/fs, подключение наблюдаемости, полировка README
      → `tasks/phase-*.md`

Открытые вопросы по требованиям (скрейпинг · объёмы · serving/FS/semantic · SQL+Python):
[../docs/OPEN-QUESTIONS.md](../docs/OPEN-QUESTIONS.md).

_Детали по фазам живут в `tasks/`; это — управляющий чек-лист._
