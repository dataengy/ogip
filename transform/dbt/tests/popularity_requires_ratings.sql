select violations
from (SELECT
  COUNT(*)
FROM {{ ref('market_features') }}
WHERE
  popularity_score > 0 AND COALESCE(ratings_count, 0) = 0) as _check(violations)
where violations != 0
