/* @bruin
name: raw.psn__concept
type: duckdb.sql
materialization:
  type: view
owner: data-eng@ogip
tags: [raw, psn, daily]
description: Layer-0 registration of the immutable PSN concept Parquet (1:1 AS-IS).
columns:
  - name: row_key
    checks: [{name: not_null}]
  - name: content_hash
    checks: [{name: not_null}]
  - name: source_url
    checks: [{name: not_null}]
@bruin */
select *
from read_parquet('.run/data/raw/psn__concept/*.parquet')
