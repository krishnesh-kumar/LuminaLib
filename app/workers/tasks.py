import io
import logging
from pathlib import Path
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.providers.storage import get_storage_provider
from app.providers.llm import get_llm_provider
from app.providers.recs import get_recommendation_provider
from app.providers.recs.content_based import ContentBasedRecommender
from app.providers.recs.ml_als import ALSRecommender
from app.models import BookFile, BookAISummary, BookReviewConsensus, Review
from app.repositories.tag_repo import TagRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.repositories.borrow_repo import BorrowRepository
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pypdf import PdfReader

logger = logging.getLogger(__name__)

SUMMARY_PROMPT_PATH = Path(__file__).resolve().parent.parent / "core" / "prompts" / "summary.txt"
CONSENSUS_PROMPT_PATH = Path(__file__).resolve().parent.parent / "core" / "prompts" / "review_consensus.txt"


@celery_app.task(
    name="app.workers.tasks.summarize_book",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def summarize_book(self, book_id: str) -> str:
    storage = get_storage_provider()
    llm = get_llm_provider()
    prompt = SUMMARY_PROMPT_PATH.read_text(encoding="utf-8")
    with SessionLocal() as db:
        try:
            summary_row = db.execute(select(BookAISummary).where(BookAISummary.book_id == book_id)).scalar_one_or_none()
            if summary_row:
                summary_row.status = "running"
                summary_row.error_message = None
                db.flush()

            bf = db.execute(select(BookFile).where(BookFile.book_id == book_id)).scalar_one_or_none()
            if not bf:
                raise RuntimeError("Book file not found")

            file_bytes = storage.get(bf.object_key)
            text = _extract_text(file_bytes, bf.mime_type or "")
            full_prompt = f"{prompt}\n\n{text[:6000]}"
            summary = llm.generate(full_prompt)

            if not summary_row:
                summary_row = BookAISummary(
                    book_id=book_id,
                    status="completed",
                    model_name=settings.OLLAMA_MODEL,
                    prompt_version="v1",
                    summary=summary,
                )
                db.add(summary_row)
            else:
                summary_row.status = "completed"
                summary_row.model_name = settings.OLLAMA_MODEL
                summary_row.prompt_version = "v1"
                summary_row.summary = summary
            db.commit()
            return "ok"
        except Exception as e:
            logger.exception("summarize_book failed for %s", book_id)
            try:
                summary_row = db.execute(select(BookAISummary).where(BookAISummary.book_id == book_id)).scalar_one_or_none()
                if summary_row:
                    summary_row.status = "failed"
                    summary_row.error_message = str(e)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
            return f"error: {e}"


def _extract_text(file_bytes: bytes, mime_type: str) -> str:
    if mime_type and mime_type.endswith("pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    return file_bytes.decode("utf-8", errors="ignore")


@celery_app.task(
    name="app.workers.tasks.update_review_consensus",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def update_review_consensus(self, book_id: str) -> str:
    llm = get_llm_provider()
    prompt = CONSENSUS_PROMPT_PATH.read_text(encoding="utf-8")
    with SessionLocal() as db:
        try:
            row = db.execute(select(BookReviewConsensus).where(BookReviewConsensus.book_id == book_id)).scalar_one_or_none()
            if row:
                row.status = "running"
                row.error_message = None
                db.flush()

            reviews = db.execute(select(Review).where(Review.book_id == book_id)).scalars().all()
            if not reviews:
                raise RuntimeError("No reviews found")

            text_parts = []
            for r in reviews:
                piece = f"Rating: {r.rating}. Review: {r.review_text or ''}"
                text_parts.append(piece)
            combined = "\n".join(text_parts)
            full_prompt = f"{prompt}\n\n{combined[:6000]}"
            consensus = llm.generate(full_prompt)

            if not row:
                row = BookReviewConsensus(
                    book_id=book_id,
                    status="completed",
                    model_name=settings.OLLAMA_MODEL,
                    prompt_version="v1",
                    consensus=consensus,
                )
                db.add(row)
            else:
                row.status = "completed"
                row.model_name = settings.OLLAMA_MODEL
                row.prompt_version = "v1"
                row.consensus = consensus
            db.commit()
            return "ok"
        except Exception as e:
            logger.exception("update_review_consensus failed for %s", book_id)
            try:
                row = db.execute(select(BookReviewConsensus).where(BookReviewConsensus.book_id == book_id)).scalar_one_or_none()
                if row:
                    row.status = "failed"
                    row.error_message = str(e)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
            return f"error: {e}"


@celery_app.task(
    name="app.workers.tasks.recompute_user_preferences",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def recompute_user_preferences(self, user_id: str) -> str:
    with SessionLocal() as db:
        tags_repo = TagRepository(db)
        rec_repo = RecommendationRepository(db)
        from app.models import UserTagPreference

        # Count tag occurrences across all borrows
        tag_counts: dict[str, float] = {}
        user_borrow_book_ids = rec_repo.user_borrowed_book_ids(user_id)
        book_tags = tags_repo.get_tags_for_books()
        for bid in user_borrow_book_ids:
            for t in book_tags.get(bid, []):
                tag_counts[t] = tag_counts.get(t, 0.0) + 1.0

        # Reset and insert preferences
        db.query(UserTagPreference).filter(UserTagPreference.user_id == user_id).delete()
        for tag_name, weight in tag_counts.items():
            tag_obj = tags_repo.get_or_create(tag_name)
            db.add(UserTagPreference(user_id=user_id, tag_id=tag_obj.id, weight=weight))
        db.commit()
    return f"preferences recomputed for {user_id}"


@celery_app.task(
    name="app.workers.tasks.recompute_recommendations",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def recompute_recommendations(self, user_id: str) -> str:
    with SessionLocal() as db:
        rec_repo = RecommendationRepository(db)
        tag_repo = TagRepository(db)
        provider = get_recommendation_provider()

        user_pref_map = rec_repo.user_preferences_with_names(user_id)
        book_tags = tag_repo.get_tags_for_books()
        exclude = rec_repo.user_borrowed_book_ids(user_id)

        provider_name = "content"
        if isinstance(provider, ALSRecommender):
            rows = rec_repo.interactions()
            scores = []
            if rows:
                user_to_idx, book_to_idx, _, book_ids = rec_repo.index_mappings(rows)
                data = []
                row_idx = []
                col_idx = []
                for u, b, w in rows:
                    row_idx.append(user_to_idx[u])
                    col_idx.append(book_to_idx[b])
                    data.append(w)
                interactions = sparse.coo_matrix((data, (row_idx, col_idx)), shape=(len(user_to_idx), len(book_to_idx))).tocsr()
                if str(user_id) in user_to_idx:
                    user_items = interactions[user_to_idx[str(user_id)]]
                    scores = provider.score_with_matrix(
                        user_id=user_to_idx[str(user_id)],
                        interactions=interactions,
                        user_items=user_items,
                        book_index_to_id=book_ids,
                        exclude_book_ids=exclude,
                        limit=20,
                    )
                    provider_name = "ml_als" if scores else provider_name
            if not scores:
                scores = ContentBasedRecommender().recommend(user_pref_map, book_tags, exclude_book_ids=exclude, limit=20)
                provider_name = "content"
            else:
                cb_scores = ContentBasedRecommender().recommend(user_pref_map, book_tags, exclude_book_ids=exclude, limit=20)
                seen = set(b for b, _ in scores)
                for b, s in cb_scores:
                    if b not in seen:
                        scores.append((b, s))
                scores = scores[:20]
        else:
            scores = provider.recommend(user_pref_map, book_tags, exclude_book_ids=exclude, limit=20)
            provider_name = "content"
        snap = rec_repo.create_snapshot(user_id, provider=provider_name)
        rec_repo.replace_items(snap.id, scores)
        db.commit()
    return f"recommendations recomputed for {user_id}"
