from pydantic import BaseModel


class MovieLikeCreateSchema(BaseModel):
    is_like: bool


class MovieLikeSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    is_like: bool
    model_config = {"from_attributes": True}


class MovieReactionsSchema(BaseModel):
    likes: int
    dislikes: int


class CommentLikeCreateSchema(BaseModel):
    is_like: bool


class CommentLikeSchema(BaseModel):
    id: int
    user_id: int
    comment_id: int
    is_like: bool

    model_config = {"from_attributes": True}


class CommentReactionsSchema(BaseModel):
    likes: int
    dislikes: int
