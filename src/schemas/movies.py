from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from enum import Enum


class MovieSortField(str, Enum):
    price = "price"
    year = "year"
    votes = "votes"
    imdb = "imdb"
    popularity = "popularity"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class GenreCreateSchema(BaseModel):
    name: str


class StarSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class StarCreateSchema(BaseModel):
    name: str


class DirectorSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class DirectorCreateSchema(BaseModel):
    name: str


class CertificationSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class CertificationCreateSchema(BaseModel):
    name: str


class MovieBaseSchema(BaseModel):
    name: str = Field(max_length=255)
    year: int = Field(ge=1888, le=2100)
    time: int = Field(ge=1, le=1200)
    imdb: float = Field(ge=0, le=10)
    votes: int = Field(ge=0)
    meta_score: float | None = Field(None, ge=0, le=100)
    gross: Decimal | None = Field(None, ge=0)
    description: str
    price: Decimal = Field(ge=0)


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    year: int
    imdb: float

    model_config = {
        "from_attributes": True,
    }


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int


class MovieDetailSchema(MovieBaseSchema):
    id: int
    uuid: UUID
    genres: list[GenreSchema]
    stars: list[StarSchema]
    directors: list[DirectorSchema]
    certification: CertificationSchema

    model_config = {
        "from_attributes": True,
    }


class MovieCreateSchema(MovieBaseSchema):
    certification_id: int
    genre_ids: list[int]
    star_ids: list[int]
    director_ids: list[int]


class MovieUpdateSchema(BaseModel):
    name: str | None = None
    year: int | None = Field(None, ge=1888, le=2100)
    time: int | None = Field(None, ge=1, le=1200)
    imdb: float | None = Field(None, ge=0, le=10)
    votes: int | None = Field(None, ge=0)
    meta_score: float | None = Field(None, ge=0, le=100)
    gross: Decimal | None = Field(None, ge=0)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    certification_id: int | None = None
    genre_ids: list[int] | None = None
    star_ids: list[int] | None = None
    director_ids: list[int] | None = None


class MessageResponseSchema(BaseModel):
    detail: str


class GenreWithCountSchema(BaseModel):
    id: int
    name: str
    movies_count: int

    model_config = {
        "from_attributes": True,
    }


class MovieRatingSchema(BaseModel):
    rating: int = Field(ge=1, le=10)
