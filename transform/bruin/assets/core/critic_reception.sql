/* @bruin
name: core.critic_reception
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [core, feature, daily]
depends:
  - staging.stg_game_match
  - staging.stg_metacritic_games
  - staging.stg_opencritic_games
columns:
  - name: game_sk
    type: varchar
    primary_key: true
    checks: [{name: not_null}, {name: unique}]
  - name: metacritic_score
    type: integer
    checks: [{name: between, args: [0, 100]}]
  - name: opencritic_score
    type: integer
    checks: [{name: between, args: [0, 100]}]
@bruin */
select
    b.game_sk
    , mc.metascore as metacritic_score
    , oc.score as opencritic_score
from staging.stg_game_match as b
left join staging.stg_metacritic_games as mc
    on regexp_replace(lower(mc.name), '[^a-z0-9]', '', 'g') = b.match_key
left join staging.stg_opencritic_games as oc
    on regexp_replace(lower(oc.name), '[^a-z0-9]', '', 'g') = b.match_key
