/* @bruin
name: staging.stg_game_match
type: duckdb.sql
materialization:
  type: view
owner: data-eng@ogip
tags: [staging, bridge, daily]
depends:
  - staging.stg_games
columns:
  - name: game_sk
    type: varchar
    checks: [{name: not_null}]
  - name: match_key
    type: varchar
    checks: [{name: not_null}]
@bruin */
with spine as (
    select
        md5(cast(game_id as varchar)) as game_sk
        , regexp_replace(lower(name), '[^a-z0-9]', '', 'g') as match_key
    from staging.stg_games
)

select
    game_sk
    , match_key
from spine
