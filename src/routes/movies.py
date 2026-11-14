from math import ceil
from typing import Literal, Sequence
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.dependencies import get_current_user
from crud.comments import create_comment, get_movie_comments
from crud.likes import set_movie_reaction, delete_movie_reaction, get_movie_reactions
from database.models import Movie, User, Comment, MovieLike
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
    get_genre_by_id,
    get_movies_by_genre,
    get_genres_with_count,
    create_genre,
    update_genre,
    delete_genre,
    get_star_by_id,
    create_star,
    update_star,
    delete_star,
    set_rating,
    remove_rating,
)
from schemas.comments import CommentSchema, CommentCreateSchema
from schemas.likes import MovieLikeSchema, MovieLikeCreateSchema, MovieReactionsSchema
from schemas.movies import (
    MovieDetailSchema,
    MovieListResponseSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
    MessageResponseSchema,
    GenreWithCountSchema,
    MovieRatingSchema,
    GenreSchema,
    GenreCreateSchema,
    StarSchema,
    StarCreateSchema,
)

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/favorites/", response_model=MovieListResponseSchema)
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


@router.get("/genres/", response_model=list[GenreWithCountSchema])
async def list_genres(db: AsyncSession = Depends(get_db_session)):
    return await get_genres_with_count(db)


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
        moderator: User = Depends(require_moderator),
) -> Movie:
    movie = await create_movie(db, movie_data)
    return await get_movie_by_id(db, movie.id)


@router.put("/{movie_id}/", response_model=MovieDetailSchema)
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


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
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
    "/{movie_id}/favorite/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
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


@router.delete("/{movie_id}/favorite/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
):
    if not await remove_favorite(db, current_user.id, movie_id):
        raise HTTPException(status_code=404, detail="Movie is not in favorites.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{movie_id}/rating/", response_model=MessageResponseSchema)
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


@router.delete("/{movie_id}/rating/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_movie_rating(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
):
    if not await remove_rating(db, current_user.id, movie_id):
        raise HTTPException(status_code=404, detail="Rating not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/genres/{genre_id}/movies/", response_model=MovieListResponseSchema)
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


@router.post("/genres/", response_model=GenreSchema, status_code=status.HTTP_201_CREATED)
async def add_genre(
        data: GenreCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
):
    genre = await create_genre(db, data.name)
    if genre is None:
        raise HTTPException(status_code=409, detail="Genre with this name already exists.")
    return genre


@router.put("/genres/{genre_id}/", response_model=GenreSchema)
async def edit_genre(
        genre_id: int,
        data: GenreCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
):
    genre = await get_genre_by_id(db, genre_id)
    if genre is None:
        raise HTTPException(status_code=404, detail="Genre not found.")

    if not await update_genre(db, genre, data.name):
        raise HTTPException(status_code=409, detail="Genre with this name already exists.")
    return genre


@router.delete("/genres/{genre_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_genre(
        genre_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
):
    if not await delete_genre(db, genre_id):
        raise HTTPException(status_code=404, detail="Genre not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/stars/", response_model=StarSchema, status_code=status.HTTP_201_CREATED)
async def add_star(
        data: StarCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
):
    star = await create_star(db, data.name)
    if star is None:
        raise HTTPException(status_code=409, detail="Star with this name already exists.")
    return star


@router.put("/stars/{star_id}/", response_model=StarSchema)
async def edit_star(
        star_id: int,
        data: StarCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
):
    star = await get_star_by_id(db, star_id)
    if star is None:
        raise HTTPException(status_code=404, detail="Star not found.")

    if not await update_star(db, star, data.name):
        raise HTTPException(status_code=409, detail="Star with this name already exists.")
    return star


@router.delete("/stars/{star_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_star(
        star_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
):
    if not await delete_star(db, star_id):
        raise HTTPException(status_code=404, detail="Star not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
