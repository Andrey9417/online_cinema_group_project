from decimal import Decimal

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models.movies import Movie, Genre, Director, Star
from schemas.movies import MovieCreateSchema, MovieUpdateSchema
from collections.abc import Sequence

SORT_FIELDS = {
    "price": Movie.price,
    "year": Movie.year,
    "votes": Movie.votes,
    "imdb": Movie.imdb,
}


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
        db: AsyncSession,
        page: int = 1,
        per_page: int = 10,
        sort_by: str | None = None,
        search: str | None = None,
        year: int | None = None,
        min_imdb: float | None = None,
        price: Decimal | None = None,
        certification_id: int | None = None
) -> tuple[Sequence[Movie], int]:
    offset = (page - 1) * per_page

    conditions = []

    if year is not None:
        conditions.append(Movie.year == year)
    if min_imdb is not None:
        conditions.append(Movie.imdb >= min_imdb)
    if price is not None:
        conditions.append(Movie.price <= price)
    if certification_id is not None:
        conditions.append(Movie.certification_id == certification_id)

    if search:
        pattern = f"%{search}%"
        conditions.append(
            or_(
                Movie.name.ilike(pattern),
                Movie.description.ilike(pattern),
                Movie.stars.any(Star.name.ilike(pattern)),
                Movie.directors.any(Director.name.ilike(pattern)),
            )
        )

    stmt = (
        select(Movie)
        .where(*conditions)
        .offset(offset)
        .limit(per_page)
    )

    column = None
    descending = False
    if sort_by:
        descending = sort_by.startswith("-")
        field_name = sort_by.lstrip("-")
        column = SORT_FIELDS.get(field_name)

    if column is not None:
        order = column.desc() if descending else column.asc()
        stmt = stmt.order_by(order)
    else:
        stmt = stmt.order_by(Movie.id)

    count_stmt = select(func.count(Movie.id)).where(*conditions)
    result = await db.execute(stmt)
    movies = result.scalars().all()

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
