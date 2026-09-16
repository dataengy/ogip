# `spec/sql/raw` — Layer 0

`<system>__<table>`, 1:1 AS-IS external views over landed Parquet; only
`_ingested_at`/`etl_batch_id` may be added (ADR-0001). No medallion vocabulary.
