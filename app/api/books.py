from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.api import deps
from app.schemas.books import BookCreate, BookUpdate, BookOut
from app.services.book_service import BookService

router = APIRouter(prefix="/books", tags=["books"])


def get_book_service(db: Session = Depends(get_db)) -> BookService:
    return BookService(db)


@router.post("", response_model=BookOut, status_code=201)
def create_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(...),
    isbn: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    published_year: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    svc: BookService = Depends(get_book_service),
    current_user=Depends(deps.get_current_user),
):
    book = svc.create_book(
        file=file,
        title=title,
        author=author,
        isbn=isbn,
        language=language,
        published_year=published_year,
        tags=tags,
    )
    return book


@router.get("", response_model=List[BookOut])
def list_books(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    svc: BookService = Depends(get_book_service),
    current_user=Depends(deps.get_current_user),
):
    return svc.list_books(offset=offset, limit=limit)


@router.put("/{book_id}", response_model=BookOut)
def update_book(
    book_id: str,
    file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    isbn: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    published_year: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    svc: BookService = Depends(get_book_service),
    current_user=Depends(deps.get_current_user),
):
    book = svc.update_book(
        book_id=book_id,
        file=file,
        title=title,
        author=author,
        isbn=isbn,
        language=language,
        published_year=published_year,
        tags=tags,
    )
    return book


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: str,
    svc: BookService = Depends(get_book_service),
    current_user=Depends(deps.get_current_user),
):
    svc.delete_book(book_id)
    return None
