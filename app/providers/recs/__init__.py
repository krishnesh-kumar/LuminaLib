from app.providers.recs.content_based import ContentBasedRecommender
from app.providers.recs.ml_als import ALSRecommender
from app.providers.recs.base import RecommendationProvider
from app.core.config import settings


def get_recommendation_provider() -> RecommendationProvider:
    if settings.RECS_PROVIDER == "ml_als":
        return ALSRecommender()
    return ContentBasedRecommender()
