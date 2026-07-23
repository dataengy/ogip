/* @bruin
name: raw.steamcharts__app
type: duckdb.sql
materialization:
  type: view
owner: data-eng@ogip
tags: [raw, steamcharts, daily]
description: Layer-0 registration of the immutable SteamCharts app Parquet (1:1 AS-IS).
columns:
  - name: appid
    checks: [{name: not_null}]
  - name: content_hash
    checks: [{name: not_null}]
  - name: source_url
    checks: [{name: not_null}]
@bruin */
select *
from read_parquet('.run/data/raw/steamcharts__app/*.parquet')
