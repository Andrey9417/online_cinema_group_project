import math
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Movie
from database.session import get_db_session
from typing import Literal
from crud.movies import (
    get_movie_by_id,
    get_movie_list,
    create_movie,
    update_movie,
    delete_movie,
)
from schemas.movies import (
    MovieDetailSchema,
    MovieListResponseSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
)

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/{movie_id}/", response_model=MovieDetailSchema)
async def movie_detail(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session)
) -> Movie:
    movie = await get_movie_by_id(db, movie_id)

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie not found",
        )

    return movie



@router.get("/movies/favorites/", response_model=MovieListResponseSchema)
async def list_favorites(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    search: str | None = Query(None),
    year: int | None = Query(None),
    min_imdb: float | None = Query(None, ge=0, le=10),
    sort_by: Literal["price", "year", "imdb", "popularity"] = "year",
    order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    movies, total = await crud.get_favorite_movies(
        db, current_user.id, page, per_page, search, year, min_imdb, sort_by, order
    )
    total_pages = math.ceil(total / per_page)

    return {
        "movies": movies,
        "prev_page": f"/movies/favorites/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        "next_page": f"/movies/favorites/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        "total_pages": total_pages,
        "total_items": total,
    }

@router.get("/", response_model=MovieListResponseSchema)
async def movie_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(
            10,
            ge=1,
            le=20,
            description="Number of items per page"
        ),
        db: AsyncSession = Depends(get_db_session)
) -> MovieListResponseSchema:
    movies, total_items = await get_movie_list(db, page, per_page)
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
)
async def add_movie(
        movie_data: MovieCreateSchema,
        db: AsyncSession = Depends(get_db_session),
) -> Movie:
    movie = await create_movie(db, movie_data)
    return await get_movie_by_id(db, movie.id)


@router.put("/{movie_id}/", response_model=MovieDetailSchema)
async def edit_movie(
        movie_id: int,
        movie_data: MovieUpdateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Movie | None:
    movie = await update_movie(db, movie_id, movie_data)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return await get_movie_by_id(db, movie_id)


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session)
) -> None:
    deleted = await delete_movie(db, movie_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Movie not found")
