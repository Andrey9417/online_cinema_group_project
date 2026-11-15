from decimal import Decimal

from sqlalchemy import select, func, or_, insert, delete, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from database.models.movies import (
    Movie,
    Genre,
    Director,
    Star,
    FavoriteMoviesTable,
    movie_genres,
    MovieRating,
)
from schemas.movies import MovieCreateSchema, MovieUpdateSchema, MovieSortField, SortOrder
from collections.abc import Sequence
from database.models.orders import Order, OrderItem, OrderStatusEnum

SORT_FIELDS = {
    "price": Movie.price,
    "year": Movie.year,
    "votes": Movie.votes,
    "imdb": Movie.imdb,
    "popularity": Movie.votes,
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
        page: int,
        per_page: int,
        sort_by: MovieSortField = MovieSortField.year,
        order: SortOrder = SortOrder.desc,
        search: str | None = None,
        year: int | None = None,
        min_imdb: float | None = None,
        price: Decimal | None = None,
        certification_id: int | None = None,
) -> tuple[Sequence[Movie], int]:
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

    column = SORT_FIELDS[sort_by.value]
    order_by = column.desc() if order == SortOrder.desc else column.asc()

    stmt = (
        select(Movie)
        .where(*conditions)
        .order_by(order_by)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    movies = result.scalars().all()

    count_stmt = select(func.count()).select_from(Movie).where(*conditions)
    total_items = await db.scalar(count_stmt)

    return movies, total_items


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

    await db.delete(movie)
    await db.commit()
    return True


async def add_favorite(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    exists = await db.scalar(
        select(FavoriteMoviesTable.c.movie_id).where(
            FavoriteMoviesTable.c.user_id == user_id,
            FavoriteMoviesTable.c.movie_id == movie_id,
        )
    )
    if exists:
        return False

    await db.execute(insert(FavoriteMoviesTable).values(user_id=user_id, movie_id=movie_id))
    await db.commit()
    return True


async def remove_favorite(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    result = await db.execute(
        delete(FavoriteMoviesTable).where(
            FavoriteMoviesTable.c.user_id == user_id,
            FavoriteMoviesTable.c.movie_id == movie_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_favorite_movies(
        db: AsyncSession,
        user_id: int,
        page: int,
        per_page: int,
        search: str | None = None,
        year: int | None = None,
        min_imdb: float | None = None,
        sort_by: str = "year",
        order: str = "desc",
) -> tuple[list[Movie], int]:
    conditions = [FavoriteMoviesTable.c.user_id == user_id]

    if search:
        like = f"%{search}%"
        conditions.append(
            Movie.name.ilike(like)
            | Movie.description.ilike(like)
            | Movie.stars.any(Star.name.ilike(like))
            | Movie.directors.any(Director.name.ilike(like))
        )
    if year is not None:
        conditions.append(Movie.year == year)
    if min_imdb is not None:
        conditions.append(Movie.imdb >= min_imdb)

    base = (
        select(Movie)
        .join(FavoriteMoviesTable, FavoriteMoviesTable.c.movie_id == Movie.id)
        .where(*conditions)
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    direction = asc if order == "asc" else desc
    stmt = (
        base.order_by(direction(SORT_FIELDS[sort_by]), Movie.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    movies = (await db.execute(stmt)).scalars().all()
    return movies, total


async def get_genres_with_count(db: AsyncSession):
    stmt = (
        select(
            Genre.id,
            Genre.name,
            func.count(movie_genres.c.movie_id).label("movies_count"),
        )
        .outerjoin(movie_genres, movie_genres.c.genre_id == Genre.id)
        .group_by(Genre.id, Genre.name)
        .order_by(Genre.name)
    )
    result = await db.execute(stmt)
    return result.all()


async def get_movies_by_genre(
        db: AsyncSession, genre_id: int, page: int = 1, per_page: int = 10
) -> tuple[list[Movie], int]:
    base = (
        select(Movie)
        .join(movie_genres, movie_genres.c.movie_id == Movie.id)
        .where(movie_genres.c.genre_id == genre_id)
    )

    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    stmt = base.order_by(Movie.id).offset((page - 1) * per_page).limit(per_page)
    movies = (await db.execute(stmt)).scalars().all()

    return movies, total


async def set_rating(db: AsyncSession, user_id: int, movie_id: int, rating: int) -> None:
    existing = await db.get(MovieRating, (user_id, movie_id))

    if existing:
        existing.rating = rating
    else:
        db.add(MovieRating(user_id=user_id, movie_id=movie_id, rating=rating))

    await db.commit()


async def remove_rating(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    result = await db.execute(
        delete(MovieRating).where(
            MovieRating.user_id == user_id,
            MovieRating.movie_id == movie_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def movie_is_purchased(db: AsyncSession, movie_id: int) -> bool:
    stmt = (
        select(OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            OrderItem.movie_id == movie_id,
            Order.status == OrderStatusEnum.PAID,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.first() is not None
