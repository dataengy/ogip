<!-- ru-translation-of: docs/architecture/README.md sha:6f41039953a4 -->
<!-- Автоперевод. Источник — docs/architecture/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# Архитектура

Документы по архитектуре OGIP. Начните с [`overview.md`](overview.md); точечные во времени
решения живут как [ADR](../adr/); полный план создания — [`.ai/PLAN.md`](../../.ai/PLAN.md).

| Doc | What | Status |
|---|---|---|
| [overview.md](overview.md) | Системный контекст, конвейер, стек слоёв, карта компонентов | draft |
| data-flow.md | Сквозной поток данных (source → landing → raw → warehouse → outputs) | _Phase 1_ |
| ingestion.md | Семейство `BaseSource`, dlt/ingestr, Postgres landing, водяные знаки | _Phase 2_ |
| transformation.md | Компилятор Spec → SQLMesh, сборки слоёв, переносимость | _Phase 3_ |
| storage.md | Parquet/PyArrow, FS/R2/MinIO/S3, хранилище DuckDB | _Phase 3_ |
| data-quality.md | Контракты (ODCS), утверждения, свежесть, RI, серьёзность | _Phase 4_ |
| [observability.md](observability.md) | Логирование, метрики (VictoriaMetrics), Loki, Grafana, алерты | draft |

Пока подраздел не существует, его тема покрывается соответствующим разделом
[`.ai/PLAN.md`](../../.ai/PLAN.md) Part A.
