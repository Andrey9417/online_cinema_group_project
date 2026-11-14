from decimal import Decimal
from math import ceil
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from crud.comments import create_comment, get_movie_comments
from crud.likes import set_movie_reaction, delete_movie_reaction, get_movie_reactions
from database.models import Movie, User, Comment, MovieLike
from database.session import get_db_session
from crud.movies import (
    get_movie_by_id,
    get_movie_list,
    create_movie,
    update_movie,
    delete_movie,
)
from schemas.comments import CommentSchema, CommentCreateSchema
from schemas.likes import MovieLikeSchema, MovieLikeCreateSchema, MovieReactionsSchema
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

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found",
        )

    return movie


@router.get("/", response_model=MovieListResponseSchema)
async def movie_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(
            10,
            ge=1,
            le=20,
            description="Number of items per page"
        ),
        sort_by: str | None = Query(None),
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
    if not movie:
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


@router.post(
    "/{movie_id}/comments/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED
)
async def add_comment(
        movie_id: int,
        comment_data: CommentCreateSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
) -> Comment:
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return await create_comment(db, movie_id, current_user.id, comment_data)


@router.get(
    "/{movie_id}/comments/",
    response_model=list[CommentSchema]
)
async def list_comments(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> Sequence[Comment]:
    return await get_movie_comments(db, movie_id)


@router.post(
    "/{movie_id}/like/",
    response_model=MovieLikeSchema
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
    status_code=status.HTTP_204_NO_CONTENT
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
)
async def movie_reactions(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> MovieReactionsSchema:
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return await get_movie_reactions(db, movie_id)
