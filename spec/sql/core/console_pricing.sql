/* @bruin
name: core.console_pricing
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [core, feature, daily]
depends:
  - staging.stg_game_match
  - staging.stg_psn_concepts
columns:
  - name: game_sk
    type: varchar
    checks: [{name: not_null}]
  - name: locale
    type: varchar
    checks: [{name: not_null}]
  - name: psn_price
    type: double
    checks: [{name: non_negative}]
  - name: psn_currency
    type: varchar
    checks: []
checks:
  - name: unique
    columns: [game_sk, locale]
@bruin */
select
    b.game_sk
    , psn.locale
    , psn.price as psn_price
    , psn.currency as psn_currency
from staging.stg_game_match as b
left join staging.stg_psn_concepts as psn
    on regexp_replace(lower(psn.name), '[^a-z0-9]', '', 'g') = b.match_key
