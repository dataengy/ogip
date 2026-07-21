/* @bruin
name: raw.metacritic__game
type: duckdb.sql
materialization:
  type: view
owner: data-eng@ogip
tags: [raw, metacritic, daily]
description: Layer-0 registration of the immutable Metacritic games Parquet (1:1 AS-IS).
@bruin */
select *
from read_parquet('.run/data/raw/metacritic__game/*.parquet')
