from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api import deps
from app.schemas.reviews import ReviewCreate, ReviewOut
from app.services.review_service import ReviewService

router = APIRouter(prefix="/books", tags=["reviews"])


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    return ReviewService(db)


@router.post("/{book_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(book_id: str, payload: ReviewCreate, svc: ReviewService = Depends(get_review_service), current_user=Depends(deps.get_current_user)):
    return svc.add_review(user_id=str(current_user.id), book_id=book_id, rating=payload.rating, review_text=payload.review_text)


@router.get("/{book_id}/reviews", response_model=List[ReviewOut])
def list_reviews(book_id: str, svc: ReviewService = Depends(get_review_service), current_user=Depends(deps.get_current_user)):
    return svc.list_reviews(book_id)
