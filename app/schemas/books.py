from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    isbn: Optional[str] = None
    language: Optional[str] = None
    published_year: Optional[int] = None


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    language: Optional[str] = None
    published_year: Optional[int] = None


class BookFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    storage_provider: str
    object_key: str
    file_type: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    original_filename: Optional[str] = None


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    author: str
    isbn: Optional[str] = None
    language: Optional[str] = None
    published_year: Optional[int] = None
    file: Optional[BookFileOut] = None
    tags: list[str] = []
