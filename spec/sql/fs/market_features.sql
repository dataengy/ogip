/* @bruin
name: fs.market_features
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [fs, feature-store, daily]
depends:
  - core.game
  - core.critic_reception
  - core.console_pricing
  - core.traction
columns:
  - name: game_sk
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: popularity_score
    type: double
    checks: [{name: non_negative}]
  - name: metacritic_score
    type: integer
    checks: [{name: between, args: [0, 100]}]
  - name: opencritic_score
    type: integer
    checks: [{name: between, args: [0, 100]}]
  - name: avg_critic_score
    type: double
    checks: [{name: between, args: [0, 100]}]
  - name: psn_price
    type: double
    checks: [{name: non_negative}]
  - name: peak_players
    type: bigint
    checks: [{name: non_negative}]
  - name: has_critic_reception
    type: boolean
    checks: [{name: not_null}]
  - name: has_console_pricing
    type: boolean
    checks: [{name: not_null}]
  - name: has_traction
    type: boolean
    checks: [{name: not_null}]
@bruin */
-- `core.console_pricing` grain is (game_sk, locale); collapse to one row per game_sk here
-- (cheapest observed locale price) so this feature store keeps its own declared grain
-- (one row per game_sk) instead of fanning out on locale.
with pricing_by_game as (
    select
        game_sk
        , min(psn_price) as psn_price
    from core.console_pricing
    group by game_sk
)

select
    g.game_sk
    , g.game_id
    , g.title
    , g.release_year
    , g.rating
    , g.ratings_count
    , g.metacritic
    , g.playtime_hours
    , g.added_count
    , coalesce(g.rating, 0) * ln(1 + coalesce(g.ratings_count, 0)) as popularity_score
    , coalesce(g.metacritic, 0) / 100.0 as critic_score
    , cr.metacritic_score
    , cr.opencritic_score
    , case
        when cr.metacritic_score is not null and cr.opencritic_score is not null
            then (cr.metacritic_score + cr.opencritic_score) / 2.0
        else coalesce(cr.metacritic_score, cr.opencritic_score)
    end as avg_critic_score
    , pg.psn_price
    , tr.peak_all as peak_players
    -- `game_sk` on cr/pg/tr is projected from the bridge and is therefore NEVER null (every
    -- bridge row survives the LEFT JOIN inside the source model); the actual measured column
    -- IS null when the title match failed, so that is what a coverage flag has to test.
    , coalesce(cr.metacritic_score, cr.opencritic_score) is not null as has_critic_reception
    , pg.psn_price is not null as has_console_pricing
    , tr.peak_all is not null as has_traction
from core.game as g
left join core.critic_reception as cr on g.game_sk = cr.game_sk
left join pricing_by_game as pg on g.game_sk = pg.game_sk
left join core.traction as tr on g.game_sk = tr.game_sk
