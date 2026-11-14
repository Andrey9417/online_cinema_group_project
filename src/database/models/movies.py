from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid, CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

movie_stars = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    movies: Mapped[list["Movie"]] = relationship(
        secondary=movie_genres, back_populates="genres"
    )


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    movies: Mapped[list["Movie"]] = relationship(
        secondary=movie_stars, back_populates="stars"
    )


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    movies: Mapped[list["Movie"]] = relationship(
        secondary=movie_directors, back_populates="directors"
    )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    movies: Mapped[list["Movie"]] = relationship(back_populates="certification")


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="uc_movie_name_year_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    year: Mapped[int]
    time: Mapped[int]
    imdb: Mapped[float] = mapped_column(Float)
    votes: Mapped[int]
    meta_score: Mapped[Optional[float]] = mapped_column(Float)
    gross: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"))

    certification: Mapped["Certification"] = relationship(back_populates="movies")
    genres: Mapped[list["Genre"]] = relationship(
        secondary=movie_genres, back_populates="movies"
    )
    directors: Mapped[list["Director"]] = relationship(
        secondary=movie_directors, back_populates="movies"
    )
    stars: Mapped[list["Star"]] = relationship(
        secondary=movie_stars, back_populates="movies"
    )


FavoriteMoviesTable = Table(
    "favorite_movies",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
)


class MovieRating(Base):
    __tablename__ = "movie_ratings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    rating: Mapped[int] = mapped_column()

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 10", name="ck_movie_ratings_rating_range"),
    )
