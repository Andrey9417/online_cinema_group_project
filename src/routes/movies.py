from decimal import Decimal
from math import ceil
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.dependencies import get_current_user
from crud.likes import set_movie_reaction, delete_movie_reaction, get_movie_reactions
from database.models import Movie, User, MovieLike
from database.session import get_db_session
from config.dependencies import require_moderator
from crud.movies import (
    get_movie_by_id,
    get_movie_list,
    create_movie,
    update_movie,
    delete_movie,
    add_favorite,
    remove_favorite,
    get_favorite_movies,
    get_movies_by_genre,
    get_genres_with_count,
    set_rating,
    remove_rating, movie_is_purchased,
)
from crud.reference import get_genre_by_id
from schemas.likes import MovieLikeSchema, MovieLikeCreateSchema, MovieReactionsSchema
from schemas.movies import (
    MovieDetailSchema,
    MovieListResponseSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
    MessageResponseSchema,
    GenreWithCountSchema,
    MovieRatingSchema, MovieSortField, SortOrder,
)

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get(
    "/favorites/",
    response_model=MovieListResponseSchema,
    summary="List my favorite movies",
    description=(
        "Returns the current user's favorites with pagination. "
        "Supports search (title, description, actor, director), "
        "filters (year, min_imdb) and sorting."
    ),
)
async def list_favorites(
        page: int = Query(
            1, ge=1, description="Page number (1-based index)"
        ),
        per_page: int = Query(
            10, ge=1, le=20, description="Number of items per page"
        ),
        search: str | None = Query(
            None,
            description="Substring of title, description, actor or director",
        ),
        year: int | None = Query(
            None, description="Exact release year"
        ),
        min_imdb: float | None = Query(
            None, ge=0, le=10, description="Minimum IMDb rating"
        ),
        sort_by: Literal["price", "year", "imdb", "popularity"] = Query(
            "year",
            description="Sort field (popularity = number of IMDb votes)",
        ),
        order: Literal["asc", "desc"] = Query(
            "desc", description="Sort direction"
        ),
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
):
    movies, total = await get_favorite_movies(
        db, current_user.id, page, per_page,
        search, year, min_imdb, sort_by, order,
    )
    total_pages = ceil(total / per_page)

    base = "/movies/favorites/"
    return {
        "movies": movies,
        "prev_page": f"{base}?page={page - 1}&per_page={per_page}" if page > 1 else None,
        "next_page": f"{base}?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        "total_pages": total_pages,
        "total_items": total,
    }


@router.get(
    "/genres/",
    response_model=list[GenreWithCountSchema],
    summary="List genres with movie counts",
    description=(
        "All genres with the number of movies in each. Use "
        "GET /movies/genres/{genre_id}/movies/ to see a genre's movies."
    ),
)
async def list_genres(db: AsyncSession = Depends(get_db_session)):
    return await get_genres_with_count(db)


