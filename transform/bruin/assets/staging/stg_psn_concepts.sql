/* @bruin
name: staging.stg_psn_concepts
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [staging, psn, daily]
depends:
  - raw.psn__concept
columns:
  - name: row_key
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: name
    type: varchar
    checks: [{name: not_null}]
  - name: price
    type: double
    checks: [{name: non_negative}]
@bruin */
select
    row_key
    , concept_id
    , locale
    , name
    , sku
    , category
    , try_cast(price as double) as price
    , currency
    , content_hash
    , source_url
    , cast(_ingested_at as timestamp) as ingested_at
    , etl_batch_id
from raw.psn__concept
