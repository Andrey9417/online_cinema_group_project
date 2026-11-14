from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field, Field

from schemas.movies import GenreSchema


class CartMovieSchema(BaseModel):
    id: int
    name: str
    year: int
    price: Decimal
    genres: list[GenreSchema]

    model_config = ConfigDict(from_attributes=True)


class CartItemResponse(BaseModel):
    id: int
    movie: CartMovieSchema
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    items: list[CartItemResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def total_amount(self) -> Decimal:
        return sum(
            (item.movie.price for item in self.items),
            start=Decimal("0.00"),
        )


class CartItemCreateSchema(BaseModel):
    movie_id: int = Field(gt=0)
