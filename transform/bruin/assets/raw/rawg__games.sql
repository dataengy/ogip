/* @bruin
name: raw.rawg__games
type: duckdb.sql
materialization:
  type: view
owner: data-eng@ogip
tags: [raw, rawg, daily]
description: Layer-0 registration of the immutable RAWG games Parquet (1:1 AS-IS).
columns:
  - name: id
    checks: [{name: not_null}]
@bruin */
select *
from read_parquet('.run/data/raw/rawg__games/*.parquet')
