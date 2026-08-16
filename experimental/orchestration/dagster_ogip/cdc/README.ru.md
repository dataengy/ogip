<!-- ru-translation-of: experimental/orchestration/dagster_ogip/cdc/README.md sha:a5e13add7f35 -->
<!-- Автоперевод. Источник — experimental/orchestration/dagster_ogip/cdc/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# CDC — Change Data Capture из Postgres landing-зоны (ingestr)

**CDC использует один пайплайн, намеренно** (D11). Инжестер по умолчанию — **dlt** для
батчевых API-источников (ADR-0006). Но Postgres-зона **landing** — куда скрейперы непрерывно
пишут распарсенные строки — именно тот источник, где CDC окупается, поэтому она использует
**ingestr**, который предоставляет CDC на логической репликации Postgres как одну команду,
управляемую флагами.

Справка: <https://getbruin.com/docs/ingestr/getting-started/cdc.html>

## Как

`ingestr_cdc.sh` захватывает INSERT/UPDATE/DELETE на `landing.*` через **slot** репликации +
**publication** и мёржит их в lake (DuckDB), так что lake — это *живое зеркало* landing, а не
периодический снапшот.

```bash
cdc/ingestr_cdc.sh --dry-run     # print the command, touch nothing (works with no DB)
cdc/ingestr_cdc.sh               # one-shot CDC catch-up (merge changes since the slot)
cdc/ingestr_cdc.sh --stream      # continuous (flush on interval / row-count trigger)
```

Конфигурация — только env-переменные `OGIP_*` (ADR-0011 — никаких секретных литералов);
печатаемая команда затирает пароль. В этом окружении скрипт прогоняется через `--dry-run`
(без Docker/Postgres); живой запуск требует landing-БД с `wal_level=logical` и созданной
publication:

```sql
ALTER SYSTEM SET wal_level = logical;   -- then restart
CREATE PUBLICATION ogip_landing_pub FOR TABLES IN SCHEMA landing;
```

## Разовая настройка на источнике (prod)

Слот репликации создаётся ingestr при первом запуске; publication и `wal_level` — шаг
DBA/провижининга (принадлежит lane VPS/DevOps, ADR-0012). Затем поставьте asset (ниже) в
расписание или запускайте `--stream` под демоном.

## Как asset Dagster

`defs/cdc_ingest/definitions.py` оборачивает скрипт в asset группы `ingestion`, так что CDC
находится в одном графе с батчевой загрузкой dlt и моделями dbt и выбирается через
`dg launch --assets 'key:"cdc_landing"'`.
