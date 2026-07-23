/* @bruin
name: raw.opencritic__game
type: duckdb.sql
materialization:
  type: view
owner: data-eng@ogip
tags: [raw, opencritic, daily]
description: Layer-0 registration of the immutable OpenCritic games Parquet (1:1 AS-IS).
columns:
  - name: game_id
    checks: [{name: not_null}]
  - name: content_hash
    checks: [{name: not_null}]
  - name: source_url
    checks: [{name: not_null}]
@bruin */
select *
from read_parquet('.run/data/raw/opencritic__game/*.parquet')
