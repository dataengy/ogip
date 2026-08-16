<!-- ru-translation-of: spec/sql/raw/README.md sha:febfabf14264 -->
<!-- Автоперевод. Источник — spec/sql/raw/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `spec/sql/raw` — слой 0

`<system>__<table>`, внешние представления 1:1 AS-IS над приземлённым Parquet; добавлять
можно только `_ingested_at`/`etl_batch_id` (ADR-0001). Никакого medallion-словаря.
