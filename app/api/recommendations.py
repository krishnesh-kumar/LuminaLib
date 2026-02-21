from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api import deps
from app.schemas.recommendations import RecommendationsOut, RecommendationItemOut
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_rec_service(db: Session = Depends(get_db)) -> RecommendationService:
    return RecommendationService(db)


@router.get("", response_model=RecommendationsOut)
def get_recommendations(
    svc: RecommendationService = Depends(get_rec_service), current_user=Depends(deps.get_current_user)
):
    items, prefs, book_tags = svc.compute_and_get(user_id=str(current_user.id), limit=10)
    if not prefs or not book_tags or len(items) == 0:
        return RecommendationsOut(items=[], message="No recommendations yet. Add tags to books and borrow to build signal.")
    return RecommendationsOut(items=[RecommendationItemOut(book_id=item.book_id, score=item.score, rank=item.rank) for item in items])
