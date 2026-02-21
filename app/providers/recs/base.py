from abc import ABC, abstractmethod
from typing import Sequence


class RecommendationProvider(ABC):
    @abstractmethod
    def recommend(
        self,
        user_preferences: dict[str, float],
        book_tags: dict[str, list[str]],
        exclude_book_ids: set[str],
        limit: int = 10,
    ) -> Sequence[tuple[str, float]]:
        ...
