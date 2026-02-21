from typing import Sequence, Dict
from .base import RecommendationProvider


class ContentBasedRecommender(RecommendationProvider):
    def recommend(
        self,
        user_preferences: Dict[str, float],
        book_tags: Dict[str, list[str]],
        exclude_book_ids: set[str],
        limit: int = 10,
    ) -> Sequence[tuple[str, float]]:
        scores = []
        for book_id, tags in book_tags.items():
            if book_id in exclude_book_ids:
                continue
            score = sum(user_preferences.get(tag, 0.0) for tag in tags)
            if score > 0:
                scores.append((book_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]
