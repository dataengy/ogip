SELECT
  game_sk
FROM {{ ref('market_features') }}
WHERE
  popularity_score > 0 AND COALESCE(ratings_count, 0) = 0
