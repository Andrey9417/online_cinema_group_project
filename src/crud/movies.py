from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models.movies import Movie, Genre, Director, Star
from schemas.movies import MovieCreateSchema, MovieUpdateSchema
from collections.abc import Sequence


async def _get_by_ids(
    db: AsyncSession, model: type, ids: list[int]
) -> Sequence:
    result = await db.execute(select(model).where(model.id.in_(ids)))
    return result.scalars().all()


async def get_movie_by_id(db: AsyncSession, movie_id: int) -> Movie | None:
    stmt = (
        select(Movie)
        .options(
            joinedload(Movie.genres),
            joinedload(Movie.directors),
            joinedload(Movie.stars),
            joinedload(Movie.certification),
        ).where(Movie.id == movie_id)
    )

    result = await db.execute(stmt)
    movie = result.unique().scalar_one_or_none()

    return movie


async def get_movie_list(
        db: AsyncSession, page: int = 1, per_page: int = 10
) -> tuple[list[Movie], int]:
    offset = (page - 1) * per_page

    stmt = (select(Movie).offset(offset).limit(per_page).order_by(Movie.id))
    result = await db.execute(stmt)
    movies = result.scalars().all()

    count_stmt = select(func.count(Movie.id))
    result_count = await db.execute(count_stmt)
    count = result_count.scalar()

    return (movies, count)


async def create_movie(db: AsyncSession, movie_data: MovieCreateSchema) -> Movie:
    genres = await _get_by_ids(db, Genre, movie_data.genre_ids)
    directors = await _get_by_ids(db, Director, movie_data.director_ids)
    stars = await _get_by_ids(db, Star, movie_data.star_ids)

    movie = Movie(
        **movie_data.model_dump(
            exclude={"genre_ids", "star_ids", "director_ids"}
        ),
        genres=genres,
        directors=directors,
        stars=stars,
    )

    db.add(movie)
    await db.commit()
    await db.refresh(movie)

    return movie


async def update_movie(
    db: AsyncSession, movie_id: int, movie_data: MovieUpdateSchema
) -> Movie | None:
    movie = await get_movie_by_id(db, movie_id)

    if movie is None:
        return None

    data = movie_data.model_dump(exclude_unset=True)
    genre_ids = data.pop("genre_ids", None)
    star_ids = data.pop("star_ids", None)
    director_ids = data.pop("director_ids", None)

    for field, value in data.items():
        setattr(movie, field, value)

    if genre_ids is not None:
        movie.genres = await _get_by_ids(db, Genre, genre_ids)

    if star_ids is not None:
        movie.stars = await _get_by_ids(db, Star, star_ids)

    if director_ids is not None:
        movie.directors = await _get_by_ids(db, Director, director_ids)

    await db.commit()
    await db.refresh(movie)
    return movie


async def delete_movie(db: AsyncSession, movie_id: int) -> bool:
    movie = await db.get(Movie, movie_id)

    if movie is None:
        return False

    # TODO: заборонити видалення, якщо фільм куплений

    await db.delete(movie)
    await db.commit()
    return True