@router.get(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Get movie details",
    responses={404: {"description": "Movie not found"}},
)
async def movie_detail(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session)
) -> Movie:
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found",
        )

    return movie


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    summary="List movies",
    description=(
            "Paginated movie catalog with filtering (release year, minimum "
            "IMDb rating, maximum price, certification), full-text search "
            "(title, description, star, director) and sorting by price, year, "
            "votes, IMDb or popularity."
    ),
)
async def movie_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(
            10,
            ge=1,
            le=20,
            description="Number of items per page"
        ),
        sort_by: MovieSortField = Query(MovieSortField.year),
        order: SortOrder = Query(SortOrder.desc),
        search: str | None = Query(
            None,
            description="Search by title, description, actor or director",
        ),
        year: int | None = Query(None),
        min_imdb: float | None = Query(None, ge=0, le=10),
        price: Decimal | None = Query(None, ge=0),
        certification_id: int | None = Query(None),
        db: AsyncSession = Depends(get_db_session)
) -> MovieListResponseSchema:
    movies, total_items = await get_movie_list(
        db,
        page,
        per_page,
        sort_by=sort_by,
        order=order,
        search=search,
        year=year,
        min_imdb=min_imdb,
        price=price,
        certification_id=certification_id,
    )
    total_pages = ceil(total_items / per_page)

    prev_page = None
    next_page = None

    if page > 1:
        prev_page = f"/movies/?page={page - 1}&per_page={per_page}"
    if page < total_pages:
        next_page = f"/movies/?page={page + 1}&per_page={per_page}"

    return MovieListResponseSchema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post(
    "/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a movie",
    description="Moderator only. Validates field ranges (year, IMDb, etc.).",
    responses={
        403: {"description": "Moderator permissions required"},
        422: {"description": "Validation error"},
    },
)
async def add_movie(
        movie_data: MovieCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Movie:
    movie = await create_movie(db, movie_data)
    return await get_movie_by_id(db, movie.id)


@router.put(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Update a movie",
    description="Moderator only. Partial update — only provided fields change.",
    responses={
        403: {"description": "Moderator permissions required"},
        404: {"description": "Movie not found"},
        422: {"description": "Validation error"},
    },
)
async def edit_movie(
        movie_id: int,
        movie_data: MovieUpdateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Movie | None:
    movie = await update_movie(db, movie_id, movie_data)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return await get_movie_by_id(db, movie_id)


@router.post(
    "/{movie_id}/favorite/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie to favorites",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Movie not found"},
        409: {"description": "Movie is already in favorites"},
    },
)
async def add_to_favorites(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
):
    if not await db.get(Movie, movie_id):
        raise HTTPException(status_code=404, detail="Movie not found.")

    if not await add_favorite(db, current_user.id, movie_id):
        raise HTTPException(status_code=409, detail="Movie is already in favorites.")

    return {"detail": "Movie added to favorites."}


@router.delete(
    "/{movie_id}/favorite/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a movie from favorites",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Movie is not in favorites"},
    },
)
async def remove_from_favorites(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
):
    if not await remove_favorite(db, current_user.id, movie_id):
        raise HTTPException(status_code=404, detail="Movie is not in favorites.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{movie_id}/rating/",
    response_model=MessageResponseSchema,
    summary="Rate a movie (1-10)",
    description="Creates your rating or updates the existing one.",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Movie not found"},
    },
)
async def rate_movie(
        movie_id: int,
        data: MovieRatingSchema,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
):
    if not await db.get(Movie, movie_id):
        raise HTTPException(status_code=404, detail="Movie not found.")

    await set_rating(db, current_user.id, movie_id, data.rating)
    return {"detail": "Rating saved."}


@router.delete(
    "/{movie_id}/rating/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove my rating",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Rating not found"},
    },
)
async def remove_movie_rating(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
):
    if not await remove_rating(db, current_user.id, movie_id):
        raise HTTPException(status_code=404, detail="Rating not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/genres/{genre_id}/movies/",
    response_model=MovieListResponseSchema,
    summary="List movies of a genre",
    responses={404: {"description": "Genre not found"}},
)
async def list_genre_movies(
        genre_id: int,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=20),
        db: AsyncSession = Depends(get_db_session),
):
    if not await get_genre_by_id(db, genre_id):
        raise HTTPException(status_code=404, detail="Genre not found.")

    movies, total = await get_movies_by_genre(db, genre_id, page, per_page)
    total_pages = ceil(total / per_page)

    base = f"/movies/genres/{genre_id}/movies/"
    return {
        "movies": movies,
        "prev_page": f"{base}?page={page - 1}&per_page={per_page}" if page > 1 else None,
        "next_page": f"{base}?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        "total_pages": total_pages,
        "total_items": total,
    }


@router.post(
    "/{movie_id}/like/",
    response_model=MovieLikeSchema,
    summary="Like or dislike a movie",
    description="Sets or updates the current user's reaction to the movie.",
    responses={404: {"description": "Movie not found"}},
)
async def set_like(
        movie_id: int,
        like_data: MovieLikeCreateSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
) -> MovieLike:
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return await set_movie_reaction(db, movie_id, current_user.id, like_data)


@router.delete(
    "/{movie_id}/like/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove movie reaction",
    responses={404: {"description": "Reaction not found"}},
)
async def delete_like(
        movie_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await delete_movie_reaction(db, movie_id, current_user.id)

    if not deleted:
        raise HTTPException(404, "Reaction not found")


@router.get(
    "/{movie_id}/likes/",
    response_model=MovieReactionsSchema,
    summary="Get movie like/dislike counts",
    responses={404: {"description": "Movie not found"}},
)
async def movie_reactions(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> MovieReactionsSchema:
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return await get_movie_reactions(db, movie_id)


@router.delete(
    "/{movie_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a movie",
    description="Moderator only. Blocked if the movie was already purchased.",
    responses={
        403: {"description": "Moderator permissions required"},
        404: {"description": "Movie not found"},
        409: {"description": "Movie has been purchased and cannot be deleted"},
    },
)
async def remove_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Response:
    movie = await get_movie_by_id(db, movie_id)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found.",
        )
    if await movie_is_purchased(db, movie_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a movie that has been purchased.",
        )
    await delete_movie(db, movie_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
