from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api import deps
from app.services.borrow_service import BorrowService
from app.schemas.borrows import BorrowOut

router = APIRouter(prefix="/books", tags=["borrow"])


def get_borrow_service(db: Session = Depends(get_db)) -> BorrowService:
    return BorrowService(db)


@router.post("/{book_id}/borrow", response_model=BorrowOut, status_code=201)
def borrow_book(book_id: str, svc: BorrowService = Depends(get_borrow_service), current_user=Depends(deps.get_current_user)):
    return svc.borrow(user_id=current_user.id, book_id=book_id)


@router.post("/{book_id}/return", response_model=BorrowOut)
def return_book(book_id: str, svc: BorrowService = Depends(get_borrow_service), current_user=Depends(deps.get_current_user)):
    return svc.return_book(user_id=current_user.id, book_id=book_id)
