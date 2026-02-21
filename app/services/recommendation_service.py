from sqlalchemy.orm import Session
from app.repositories.recommendation_repo import RecommendationRepository
from app.repositories.tag_repo import TagRepository
from app.providers.recs import get_recommendation_provider
from app.providers.recs.content_based import ContentBasedRecommender
from app.providers.recs.ml_als import ALSRecommender
from scipy import sparse


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.rec_repo = RecommendationRepository(db)
        self.tag_repo = TagRepository(db)
        self.provider = get_recommendation_provider()

    def compute_and_get(self, user_id: str, limit: int = 10):
        # compute fresh recommendations synchronously
        user_pref_map = self.rec_repo.user_preferences_with_names(user_id)
        if not user_pref_map:
            self._compute_preferences(user_id)
            user_pref_map = self.rec_repo.user_preferences_with_names(user_id)
        book_tags = self.tag_repo.get_tags_for_books()
        exclude = self.rec_repo.user_borrowed_book_ids(user_id)
        scores, provider_name = self._recommend(user_id, book_tags, exclude, limit)
        snap = self.rec_repo.create_snapshot(user_id, provider=provider_name)
        self.rec_repo.replace_items(snap.id, scores)
        self.db.commit()
        return self.rec_repo.items_for_snapshot(snap.id), user_pref_map, book_tags

    def _compute_preferences(self, user_id: str):
        from app.models import UserTagPreference
        tag_counts: dict[str, float] = {}
        book_tags = self.tag_repo.get_tags_for_books()
        user_borrows = self.rec_repo.user_borrowed_book_ids(user_id)
        for bid in user_borrows:
            for t in book_tags.get(bid, []):
                tag_counts[t] = tag_counts.get(t, 0.0) + 1.0
        self.db.query(UserTagPreference).filter(UserTagPreference.user_id == user_id).delete()
        for tag_name, weight in tag_counts.items():
            tag_obj = self.tag_repo.get_or_create(tag_name)
            self.db.add(UserTagPreference(user_id=user_id, tag_id=tag_obj.id, weight=weight))
        self.db.flush()

    def _recommend(self, user_id: str, book_tags: dict[str, list[str]], exclude: set[str], limit: int):
        # Try provider-specific logic; fall back to content-based when empty
        provider = self.provider
        if isinstance(provider, ALSRecommender):
            rows = self.rec_repo.interactions()
            if not rows:
                return [], "content"
            user_to_idx, book_to_idx, _, book_ids = self.rec_repo.index_mappings(rows)
            data = []
            row_idx = []
            col_idx = []
            for u, b, w in rows:
                row_idx.append(user_to_idx[u])
                col_idx.append(book_to_idx[b])
                data.append(w)
            interactions = sparse.coo_matrix((data, (row_idx, col_idx)), shape=(len(user_to_idx), len(book_to_idx))).tocsr()
            # user_items for exclusion/filtering
            user_items = interactions[user_to_idx.get(str(user_id), -1)] if str(user_id) in user_to_idx else sparse.csr_matrix((1, len(book_to_idx)))
            if str(user_id) not in user_to_idx:
                # cold start for ALS -> fallback to content-based
                scores = ContentBasedRecommender().recommend(self.rec_repo.user_preferences_with_names(user_id), book_tags, exclude_book_ids=exclude, limit=limit)
                return scores, "content"
            scores = provider.score_with_matrix(
                user_id=user_to_idx[str(user_id)],
                interactions=interactions,
                user_items=user_items,
                book_index_to_id=book_ids,
                exclude_book_ids=exclude,
                limit=limit,
            )
            if scores:
                # merge content-based to ensure tagged recs surface
                cb_scores = ContentBasedRecommender().recommend(
                    self.rec_repo.user_preferences_with_names(user_id),
                    book_tags,
                    exclude_book_ids=exclude,
                    limit=limit,
                )
                seen = set(b for b, _ in scores)
                for b, s in cb_scores:
                    if b not in seen:
                        scores.append((b, s))
                return scores[:limit], "ml_als"
            # fallback when ALS returns empty
        scores = ContentBasedRecommender().recommend(self.rec_repo.user_preferences_with_names(user_id), book_tags, exclude_book_ids=exclude, limit=limit)
        return scores, "content"
