import os
# Limit OpenBLAS threads to avoid noisy warnings and oversubscription in tests/CI
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
from typing import Sequence, Dict, List, Tuple, Set
from scipy import sparse
from implicit.als import AlternatingLeastSquares

from app.providers.recs.base import RecommendationProvider


class ALSRecommender(RecommendationProvider):
    def __init__(self, factors: int = 64, iterations: int = 10, alpha: float = 40.0):
        self.factors = factors
        self.iterations = iterations
        self.alpha = alpha

    def recommend(
        self,
        user_preferences: Dict[str, float],
        book_tags: Dict[str, List[str]],
        exclude_book_ids: Set[str],
        limit: int = 10,
    ) -> Sequence[Tuple[str, float]]:
        # This provider works off interactions passed in via user_preferences/book_tags
        # but we need a proper interaction matrix; delegate to caller to build it via `score_with_matrix`.
        raise NotImplementedError("Use score_with_matrix with prebuilt matrices")

    def score_with_matrix(
        self,
        user_id: int,
        interactions: sparse.csr_matrix,
        user_items: sparse.csr_matrix,
        book_index_to_id: List[str],
        exclude_book_ids: Set[str],
        limit: int = 10,
    ) -> Sequence[Tuple[str, float]]:
        if interactions.shape[0] == 0 or interactions.shape[1] == 0:
            return []

        model = AlternatingLeastSquares(
            factors=self.factors,
            iterations=self.iterations,
            regularization=0.01,
            use_gpu=False,
        )
        model.fit(interactions)

        # implicit expects user-items in CSR for recommend to use as exclude baseline
        recs = model.recommend(user_id, user_items, N=limit * 2, filter_already_liked_items=True)
        # implicit may return (ids, scores) tuple depending on version
        if isinstance(recs, tuple) and len(recs) == 2:
            recs = list(zip(recs[0], recs[1]))
        results = []
        for idx, score in recs:
            book_id = book_index_to_id[idx]
            if book_id in exclude_book_ids:
                continue
            results.append((book_id, float(score)))
            if len(results) >= limit:
                break
        return results
