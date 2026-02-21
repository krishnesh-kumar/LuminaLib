from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api import deps
from app.repositories.book_summary_repo import BookSummaryRepository

router = APIRouter(prefix="/books", tags=["analysis"])


def get_summary_repo(db: Session = Depends(get_db)):
    return BookSummaryRepository(db)


@router.get("/{book_id}/analysis")
def get_analysis(book_id: str, repo: BookSummaryRepository = Depends(get_summary_repo), current_user=Depends(deps.get_current_user)):
    summary = repo.get_summary(book_id)
    consensus = repo.get_consensus(book_id)
    if not summary and not consensus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis available")
    return {
        "book_id": book_id,
        "summary": summary.summary if summary else None,
        "summary_status": summary.status if summary else None,
        "summary_model": summary.model_name if summary else None,
        "summary_prompt_version": summary.prompt_version if summary else None,
        "consensus": consensus.consensus if consensus else None,
        "consensus_status": consensus.status if consensus else None,
        "consensus_model": consensus.model_name if consensus else None,
        "consensus_prompt_version": consensus.prompt_version if consensus else None,
    }
