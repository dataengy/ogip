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
-- Keep only games that actually HAVE a PSN listing. This is a pricing FACT table at
-- (game_sk, locale) grain, so an unmatched game must have NO row rather than an all-null
-- one -- otherwise not_null(locale) fails for every unmatched game (caught by the e2e
-- SQLMesh run, which `make check` does not exercise). This is NOT the forbidden
-- spine-dropping inner join: the rawg spine survives downstream, where fs.market_features
-- LEFT JOINs this model, so unmatched games still appear with a null price and a false
-- psn coverage flag.
where psn.locale is not null
