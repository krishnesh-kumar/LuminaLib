from uuid import UUID
from pydantic import BaseModel, ConfigDict


class RecommendationItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    book_id: UUID
    score: float
    rank: int


class RecommendationsOut(BaseModel):
    items: list[RecommendationItemOut]
    message: str | None = None
