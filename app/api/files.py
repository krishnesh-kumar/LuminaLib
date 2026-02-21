from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api import deps
from app.repositories.book_repo import BookFileRepository, BookRepository
from app.providers.storage import get_storage_provider

router = APIRouter(prefix="/books", tags=["files"])


@router.get("/{book_id}/file")
def download_file(book_id: str, db: Session = Depends(get_db), current_user=Depends(deps.get_current_user)):
    book_repo = BookRepository(db)
    file_repo = BookFileRepository(db)
    book = book_repo.get(book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    bf = file_repo.get_by_book(book_id)
    if not bf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    storage = get_storage_provider()
    filename = bf.original_filename or "download"
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    # stream if provider supports it
    stream = getattr(storage, "get_stream", None)
    if callable(stream):
        body = stream(bf.object_key)
    else:
        body = iter([storage.get(bf.object_key)])
    return StreamingResponse(
        body,
        media_type=bf.mime_type or "application/octet-stream",
        headers={"Content-Disposition": disposition},
    )
