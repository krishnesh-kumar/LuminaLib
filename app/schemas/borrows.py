from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BorrowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    book_id: UUID
    borrowed_at: datetime
    due_at: datetime | None = None
    returned_at: datetime | None = None
