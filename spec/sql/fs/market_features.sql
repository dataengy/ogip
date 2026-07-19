/* @bruin
name: fs.market_features
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [fs, feature-store, daily]
depends:
  - core.game
checks:
  # ASSET-level: no single column can assert "the table produced rows at all".
  - {name: not_empty}
columns:
  - name: game_sk
    type: varchar
    # relationships = referential integrity back to the core entity this FS row describes.
    checks:
      - {name: not_null}
      - {name: unique}
      - {name: relationships, value: {to: game, field: game_sk}}
  - name: popularity_score
    type: double
    checks: [{name: not_null}, {name: non_negative}]
  - name: critic_score
    type: double
    # metacritic/100 — a closed range, so assert both bounds rather than just non-negativity.
    checks: [{name: accepted_range, value: {min: 0, max: 1}}]
custom_checks:
  # SINGULAR test: a bespoke assertion that is not a per-column rule. Must return ZERO rows.
  - name: popularity_requires_ratings
    query: |
      select game_sk
      from fs.market_features
      where popularity_score > 0 and coalesce(ratings_count, 0) = 0
unit_tests:
  # UNIT test (dbt >= 1.8): proves the popularity_score FORMULA on mocked input — no warehouse
  # data involved. rating=0 must zero the score even when ratings_count is large.
  - name: popularity_score_is_zero_when_rating_is_zero
    given:
      - input: ref('game')
        rows:
          - {game_sk: "a", game_id: 1, title: t, release_year: 2020, rating: 0.0,
             ratings_count: 500, metacritic: 80, playtime_hours: 1, added_count: 1}
    expect:
      rows:
        - {game_sk: "a", popularity_score: 0.0}
@bruin */
select
    game_sk
    , game_id
    , title
    , release_year
    , rating
    , ratings_count
    , metacritic
    , playtime_hours
    , added_count
    , coalesce(rating, 0) * ln(1 + coalesce(ratings_count, 0)) as popularity_score
    , coalesce(metacritic, 0) / 100.0 as critic_score
from core.game
