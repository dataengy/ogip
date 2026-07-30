select game_sk
from fs.market_features
where popularity_score > 0 and coalesce(ratings_count, 0) = 0
