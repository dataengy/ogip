/* @odts 0.1
model     fs.market_features
kind      table
owner     data-eng@ogip
tags      fs, feature-store, daily

columns:
  game_sk                varchar   !null unique
  popularity_score       double    non_negative
  metacritic_score       integer   between(0,100)
  opencritic_score       integer   between(0,100)
  avg_critic_score       double    between(0,100)
  psn_price_usd          double    non_negative
  psn_currency           varchar
  peak_players           bigint    non_negative
  has_critic_reception   boolean   !null
  has_console_pricing    boolean   !null
  has_traction           boolean   !null
*/
-- `core.console_pricing` grain is (game_sk, locale) across every PSN storefront, so a bare
-- `min(psn_price)` mixes currencies (e.g. JPY vs USD) into one meaningless number. Restrict to
-- the US/USD storefront (`en-us`) so the feature is single-currency and comparable, and keep
-- the `group by` as a defense-in-depth grain guarantee (one row per game_sk) even though
-- `core.console_pricing`'s own `unique(game_sk, locale)` check already makes at most one
-- `en-us` row per game possible. A game with no `en-us` row yields NULL here — the coverage
-- flag below already signals presence, so NULL is correct, not a gap.
with pricing_by_game as (
    select
        game_sk
        , min(psn_price) as psn_price_usd
        , min(psn_currency) as psn_currency
    from core.console_pricing
    where locale = 'en-us'
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
    , pg.psn_price_usd
    , pg.psn_currency
    , tr.peak_all as peak_players
    -- `game_sk` on cr/pg/tr is projected from the bridge and is therefore NEVER null (every
    -- bridge row survives the LEFT JOIN inside the source model); the actual measured column
    -- IS null when the title match failed, so that is what a coverage flag has to test.
    , coalesce(cr.metacritic_score, cr.opencritic_score) is not null as has_critic_reception
    , pg.psn_price_usd is not null as has_console_pricing
    , tr.peak_all is not null as has_traction
from core.game as g
left join core.critic_reception as cr on g.game_sk = cr.game_sk
left join pricing_by_game as pg on g.game_sk = pg.game_sk
left join core.traction as tr on g.game_sk = tr.game_sk
