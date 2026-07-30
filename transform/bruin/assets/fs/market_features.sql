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
checks:
  # ASSET-level: no single column can assert "the table produced rows at all".
  - {name: not_empty}
columns:
  - name: game_sk
    type: varchar
    # relationships = referential integrity back to the core entity this FS row describes.
    # Flat keys (to/field), NOT `value: {…}`: Bruin's columnCheck parser fatally rejects a map
    # in `value:` ("unexpected type map[string]interface {}"), while unknown flat fields only
    # warn — the same tolerance the `between`/`args` spelling relies on.
    checks:
      - {name: not_null}
      - {name: unique}
      - {name: relationships, to: game, field: game_sk}
  - name: popularity_score
    type: double
    checks: [{name: not_null}, {name: non_negative}]
  - name: critic_score
    type: double
    # metacritic/100 — a closed range, so assert both bounds rather than just non-negativity.
    checks: [{name: between, args: [0, 1]}]
  - name: metacritic_score
    type: integer
    checks: [{name: between, args: [0, 100]}]
  - name: opencritic_score
    type: integer
    checks: [{name: between, args: [0, 100]}]
  - name: avg_critic_score
    type: double
    checks: [{name: between, args: [0, 100]}]
  - name: psn_price_usd
    type: double
    checks: [{name: non_negative}]
  - name: psn_currency
    type: varchar
    checks: []
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
custom_checks:
  # SINGULAR test: a bespoke assertion that is not a per-column rule. Must return ZERO rows.
  - name: popularity_requires_ratings
    query: |
      select game_sk
      from fs.market_features
      where popularity_score > 0 and coalesce(ratings_count, 0) = 0
unit_tests:
  # UNIT test (dbt >= 1.8): proves the popularity_score FORMULA on mocked input — no warehouse
  # data involved. rating=0 must zero the score even when ratings_count is large. The three
  # scraped-source refs are mocked EMPTY: the LEFT JOINs then yield NULLs, which is exactly the
  # no-coverage case, and the expect row only compares the columns it names.
  - name: popularity_score_is_zero_when_rating_is_zero
    given:
      - input: ref('game')
        rows:
          - {game_sk: "a", game_id: 1, title: t, release_year: 2020, rating: 0.0,
             ratings_count: 500, metacritic: 80, playtime_hours: 1, added_count: 1}
      - input: ref('critic_reception')
        rows: []
      - input: ref('console_pricing')
        rows: []
      - input: ref('traction')
        rows: []
    expect:
      rows:
        - {game_sk: "a", popularity_score: 0.0}
@bruin */
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
