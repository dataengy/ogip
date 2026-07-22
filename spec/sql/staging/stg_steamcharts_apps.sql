/* @bruin
name: staging.stg_steamcharts_apps
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [staging, steamcharts, daily]
depends:
  - raw.steamcharts__app
columns:
  - name: appid
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: peak_all
    type: bigint
    checks: [{name: non_negative}]
@bruin */
select
    appid
    , name
    -- Layer-0 lands the counts AS-IS with thousands separators ("912,345"); strip and cast here.
    , try_cast(replace(current_players, ',', '') as bigint) as current_players
    , try_cast(replace(peak_24h, ',', '') as bigint) as peak_24h
    , try_cast(replace(peak_all, ',', '') as bigint) as peak_all
    , content_hash
    , source_url
    , cast(_ingested_at as timestamp) as ingested_at
    , etl_batch_id
from raw.steamcharts__app
