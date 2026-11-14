from datetime import datetime

from pydantic import BaseModel


class CommentCreateSchema(BaseModel):
    text: str


class CommentSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    text: str
    created_at: datetime
    model_config = {"from_attributes": True}
