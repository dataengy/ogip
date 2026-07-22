/* @bruin
name: core.traction
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [core, feature, daily]
depends:
  - staging.stg_game_match
  - staging.stg_steamcharts_apps
columns:
  - name: game_sk
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: current_players
    type: bigint
    checks: [{name: non_negative}]
  - name: peak_24h
    type: bigint
    checks: [{name: non_negative}]
  - name: peak_all
    type: bigint
    checks: [{name: non_negative}]
@bruin */
select
    b.game_sk
    , cast(sc.current_players as bigint) as current_players
    , cast(sc.peak_24h as bigint) as peak_24h
    , cast(sc.peak_all as bigint) as peak_all
from staging.stg_game_match as b
left join staging.stg_steamcharts_apps as sc
    on regexp_replace(lower(sc.name), '[^a-z0-9]', '', 'g') = b.match_key
